"""This is the key management service (kms) to generate short-lived s3
keys on the fly that match the permissions of a user's token.

It is only compatible with Garage S3 and Authentik, and assumes a reverse proxy provider is used.
"""

# TODO: group scope -> s3 prefix
# TODO: custom scope (e.g. write: bool) for read/write

from __future__ import annotations
from dataclasses import dataclass
import datetime
from functools import lru_cache
import os
from typing import cast, Self
import uuid

from fastapi import FastAPI, HTTPException
import jwt
from modos.logging import setup_logging
from pydantic import BaseModel
import requests

from . import models

AUTH_TOKEN = os.environ["AUTH_TOKEN"]  # NOTE: Authentik bootstrap token
AUTH_URL = os.environ["AUTH_URL"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_API_URL = os.environ["S3_API_URL"]
S3_API_TOKEN = os.environ["S3_API_TOKEN"]

setup_logging(
    level="INFO",
    time=True,
)

app = FastAPI()


@lru_cache
def get_client_credentials() -> tuple[str, str]:
    """Get client id and secret from authentik outpost proxy endpoint.

    Returns
    -------
    (client_id, client_secret)
        Outpost client credentials.

    """

    # NOTE: We assume there is only one reverse proxy provider.

    resp = requests.get(
        f"{AUTH_URL}/api/v3/outposts/proxy/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise HTTPException(status_code=resp.status_code, detail=str(err))

    outpost_data = resp.json()["results"][0]

    return (outpost_data["client_id"], outpost_data["client_secret"])


def decode_token(token: str) -> dict[str, str | list[str]]:
    """Decodes a JWT token with symmetric encryption.
    The decryption secret is fetched from the S3 server
    """
    client_id, client_secret = get_client_credentials()
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


class Permissions(BaseModel):
    read: bool
    write: bool
    owner: bool

    @classmethod
    def default(cls) -> Self:
        return cls(read=True, write=False, owner=False)


@dataclass
class KeySpec:
    bucket: str
    expiration: datetime.datetime
    prefixes: list[str] | None
    permissions: Permissions
    name: str | None = None

    @classmethod
    def from_token(cls, token: Token) -> Self:
        """S3 key specifications are extracted from a JWT token with the following assumptions:
        - 'exp' claim specifies the expiration time.
        - 'roles' claim (optional) specifies the allowed prefixes.
        - 'write' claim (optional) specifies if write access is granted.
        """
        data = decode_token(token.jwt)

        permissions: Permissions = Permissions.default()
        if str(data.get("permissions", "read")) == "write":
            permissions.write = True

        exp = cast(str, data["exp"])
        try:
            timestamp = float(exp)
        except (ValueError, TypeError):
            raise ValueError(f"exp field was not a POSIX timestamp: {exp}")
        expiration = timestamp

        roles = data.get("roles", None)
        if not isinstance(roles, list) and roles is not None:
            roles = [roles]

        return cls(
            bucket=S3_BUCKET,
            name=str(uuid.uuid4()),
            expiration=datetime.datetime.fromtimestamp(expiration),
            prefixes=roles,
            permissions=permissions,
        )


@dataclass
class Key:
    spec: KeySpec
    access_key_id: str
    secret_access_key: str | None

    @classmethod
    def from_spec(cls, spec: KeySpec) -> Self:
        """Request a new S3 Key with the correct expiration from garage S3 API."""
        resp = requests.post(
            f"{S3_API_URL}/v2/CreateKey",
            headers={"Authorization": f"Bearer {S3_API_TOKEN}"},
            json={
                "name": spec.name,
                "expiration": spec.expiration.isoformat(),
            },
        ).json()

        key_info = models.KeyInfoResponse.model_validate(resp)

        return cls(
            spec=spec,
            access_key_id=key_info.access_key_id,
            secret_access_key=key_info.secret_access_key,
        )

    def set_permissions(self) -> None:
        """Configure the right permissions for this key on the S3 server"""

        _ = requests.post(
            f"{S3_API_URL}/v2/AllowBucketKey",
            headers={"Authorization": f"Bearer {S3_API_TOKEN}"},
            json={
                "accessKeyId": self.access_key_id,
                "bucketId": S3_BUCKET,
                "permissions": self.spec.permissions.model_dump(),
            },
        )


class Token(BaseModel):
    jwt: str


@app.post("/create")
def create(token: Token) -> Key:
    """List MODO entries in bucket.

    Parameters
    ----------
    token
        The encoded JWT token provided by a client.

    Returns
    -------
    Key
        The generated S3 key with appropriate permissions.
    """
    key_spec = KeySpec.from_token(token)
    key = Key.from_spec(key_spec)
    key.set_permissions()

    return key
