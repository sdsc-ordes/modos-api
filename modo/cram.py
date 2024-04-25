"""Utilities to interact with genomic intervals in CRAM files."""
from pathlib import Path
from typing import Iterator, List

from pysam import (
    AlignedSegment,
    AlignmentFile,
)
from urllib.parse import urlparse
import modo_schema.datamodel as model

import sys
import htsget
from .helpers import parse_region


def slice_cram(path: str, region: str) -> Iterator[AlignedSegment]:
    """Return an iterable slice of the CRAM file."""

    chrom, start, end = parse_region(region)
    if start == "":
        start = None
    else:
        start = int(start)
    if end == "":
        end = None
    else:
        end = int(end)
    cramfile = AlignmentFile(path, "rc")

    iter = cramfile.fetch(chrom, start, end)

    return iter


def slice_remote_cram(
    url: str, region: str = None, output_filename: str = None
):
    """Stream or write to a local file a slice of a remote CRAM file"""

    url = urlparse(url)
    url = url._replace(path=str(Path(url.path).with_suffix("")))

    reference_name, start, end = parse_region(region)
    if start == "":
        start = None
    else:
        start = int(start)
    if end == "":
        end = None
    else:
        end = int(end)

    if output_filename:
        with open(output_filename, "wb") as output:
            htsget.get(
                url=url.geturl(),
                output=output,
                reference_name=reference_name,
                start=start,
                end=end,
                data_format="cram",
            )
    else:
        htsget.get(
            url=url.geturl(),
            output=sys.stdout.buffer,
            reference_name=reference_name,
            start=start,
            end=end,
            data_format="cram",
        )

    return None


def extract_cram_metadata(cram: AlignmentFile) -> List:
    """Extract metadata from the CRAM file header and
    convert specific attributes according to the modo schema."""
    cram_head = cram.header
    ref_list: List = []
    for refseq in cram_head.get("SQ"):
        refseq_mod = model.ReferenceSequence(
            id=create_sequence_id(refseq.get("SN"), refseq.get("M5")),
            name=refseq.get("SN"),
            sequence_md5=refseq.get("M5"),
            source_uri=refseq.get("UR"),
            description=refseq.get("DS"),
        )
        ref_list.append(refseq_mod)
    # NOTE: Could also extract species name, sample name, sequencer etc. here
    return ref_list


def validate_cram_files(cram_path: str):
    """Validate CRAM files using pysam.
    Checks if the file is sorted and has an index."""
    # NOTE: Not a priority
    # TODO:
    # Check if sorted
    # Check if index exists
    # Check if reference exists


# TODO: Add functions to edit CRAM files (liftover)


def create_sequence_id(name: str, sequence_md5: str) -> str:
    """Helper function to create a unique id from a sequence name and md5 hash"""
    return name + "_" + sequence_md5[:6]
