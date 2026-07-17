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
from collections.abc import Buffer, Iterator
from collections import deque
from functools import cached_property
import io
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.parse import urlparse, parse_qs

import htslurp

from crypt4gh import CIPHER_SEGMENT_SIZE
from crypt4gh.lib import decrypt

from pydantic import HttpUrl, validate_call
from pydantic.dataclasses import dataclass
import pysam
import requests

from modos.remote import get_session
from modos.genomics.c4gh import derive_public_key, get_secret_key
from modos.genomics.region import Region
from modos.genomics.formats import GenomicFileSuffix


@validate_call
def build_htsget_url(
    host: HttpUrl,
    path: Path,
    region: Region | None,
    encrypted: bool = False,
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
    >>> build_htsget_url(
    ...   "http://localhost:8000",
    ...   Path("file.bam"),
    ...   Region("chr1", 0, 1000),
    ...   encrypted=True,
    ... )
    'http://localhost:8000/reads/file?format=BAM&referenceName=chr1&start=0&end=1000&encryptionScheme=C4GH'
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
    if encrypted:
        url += "&encryptionScheme=C4GH"
    return url


@validate_call
def parse_htsget_url(url: HttpUrl) -> tuple[str, Path, Region | None]:
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

    def __init__(
        self,
        blocks: list[dict[str, str]],
        chunk_size: int = 65536,
        timeout: int = 60,
    ):
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

    def __init__(self, blocks: list[dict[str, str]]):
        self._iterator = _HtsgetBlockIter(blocks)
        self._leftover = b""

    def readable(self) -> bool:
        return True

    def readinto(self, b: Buffer) -> int:
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
    region: Region | None
    secret_key_path: Path | None = None
    passphrase: str | None = None

    @property
    def _encrypted(self) -> bool:
        return self.secret_key_path is not None

    @property
    def url(self) -> str:
        """URL to fetch the ticket."""
        return build_htsget_url(
            self.host, Path(self.path), self.region, encrypted=self._encrypted
        )

    @cached_property
    def _seckey(self) -> bytes:
        return get_secret_key(self.secret_key_path, self.passphrase)

    @cached_property
    def ticket(self) -> dict[str, Any]:
        """Ticket containing the URLs to fetch the data."""
        headers = {}
        if self._encrypted:
            headers["Client-Public-Key"] = base64.b64encode(
                derive_public_key(self._seckey)
            ).decode()
        return get_session().get(self.url, headers=headers).json()

    def _stream(self) -> HtsgetStream:
        """Assemble the raw (still encrypted) htsget stream from the ticket."""
        try:
            return HtsgetStream(self.ticket["htsget"]["urls"])
        except KeyError:
            raise KeyError(f"No htsget urls found in ticket: {self.ticket}")

    def open(self) -> io.IOBase:
        """Open a connection to the stream data (decrypted if a key is set).

        Encrypted streams are buffered to a temporary file for decryption,
        so the requested region is materialized before this returns.
        """
        stream = self._stream()
        if not self._encrypted:
            return stream

        # TODO: decrypt on the stream, and return a wrapped stream instead
        # of using a temp file
        plaintext = tempfile.TemporaryFile("w+b")
        try:
            self._decrypt_into(stream, plaintext)
        except BaseException:
            plaintext.close()
            raise
        plaintext.seek(0)
        return plaintext

    def _decrypt_into(self, stream: io.RawIOBase, outfile: io.IOBase) -> None:
        """Decrypt the whole stream at once, writing plaintext to outfile."""
        # decrypt expects a full cipher segment per read; BufferedReader
        # wraps HtsgetStream's per-block reads to deliver one.
        with io.BufferedReader(
            stream, buffer_size=CIPHER_SEGMENT_SIZE
        ) as encrypted:
            try:
                decrypt(
                    keys=[(0, self._seckey, None)],
                    infile=encrypted,
                    outfile=outfile,
                )
            except Exception as err:
                raise ValueError(
                    "Failed to decrypt htsget stream. Ensure the "
                    "secret key matches the public key registered "
                    "with the server."
                ) from err

    def to_file(self, path: Path):
        """Save all data from the stream to a file.

        Decryption writes straight into the destination, so an encrypted
        stream is never materialized to an intermediate temporary file.
        """
        with self._stream() as stream, open(path, "wb") as sink:
            if self._encrypted:
                self._decrypt_into(stream, sink)
            else:
                for block in stream:
                    sink.write(block)

    @property
    def format(self) -> str:
        return GenomicFileSuffix.from_path(self.path).name

    @classmethod
    def from_url(cls, url: str):
        """Open connection directly from an htsget URL."""
        host, path, region = parse_htsget_url(url)
        return cls(host, path, region=region)

    def records(self, reference: Path | None = None) -> htslurp.RecordIter:
        # NOTE: Does note support crypt4gh encryption (yet)
        records = htslurp.stream_records(
            base_url=self.url,
            id=str(self.path),
            format=self.format,
            region=self.region,
            reference=reference,
        )
        return records

    def to_pysam(
        self, reference_filename: Path | None = None
    ) -> Iterator[pysam.AlignedSegment | pysam.VariantRecord]:
        """Convert the stream to a pysam object."""

        # NOTE: we use a dedicated client because pysam does not support bytestreams
        # ref: https://github.com/pysam-developers/pysam/blob/0787ca9da997b5911c00fd12584dad9741c82fb4/pysam/libcalignmentfile.pyx#L855
        # TODO: if above addressed, replace temporary file with
        # self.open() to stream directly from in-memory buffer.

        stream = self.records(reference_filename)

        for record in stream:
            match self.format:
                case "CRAM" | "BAM" | "SAM":
                    parsed = pysam.AlignedSegment.fromstring(
                        record.decode(), stream.header
                    )
                case _:
                    # NOTE: pysam does not support instantiating VariantRecord on the fly.
                    raise ValueError(
                        f"Cannot convert {self.format} records to pysam."
                    )

            if self.region is None:
                yield parsed
                continue

            # htsget includes all returns in the bgzf block
            # we filter out records outside requested region
            record_region = Region.from_pysam(record)
            if not record_region.overlaps(self.region):
                continue
            yield parsed
