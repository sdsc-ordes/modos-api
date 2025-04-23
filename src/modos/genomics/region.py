from __future__ import annotations
import math
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse
from typing import Optional

import pysam


@dataclass(order=True)
class Region:
    """Genomic region consisting of a chromosome (aka reference) name
    and a 0-indexed half-open coordinate interval.
    Note that the end may not be specified, in which it will be set to math.inf.
    """

    chrom: str
    start: int
    end: int | float

    def __post_init__(self):
        if not self.chrom:
            raise ValueError("Chromosome must be specified")
        if self.start < 0:
            raise ValueError("Start must be non-negative")
        if self.end < self.start:
            raise ValueError("End must be greater than or equal to start")

    def to_htsget_query(self):
        """Serializes the region into an htsget URL query.

        Example
        -------
        >>> Region(chrom='chr1', start=0, end=100).to_htsget_query()
        'referenceName=chr1&start=0&end=100'
        """
        query = f"referenceName={self.chrom}&start={self.start}"
        if self.end != math.inf:
            query += f"&end={self.end}"

        return query

    def to_tuple(self) -> tuple[str, Optional[int], Optional[int]]:
        """Return the region as a simple tuple."""
        return (
            self.chrom,
            self.start,
            int(self.end) if self.end != math.inf else None,
        )

    @classmethod
    def from_htsget_query(cls, url: str):
        """Instantiate from an htsget URL query

        Example
        -------
        >>> Region.from_htsget_query(
        ...   "http://localhost/htsget/reads/ex/demo1?format=CRAM&referenceName=chr1&start=0"
        ... )
        Region(chrom='chr1', start=0, end=inf)
        """
        query = parse_qs(urlparse(url).query)
        try:
            chrom = query["referenceName"][0]
        except KeyError:
            raise KeyError("referenceName is missing")
        start = int(query.get("start", [0])[0])
        end = float(query.get("end", [math.inf])[0])

        return Region(chrom, start, end)

    @classmethod
    def from_ucsc(cls, ucsc: str) -> Region:
        """Instantiate from a UCSC-formatted region string.

        Example
        -------
        >>> Region.from_ucsc('chr-1ba:10-320')
        Region(chrom='chr-1ba', start=10, end=320)
        >>> Region.from_ucsc('chr1:-320')
        Region(chrom='chr1', start=0, end=320)
        >>> Region.from_ucsc('chr1:10-')
        Region(chrom='chr1', start=10, end=inf)
        >>> Region.from_ucsc('chr1:10')
        Region(chrom='chr1', start=10, end=inf)

        Note
        ----
        For more information about the UCSC coordinate system,
        see: http://genomewiki.ucsc.edu/index.php/Coordinate_Transforms
        """
        try:
            chrom, interval = ucsc.split(":")
        except ValueError:
            # no : separator -> only chrom specified
            return cls(ucsc, 0, math.inf)
        try:
            start, end = interval.split("-")
        except ValueError:
            # no - separator -> only start specified
            return cls(chrom, int(interval), math.inf)

        # Allow empty strings for start and end
        start = 0 if start == "" else int(start)
        end = math.inf if end == "" else int(end)

        return cls(chrom, start, end)

    @classmethod
    def from_pysam(
        cls, record: pysam.VariantRecord | pysam.AlignedSegment
    ) -> Region:
        match record:
            case pysam.VariantRecord():
                chrom = record.chrom
                start = record.start
                end = record.stop
            case pysam.AlignedSegment():
                chrom = record.reference_name
                start = record.reference_start
                end = record.reference_end
            case _:
                raise TypeError(
                    "record must be a pysam.VariantRecord or pysam.AlignedSegment"
                )

        match (chrom, start, end):
            case str(), int(), int():
                return cls(chrom, start, end)
            case _:
                raise ValueError("Record must have coordinates")

    def overlaps(self, other: Region) -> bool:
        """Checks if other in self.
        This check if any portion of other overlaps with self.
        """
        same_chrom = self.chrom == other.chrom
        starts_in = self.start <= other.start <= self.end
        ends_in = self.start <= other.end <= self.end

        return same_chrom and (starts_in or ends_in)

    def contains(self, other: Region) -> bool:
        """Checks if other is fully contained in self."""
        same_chrom = self.chrom == other.chrom
        starts_in = self.start <= other.start <= self.end
        ends_in = self.start <= other.end <= self.end

        return same_chrom and starts_in and ends_in
