"""This is the webserver to serve MODO objects.
It connects to an S3 bucket (catalog) containing
MODOs (folders).

The role of this server is to provide a list of
available modos, as well as their metadata.

"""

import difflib
import os

from fastapi import FastAPI, HTTPException
from modos.api import MODO
from modos.logging import setup_logging
from modos.storage import connect_s3

# Required
S3_LOCAL_URL = os.environ["S3_LOCAL_URL"]
S3_PUBLIC_URL = os.environ["S3_PUBLIC_URL"]
BUCKET = os.environ["S3_BUCKET"]
HTSGET_LOCAL_URL = os.environ["HTSGET_LOCAL_URL"]

# Optional
OIDC_ISSUER_URL = os.environ.get("OIDC_ISSUER_URL", None)
AUTH_CLIENT_ID = os.environ.get("AUTH_CLIENT_ID", None)
FUZON_PUBLIC_URL = os.environ.get("FUZON_PUBLIC_URL", None)
HTSGET_PUBLIC_URL = os.environ.get("HTSGET_PUBLIC_URL", None)
REFGET_PUBLIC_URL = os.environ.get("REFGET_PUBLIC_URL", None)
KMS_PUBLIC_URL = os.environ.get("KMS_PUBLIC_URL", None)

SERVICES = {
    "s3": S3_LOCAL_URL,
    "htsget": HTSGET_LOCAL_URL,
}

app = FastAPI()

storage = connect_s3(f"s3://{BUCKET}", S3_LOCAL_URL)
setup_logging(
    level="INFO",
    time=True,
)


@app.get("/list")
def list_modos() -> dict[str, list[str]]:
    """List MODO entries in bucket."""
    try:
        modos = storage.list_with_delimiter()["common_prefixes"]
    except PermissionError:
        raise HTTPException(
            status_code=500, detail=f"Cannot access S3 bucket: {BUCKET}"
        )
    # NOTE: modo contains bucket name
    return {"data": [f"s3://{BUCKET}/{modo}" for modo in modos]}


@app.get("/meta")
def gather_metadata():
    """gather metadata from all MODOs."""
    resp = {"data": []}

    try:
        for modo in storage.list_with_delimiter()["common_prefixes"]:
            path = f"s3://{BUCKET}/{modo}"
            resp["data"].append(
                {
                    "meta": MODO(path=path, services=SERVICES).metadata,  # type: ignore
                    "path": path,
                }
            )
    except PermissionError:
        raise HTTPException(
            status_code=500, detail=f"Cannot access S3 bucket: {BUCKET}"
        )

    return resp


def str_similarity(s1: str, s2: str) -> float:
    """Computes a similarity metric between two strings between 0 and 1."""
    return difflib.SequenceMatcher(None, s1, s2).quick_ratio()


@app.get("/get")
def get_s3_path(query: str, fuzzy: bool = False):
    """Receive the S3 path of all modos matching the query.
    Can optionally use fuzzy matching to find similar names."""
    paths = storage.list_with_delimiter()["common_prefixes"]

    if not fuzzy:
        results = [path for path in paths if query == path]

    else:
        sims = [str_similarity(query, path) for path in paths]
        pairs = filter(lambda p: p[1] > 0.7, zip(paths, sims))
        pairs = sorted(pairs, key=lambda p: p[1], reverse=True)
        results = [p[0] for p in pairs]

    resp = {"data": []}
    resp["data"] = [
        {
            f"{modo}": {
                "s3_endpoint": S3_PUBLIC_URL,
                "modo_path": f"s3://{BUCKET}/{modo}",
            }
        }
        for modo in results
    ]

    return resp


@app.get("/")
def get_endpoints():
    endpoints = {
        "status": "success",
        "auth": None,
        "s3": S3_PUBLIC_URL,
        "htsget": HTSGET_PUBLIC_URL,
        "fuzon": FUZON_PUBLIC_URL,
        "kms": KMS_PUBLIC_URL,
        "refget": REFGET_PUBLIC_URL,
    }
    if OIDC_ISSUER_URL and AUTH_CLIENT_ID:
        endpoints["auth"] = {
            "url": OIDC_ISSUER_URL,
            "client_id": AUTH_CLIENT_ID,
        }
    return endpoints
