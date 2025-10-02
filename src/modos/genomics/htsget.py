"""htsget client implementation

The htsget protocol [1]_ allows to stream slices of genomic data from a remote server.
The client is implemented as a file-like interface that lazily streams chunks from the server.

In practice, the client sends a request for a file with a specific format and genomic region.
The htsget server finds the byte ranges on the data server (e.g. S3) corresponding to the requests
and responds with a "ticket".

The ticket is a json document containing a list of blocks; each having headers and a URL pointing to_file
the corresponding byte ranges on the data server.

The client then streams data from these URLs, effectively concatenating the blocks into a single stream.


.. figure:: http://samtools.github.io/hts-specs/pub/htsget-ticket.png
   :width: 66%
   :alt: htsget mechanism diagram

   Illustration of the mechanism through which the htsget server allows streaming and random-access on genomic files. See [1]_ for more details.


Notes
-----

This implementation differs from the reference GA4GH implementation [2]_ in that it allows lazily consuming chunks from a file-like interface without saving to a file. A downside of this approach is that the client cannot seek.

Additionally, this implementation does not support asynchronous fetching of blocks, which means that blocks are fetched sequentially.

References
----------

.. [1] http://samtools.github.io/hts-specs/htsget.html
.. [2] https://github.com/ga4gh/htsget
"""

import base64
from collections import deque
from functools import cached_property
import io
from pathlib import Path
import re
import tempfile
from typing import Optional, Iterator
from urllib.parse import urlparse, parse_qs

from pydantic import HttpUrl, validate_call
from pydantic.dataclasses import dataclass
import pysam
import requests

from modos.genomics.region import Region
from modos.genomics.formats import GenomicFileSuffix, read_pysam


@validate_call
def build_htsget_url(
    host: HttpUrl, path: Path, region: Optional[Region]
) -> str:
    """Build an htsget URL from a host, path, and region.

    Examples
    --------
    >>> build_htsget_url(
    ...   "http://localhost:8000",
    ...   Path("file.bam"),
    ...   Region("chr1", 0, 1000)
    ... )
    'http://localhost:8000/reads/file?format=BAM&referenceName=chr1&start=0&end=1000'
    """
    format = GenomicFileSuffix.from_path(path)
    endpoint = format.to_htsget_endpoint()

    # remove .gz suffix if present
    stem = path.with_suffix("") if path.name.endswith("gz") else path
    stem = stem.with_suffix("")

    netloc = host if str(host).endswith("/") else f"{host}/"
    url = f"{netloc}{endpoint}/{stem}?format={format.name}"
    if region:
        url += f"&{region.to_htsget_query()}"
    return url


@validate_call
def parse_htsget_url(url: HttpUrl) -> tuple[str, Path, Optional[Region]]:
    """Given a URL to an htsget resource, extract the host, path, and region."""
    parsed = urlparse(str(url))
    query = parse_qs(parsed.query)

    if "format" not in query:
        raise ValueError("Missing format in htsget URL")

    format = GenomicFileSuffix[query["format"][0]]
    endpoint = format.to_htsget_endpoint()
    pre_endpoint = re.sub(rf"/{endpoint}.*", r"", parsed.path)
    host = f"{parsed.scheme}://{parsed.netloc}{pre_endpoint}"
    path = Path(re.sub(rf"^.*{endpoint}", r"", parsed.path)).with_suffix(
        f".{format.name.lower()}"
    )
    try:
        region = Region.from_htsget_query(str(url))
    except KeyError:
        region = None
    return (host, path, region)


