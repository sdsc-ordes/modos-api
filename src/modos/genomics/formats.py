from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional

import pysam

from modos.genomics.region import Region

MAGIC_NUMBER = b"crypt4gh"


class GenomicFileSuffix(tuple, Enum):
    """Enumeration of all supported genomic file suffixes."""

    CRAM = (".cram",)
    BAM = (".bam",)
    SAM = (".sam",)
    VCF = (".vcf", ".vcf.gz")
    BCF = (".bcf",)
    FASTA = (".fasta", ".fa")
    FASTQ = (".fastq", ".fq")

    @classmethod
    def list_formats(cls):
        return [fmt.name for fmt in cls]

    @classmethod
    def from_path(cls, path: Path) -> GenomicFileSuffix:
        for genome_ft in cls:
            if "".join(path.suffixes) in genome_ft.value:
                return genome_ft
        supported = [fi_format for fi_format in cls]
        raise ValueError(
            f"Unsupported file format: {''.join(path.suffixes)}.\n"
            f"Supported formats:{supported}"
        )

    def get_index_suffix(self) -> str:
        """Return the supported index suffix related to a genomic filetype"""
        match self.name:
            case "BAM" | "SAM":
                return ".bai"
            case "BCF":
                return ".csi"
            case "CRAM":
                return ".crai"
            case "FASTA" | "FASTQ":
                return ".fai"
            case "VCF":
                return ".tbi"

    def to_htsget_endpoint(self) -> str:
        """Return the htsget endpoint for a genomic file type"""
        match self.name:
            case "BAM" | "CRAM":
                return "reads"
            case "VCF" | "BCF":
                return "variants"
            case _:
                raise ValueError(f"No htsget endpoint for format {self.name}")


def read_pysam(
    path: Path,
    region: Optional[Region] = None,
    **kwargs,
) -> Iterator[pysam.AlignedSegment | pysam.VariantRecord]:
    """Automatically instantiate a pysam file object from input path and passes any additional kwarg to it."""
    out_fileformat = GenomicFileSuffix.from_path(Path(path)).name
    match out_fileformat:
        case "CRAM" | "BAM":
            pysam_func = pysam.AlignmentFile
        case "VCF" | "BCF":
            pysam_func = pysam.VariantFile
        case _:
            raise ValueError("Unsupported output file type.")

    try:
        pysam_handle = pysam_func(str(path), **kwargs)
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            pysam_handle = pysam_func(str(path))
        else:
            raise

    if region is None:
        stream = (rec for rec in pysam_handle)
    else:
        stream = pysam_handle.fetch(*region.to_tuple())

    return stream


def get_index(file_path: Path) -> Optional[Path]:
    try:
        ft = GenomicFileSuffix.from_path(Path(file_path))
        return file_path.with_suffix(file_path.suffix + ft.get_index_suffix())
    except ValueError:
        return None


def is_encrypted(file_path):
    with open(file_path, "rb") as f:
        magic = f.read(8)
    return magic == MAGIC_NUMBER


def add_suffix(file_path: Path, suffix: str) -> Path:
    """Return the file path with specific suffix."""
    if file_path.suffix == suffix:
        return file_path
    else:
        return file_path.with_suffix(file_path.suffix + suffix)


def remove_suffix(file_path: Path, suffix: str) -> Path:
    """Return the file path without specific suffix."""
    if file_path.suffix == suffix:
        return file_path.with_suffix("")
    else:
        return file_path
