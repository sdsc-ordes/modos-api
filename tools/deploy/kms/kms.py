"""This is the key management service (kms) to generate short-lived s3
keys on the fly that match the permissions of a user's token.
"""

# TODO Get client id/secret from authentik
# curl -H 'Authorization: bearer $BOOTSTRAP_TOKEN' /api/v3/outposts/proxy/

# TODO: group scope -> s3 prefix
# TODO: custom scope (e.g. write: bool) for read/write

from dataclasses import dataclass
import datetime
import os
from typing import Self
import uuid

from fastapi import FastAPI, HTTPException
import jwt
from modos.logging import setup_logging
from pydantic import BaseModel
import requests

AUTH_TOKEN = os.environ["AUTH_TOKEN"]  # NOTE: Authentik bootstrap token
S3_LOCAL_URL = os.environ["S3_LOCAL_URL"]
S3_PUBLIC_URL = os.environ["S3_PUBLIC_URL"]
S3_API_PORT = 3900  # TODO make configurable
BUCKET = os.environ["S3_BUCKET"]
HTSGET_LOCAL_URL = os.environ["HTSGET_LOCAL_URL"]
SERVICES = {
    "s3": S3_LOCAL_URL,
    "htsget": HTSGET_LOCAL_URL,
}

setup_logging(
    level="INFO",
    time=True,
)

app = FastAPI()


def get_client_credentials() -> dict[str, str]:
    client_id, client_secret = (
        requests.get(
            "https://auth.dev.fega.ordes.ch/api/v3/outposts/proxy/",
            headers={"Authorization": "bearer " + AUTH_TOKEN},
        )
        .response.json()
        .values()
    )
    return {"client_id": client_id, "client_secret": client_secret}


@dataclass
class KeySpec:
    bucket: str
    expiration: datetime.datetime
    prefixes: list[str] | None
    read: bool
    write: bool
    name: str | None = None

    @classmethod
    def from_token(cls, token: str) -> Self:
        data = decode_token(token)
        return cls(
            name=str(uuid.uuid4()),
            bucket=data["bucket"],
            expiration=datetime.datetime.fromisoformat(data["exp"]),
            prefixes=data.get("group", "").split(","),
            read=True,
            write=data.get("write", False) == "True",
        )


class ApiBucketKeyPerm(BaseModel):
    owner: bool
    read: bool
    write: bool


class KeyInfoBucketResponse(BaseModel):
    id: str
    global_aliases: list[str]
    local_aliases: list[str]
    permissions: list[ApiBucketKeyPerm] | None


class KeyInfoResponse(BaseModel):
    name: str
    expired: bool
    buckets: list[KeyInfoBucketResponse]
    access_key_id: str
    secret_access_key: str | None
    expiration: datetime.datetime | None


def decode_token(token: str) -> dict[str, str]:
    client_id, client_secret = get_client_credentials().values()
    try:
        decoded = jwt.decode(
            token,
            client_secret,
            algorithms="HS256",
            audience=client_id,
            verify_audience=True,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return decoded


app.post("/")


def generate_s3_key(token: str) -> dict[str, list[str]]:
    """List MODO entries in bucket."""
    key_spec = KeySpec.from_token(token)
    key_resp: KeyInfoResponse = requests.post(
        f"{S3_LOCAL_URL}:{S3_API_PORT}/v2/CreateKey",
        json={"name": key_spec.name, "expiration": key_spec.expiration},
    )

    set_key_permissions(key, key_perms)
    key = {}
    return key


def generate_s3_key() -> dict[str, str]: ...


def set_key_permissions(key, scopes: KeyPerm) -> None: ...
