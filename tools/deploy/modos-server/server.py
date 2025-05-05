"""This is the webserver to serve MODO objects.
It connects to an S3 bucket (catalog) containing
MODOs (folders).

The role of this server is to provide a list of
available modos, as well as their metadata.

"""

import difflib
import os

from fastapi import FastAPI
from modos.api import MODO
from modos.storage import connect_s3


S3_LOCAL_URL = os.environ["S3_LOCAL_URL"]
S3_PUBLIC_URL = os.environ["S3_PUBLIC_URL"]
BUCKET = os.environ["S3_BUCKET"]
HTSGET_LOCAL_URL = os.environ["HTSGET_LOCAL_URL"]

app = FastAPI()
minio = connect_s3(S3_LOCAL_URL, {"anon": True})  # type: ignore


@app.get("/list")
def list_modos() -> dict[str, list[str]]:
    """List MODO entries in bucket."""
    modos = minio.ls(BUCKET, refresh=True)
    # NOTE: modo contains bucket name
    return {"modos": [f"s3://{modo}" for modo in modos]}


@app.get("/meta")
def gather_metadata():
    """Generate metadata KG from all MODOs."""
    meta = {}

    for modo in minio.ls(BUCKET, refresh=True):
        meta.update(MODO(path=modo, endpoint=S3_LOCAL_URL).metadata)  # type: ignore

    return meta


def str_similarity(s1: str, s2: str) -> float:
    """Computes a similarity metric between two strings between 0 and 1."""
    return difflib.SequenceMatcher(None, s1, s2).quick_ratio()


@app.get("/get")
def get_s3_path(query: str, exact_match: bool = False):
    """Receive the S3 path of all modos matching the query"""
    modos = minio.ls(BUCKET, refresh=True)
    paths = [modo.removeprefix(BUCKET) for modo in modos]

    if exact_match:
        res = [modo for (modo, path) in zip(modos, paths) if query == path]

    else:
        sims = [str_similarity(query, path) for path in paths]
        pairs = filter(lambda p: p[1] > 0.7, zip(modos, sims))
        pairs = sorted(pairs, key=lambda p: p[1], reverse=True)
        res = [p[0] for p in pairs]
    return [
        {
            f"{S3_PUBLIC_URL}/{modo}": {
                "s3_endpoint": S3_PUBLIC_URL,
                "modo_path": modo,
            }
        }
        for modo in res
    ]
