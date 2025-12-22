"""This is the key management service (kms) to generate short-lived s3
keys on the fly that match the permissions of a user's token.

It is only compatible with Garage S3 and Authentik, and assumes a reverse proxy provider is used.
"""

# TODO: group scope -> s3 prefix

from __future__ import annotations
from dataclasses import dataclass
import datetime
from functools import lru_cache
import os
from typing import Annotated, cast, Self
import uuid

from fastapi import FastAPI, Header, HTTPException
import jwt
from modos.logging import setup_logging
from pydantic import BaseModel
import requests

from . import models

AUTH_TOKEN = os.environ["AUTH_TOKEN"]  # NOTE: Authentik bootstrap token
AUTH_CLIENT_ID = os.environ["AUTH_CLIENT_ID"]
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

    resp = requests.get(
        f"{AUTH_URL}/api/v3/outposts/proxy/",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise HTTPException(status_code=resp.status_code, detail=str(err))

    # Find the proxy matching modos client id
    results = resp.json()["results"]
    proxies = [o for o in results if o["client_id"] == AUTH_CLIENT_ID]

    if len(proxies) > 1:
        raise ValueError("Multiple proxy providers matched client id")
    data = proxies[0]

    return (data["client_id"], data["client_secret"])


def decode_token(token: str) -> dict[str, str | list[str]]:
    """Decodes a JWT token with symmetric encryption.
    The decryption secret is fetched from the S3 server

    Parameters
    ----------
    """
    # NOTE: only symmetric HS256 is supported with authentik proxy providers
    # hence the need for client_secret
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
    def from_token(cls, token: str) -> Self:
        """S3 key specifications are extracted from a JWT token with the following assumptions:
        - 'exp' claim specifies the expiration time.
        - 'roles' claim (optional) specifies the allowed prefixes.
        - 'write' claim (optional) specifies if write access is granted.
        """
        data = decode_token(token)

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
        payload = {
            "allow": None,
            "deny": None,
            "neverExpires": False,
            "name": spec.name,
            "expiration": f"{spec.expiration.isoformat()}Z",
        }
        resp = requests.post(
            f"{S3_API_URL}/v2/CreateKey",
            headers={"Authorization": f"Bearer {S3_API_TOKEN}"},
            json=payload,
        ).json()

        key_info = models.KeyInfoResponse.model_validate(resp)

        return cls(
            spec=spec,
            access_key_id=key_info.access_key_id,
            secret_access_key=key_info.secret_access_key,
        )

    def set_permissions(self) -> None:
        """Configure the right permissions for this key on the S3 server"""

        # Retrieve internal bucket id from global alias (name)
        resp = requests.get(
            f"{S3_API_URL}/v2/GetBucketInfo?globalAlias={S3_BUCKET}",
            headers={"Authorization": f"Bearer {S3_API_TOKEN}"},
        )
        resp.raise_for_status()
        bucket_id = resp.json()["id"]

        # Apply permissions for existing key
        _ = requests.post(
            f"{S3_API_URL}/v2/AllowBucketKey",
            headers={"Authorization": f"Bearer {S3_API_TOKEN}"},
            json={
                "accessKeyId": self.access_key_id,
                "bucketId": bucket_id,
                "permissions": self.spec.permissions.model_dump(),
            },
        )


@app.get("/create")
def create(
    authorization: Annotated[str, Header(..., alias="Authorization")],
) -> Key:
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
    token = authorization.split(" ")[-1]
    key_spec = KeySpec.from_token(token)
    key = Key.from_spec(key_spec)
    key.set_permissions()

    return key
