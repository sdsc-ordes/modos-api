"""refget loader implementation

In the refget specifications each sequence object is associated by a metadata object.
Metadata provide a json encoded list of all known identifiers and aliases (see [1]_).

Sequence and metadata objects must have content-type header to fulfill the refget specification.

In S3 redirection can be used to enable sequence access via different ids.
This can be achieved by an empty object with the alternative id as filename and a Website-Redirect-Location header mapping to the sequence location (see [2]_).


References
----------

.. [1] http://samtools.github.io/hts-specs/refget.html
.. [2] https://github.com/ga4gh/refget-cloud/blob/master/docs/guides/DataSourceAwsS3.md

"""

import json
from typing import Dict, Optional

from gtars.digests import digest_fasta, sha512t24u_digest, md5_digest
from loguru import logger
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass
import pysam
import s3fs


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class RefgetStorage:
    fs: s3fs.S3FileSystem
    bucket: str

    # TODO: Restrict checksums to TypedDict?
    def upload_seq(
        self,
        seq: str,
        primary: str = "md5",
        checksums: Optional[Dict[str, str]] = None,
    ):
        checksums = checksums or calculate_checksums(seq)
        meta = {**checksums, "length": seq.__len__()}

        # upload primary checksum
        primary_path = f"sequence/{checksums.get(primary)}"
        primary_meta_path = f"metadata/json/{checksums.get(primary)}.json"
        upload_to_s3(
            fs=self.fs,
            bucket=self.bucket,
            key=primary_path,
            data=seq,
            headers={"Content-Type": "text/vnd.ga4gh.refget.v1.0.0+plain"},
        )
        upload_to_s3(
            fs=self.fs,
            bucket=self.bucket,
            key=primary_meta_path,
            data=json.dumps(meta),
            headers={
                "Content-Type": "application/vnd.ga4gh.refget.v1.0.0+json"
            },
        )

        # upload secondary checksums
        for alias, id in checksums.items():
            if alias == primary:
                continue
            else:
                secondary_path = f"sequence/{id}"
                secondary_meta_path = f"metadata/json/{id}.json"
                upload_to_s3(
                    fs=self.fs,
                    bucket=self.bucket,
                    key=secondary_path,
                    headers={"Website-Redirect-Location": f"/{primary_path}"},
                )
                upload_to_s3(
                    fs=self.fs,
                    bucket=self.bucket,
                    key=secondary_meta_path,
                    headers={
                        "Website-Redirect-Location": f"/{primary_meta_path}"
                    },
                )

    # NOTE: gtars ^0.2.3 should be able to handle pathlib.Path as input, but pysam expects a str
    def upload_fasta(self, fasta_file: str):
        digest = digest_fasta(fasta_file)
        fasta = pysam.FastaFile(fasta_file)
        for ref in digest:
            seq = fasta.fetch(ref.id)
            checksums = {"md5": ref.md5, "ga4gh": f"SQ.{ref.sha512t24u}"}
            self.upload_seq(seq, checksums=checksums)


def calculate_checksums(seq: str) -> Dict:
    checksums: Dict = {}
    checksums["md5"] = md5_digest(seq)
    checksums["ga4gh"] = "SQ.{}".format(sha512t24u_digest(seq))
    return checksums


def upload_to_s3(
    fs: s3fs.S3FileSystem,
    bucket: str,
    key: str,
    data: str = "",
    headers: Optional[Dict[str, str]] = None,
):
    s3_path = f"{bucket}/{key}"

    # Setting headers for S3 object
    s3_metadata = headers if headers else {}
    file_data = data.encode("utf-8")

    with fs.open(s3_path, "wb", metadata=s3_metadata) as f:
        f.write(file_data)

    logger.info(f"File uploaded successfully to {s3_path}")
