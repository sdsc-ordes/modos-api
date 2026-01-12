"""This is the key management service (kms) to generate short-lived s3
keys on the fly that match the permissions of a user's token.

It is only compatible with Garage S3 and Authentik, and assumes a reverse proxy provider is used.
"""

# TODO: group scope -> s3 prefix

from __future__ import annotations
import datetime
from functools import lru_cache
import os
from typing import Annotated, cast
import uuid

from fastapi import FastAPI, Header, HTTPException
import jwt
from modos.logging import setup_logging
from modos.remote import Permissions, S3Key, S3KeySpec
import requests

from . import models

AUTH_TOKEN = os.environ["AUTH_TOKEN"]  # NOTE: Authentik bootstrap token
AUTH_CLIENT_NAME = os.environ["AUTH_CLIENT_NAME"]
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
    proxies = [o for o in results if o["name"] == AUTH_CLIENT_NAME]

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
            require=["exp", "iat", "iss", "aud"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return decoded


def extract_spec(token: str) -> S3KeySpec:
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

    groups = data.get("groups", [])
    if not isinstance(groups, list):
        groups = [groups]

    return S3KeySpec(
        bucket=S3_BUCKET,
        name=str(uuid.uuid4()),
        expiration=datetime.datetime.fromtimestamp(expiration),
        prefixes=groups,
        permissions=permissions,
    )


def create_key(spec: S3KeySpec) -> S3Key:
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

    return S3Key(
        spec=spec,
        access_key_id=key_info.access_key_id,
        secret_access_key=key_info.secret_access_key,
    )


def set_key_permissions(key: S3Key) -> None:
    """Configure the right permissions for this key on the S3 server"""

    # Retrieve internal bucket id from global alias (name)
    resp = requests.get(
        f"{S3_API_URL}/v2/GetBucketInfo?globalAlias={S3_BUCKET}",
        headers={"Authorization": f"Bearer {S3_API_TOKEN}"},
    )
    resp.raise_for_status()
    print(resp.json())
    bucket_id = resp.json()["id"]

    # Apply permissions for existing key
    _ = requests.post(
        f"{S3_API_URL}/v2/AllowBucketKey",
        headers={"Authorization": f"Bearer {S3_API_TOKEN}"},
        json={
            "accessKeyId": key.access_key_id,
            "bucketId": bucket_id,
            "permissions": key.spec.permissions.model_dump(),
        },
    )

    print(_.json())


@app.get("/create")
def create(
    authorization: Annotated[str, Header(..., alias="Authorization")],
) -> S3Key:
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
    spec = extract_spec(token)
    key = create_key(spec)
    set_key_permissions(key)

    return key