class _HtsgetBlockIter:
    """Transparent iterator over blocks of an htsget stream.

    This is used internally by HtsgetStream to lazily fetch and concatenate blocks.

    Examples
    --------
    >>> next(_HtsgetBlockIter([
    ...     {"url": "data:;base64,MTIzNDU2Nzg5"},
    ...     {"url": "data:;base64,MTIzNDU2Nzg5"},
    ... ]))
    b'123456789'
    """

    def __init__(self, blocks: list[dict], chunk_size=65536, timeout=60):
        # the queue of block is consumed in order of appearance
        self._blocks = deque(blocks)
        self._source = self._consume_block()
        self.chunk_size = chunk_size
        self.timeout = timeout

    def __iter__(self):
        return self

    def _consume_block(self) -> Iterator[bytes]:
        """Get streaming iterator over current block."""
        curr_block = self._blocks.popleft()
        parsed = urlparse(curr_block["url"])
        match parsed.scheme:
            # http url -> fetch from data server
            case "http" | "https":
                chunks = requests.get(
                    curr_block["url"],
                    headers=curr_block.get("headers"),
                    stream=True,
                    timeout=self.timeout,
                ).iter_content(chunk_size=self.chunk_size)
                for chunk in chunks:
                    yield chunk
            # data uri -> content directly in ticket
            case "data":
                split = parsed.path.split(",", 1)
                data = base64.b64decode(split[1])
                yield data
            case _:
                raise ValueError(f"Unsupported scheme: {parsed.scheme}")

    def __next__(self) -> bytes:
        """
        Stream next chunk of current block, or first
        chunk of next block.
        """

        # Iterate over current block
        try:
            return next(self._source)
        # End of current block
        except StopIteration:
            # remaining blocks -> move to next block
            try:
                self._source = self._consume_block()
                return self.__next__()
            # last block -> end of stream
            except IndexError:
                raise StopIteration


class HtsgetStream(io.RawIOBase):
    """A file-like handle to a read-only, buffered htsget stream.

    Examples
    --------
    >>> stream = HtsgetStream([
    ...   {"url": "data:;base64,MTIzNDU2Nzg5Cg=="},
    ...   {"url": "data:;base64,MTIzNDU2Nzg5Cg=="},
    ... ])
    >>> stream.read(4)
    b'1234'
    """

    def __init__(self, blocks: list[dict]):
        self._iterator = _HtsgetBlockIter(blocks)
        self._leftover = b""

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:
        """
        Read up to len(b) bytes into a writable buffer bytes
        and return the number of bytes read.

        Notes
        -----
        See https://docs.python.org/3/library/io.html#io.RawIOBase.readinto
        """
        try:
            buflen = len(b)  # We return at most this much
            while True:
                chunk = self._leftover or next(self._iterator)
                # skip empty elements
                if not chunk:
                    continue

                # fill buffer and keep any leftover for next chunk
                output, self._leftover = chunk[:buflen], chunk[buflen:]
                b[: len(output)] = output
                return len(output)
        except StopIteration:
            return 0  # indicate EOF


@dataclass
class HtsgetConnection:
    """Connection to an htsget resource.
    It allows to open a stream to the resource and lazily fetch data from it.
    """

    host: HttpUrl
    path: Path
    region: Optional[Region]

    @property
    def url(self) -> str:
        """URL to fetch the ticket."""
        return build_htsget_url(self.host, Path(self.path), self.region)

    @cached_property
    def ticket(self) -> dict:
        """Ticket containing the URLs to fetch the data."""
        return requests.get(self.url).json()

    def open(self) -> io.RawIOBase:
        """Open a connection to the stream data."""
        try:
            return HtsgetStream(self.ticket["htsget"]["urls"])
        except KeyError:
            raise KeyError(f"No htsget urls found in ticket: {self.ticket}")

    def to_file(self, path: Path):
        """Save all data from the stream to a file."""
        with self.open() as source, open(path, "wb") as sink:
            for block in source:
                sink.write(block)

    @classmethod
    def from_url(cls, url: str):
        """Open connection directly from an htsget URL."""
        host, path, region = parse_htsget_url(url)
        return cls(host, path, region=region)

    def to_pysam(
        self, reference_filename: Optional[str] = None
    ) -> Iterator[pysam.AlignedSegment | pysam.VariantRecord]:
        """Convert the stream to a pysam object."""

        # NOTE: pysam needs a path or file descriptor,
        # we have to stream from drive until this is addressed:
        # ref: https://github.com/pysam-developers/pysam/blob/0787ca9da997b5911c00fd12584dad9741c82fb4/pysam/libcalignmentfile.pyx#L855
        # TODO: when above addressed, replace temporary file with
        # self.open() to stream directly from in-memory buffer.
        buffer = tempfile.NamedTemporaryFile(
            "w+b", delete=False, suffix="".join(self.path.suffixes)
        ).name

        self.to_file(Path(buffer))
        buffer = read_pysam(
            Path(buffer), reference_filename=reference_filename
        )

        for record in buffer:
            if self.region is None:
                yield record
                continue

            # htsget includes all returns in the bgzf block
            # we filter out records outside requested region
            record_region = Region.from_pysam(record)
            if not record_region.overlaps(self.region):
                continue
            yield record
