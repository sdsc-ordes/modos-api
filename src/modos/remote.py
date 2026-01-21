"""Functions related to server storage handling"""

from __future__ import annotations
from dataclasses import field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import os
from pathlib import Path
from typing import Any, Self
import warnings

import jwt
from pydantic import BaseModel, HttpUrl, validate_call
from pydantic.dataclasses import dataclass
import requests
from requests.auth import AuthBase


class BearerAuth(AuthBase):
    def __init__(self):
        self.jwt = JWT.from_cache()

    def __call__(
        self, r: requests.PreparedRequest
    ) -> requests.PreparedRequest:
        if self.jwt:
            if self.jwt.is_expired:
                self.jwt = self.jwt.refresh()
            if self.jwt:
                r.headers["Authorization"] = f"Bearer {self.jwt.access_token}"
        return r


@lru_cache
def get_session() -> requests.Session:
    s = requests.Session()
    s.auth = BearerAuth()
    return s


@dataclass(frozen=True)
class EndpointManager:
    """Handle modos server endpoints.
    If a modos server url is provided, it is used to detect
    available service urls. Alternatively, service urls can
    be provided explicitely if no modos server is available.

    Parameters
    ----------
    modos
        URL to the modos server.
    services
        Mapping of services to their urls.

    Examples
    --------
    >>> ex = EndpointManager(modos="http://modos.example.org") # doctest: +SKIP
    >>> ex.list() # doctest: +SKIP
    {
      's3: 'http://s3.example.org/',
      'htsget': 'http://htsget.example.org/'
    }
    >>> ex.htsget # doctest: +SKIP
    'http://htsget.example.org'
    >>> ex = EndpointManager(services={"s3": "http://s3.example.org"})
    >>> ex.s3
    'http://s3.example.org'
    """

    modos: HttpUrl | None = None
    services: dict[str, Any] = field(default_factory=dict)

    @property
    def session(self):
        return get_session()

    def list(self) -> dict[str, Any]:
        """List available endpoints."""
        if self.modos:
            return self.session.get(url=str(self.modos)).json()
        elif self.services:
            return self.services
        else:
            return {}

    @property
    def auth(self) -> dict[str, str | HttpUrl] | None:
        return self.list().get("auth")

    @property
    def kms(self) -> HttpUrl | None:
        return self.list().get("kms")

    @property
    def s3(self) -> dict[str, str | HttpUrl] | None:
        return self.list().get("s3")

    @property
    def fuzon(self) -> HttpUrl | None:
        return self.list().get("fuzon")

    @property
    def htsget(self) -> HttpUrl | None:
        return self.list().get("htsget")

    @property
    def refget(self) -> HttpUrl | None:
        return self.list().get("refget")


@validate_call
def list_remote_items(url: HttpUrl) -> list[HttpUrl]:
    session = get_session()
    return session.get(url=f"{url}/list").json()["data"]


@validate_call
def get_metadata_from_remote(
    url: HttpUrl, modo_id: str | None = None
) -> dict[str, Any]:
    """Function to access metadata from one specific or all modos on a remote server

    Parameters
    ----------
    server_url
        Url to the remote modo server
    id
        id of the modo to retrieve metadata from. Will return all if not specified (default).
    """
    session = get_session()
    meta = session.get(url=f"{url}/meta").json()
    if modo_id is not None:
        try:
            return meta[modo_id]
        except KeyError as e:
            raise ValueError(
                f"Could not find metadata for modo with id: {modo_id}"
            ) from e
    else:
        return meta


def is_s3_path(path: str):
    """Check if a path is an S3 path"""
    return path.startswith("s3://")


@validate_call
def get_s3_path(
    url: HttpUrl, query: str, exact_match: bool = False
) -> dict[str, Any]:
    """Request public S3 path of a specific modo or all modos matching the query string
    Parameters
    ----------
    remote_url
        Url to the remote modo server
    query
        query string to specify the modo of interest
    exact_match
        if True only modos with exactly that id will be returned, otherwise (default) all matching modos
    """
    session = get_session()
    return session.get(
        url=f"{url}/get",
        params={"query": query, "exact_match": exact_match},
    ).json()


@lru_cache
def get_cache_dir() -> Path:
    from platformdirs import user_cache_dir

    cache = user_cache_dir("modos", "sdsc", ensure_exists=True)
    return Path(cache)


@dataclass
class JWT:
    """Handles storage of JWT tokens for authentication.

    Examples
    --------
    >>> token = JWT(access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MzI5MjU2MDB9.DummySignature")
    >>> token.is_expired
    True
    >>> token.to_cache()
    >>> loaded_jwt = JWT.from_cache()
    >>> loaded_jwt.access_token == token.access_token
    True
    """

    access_token: str
    _expires_at: datetime | None = None

    @property
    def expires_at(self):
        if not self._expires_at:
            payload = jwt.decode(
                self.access_token, options={"verify_signature": False}
            )
            self._expires_at = datetime.fromtimestamp(
                float(payload["exp"]), tz=timezone.utc
            )
        return self._expires_at

    @staticmethod
    def get_cache_path() -> Path:
        return get_cache_dir() / "token.jwt"

    def to_cache(self):
        """Store JWT in cache directory."""
        with open(JWT.get_cache_path(), "w") as f:
            _ = f.write(self.access_token)
        os.chmod(JWT.get_cache_path(), 0o600)

    @classmethod
    def from_cache(cls) -> JWT | None:
        """Load JWT from cache directory if it exists."""

        if not JWT.get_cache_path().exists():
            return None

        with open(JWT.get_cache_path(), "r") as f:
            return cls(f.read().strip())

    @property
    def is_expired(self, skew: int = 30) -> bool:
        return datetime.now(timezone.utc) >= (
            self.expires_at - timedelta(seconds=skew)
        )

    def refresh(self) -> JWT | None:
        warnings.warn("Token refresh is not yet implemented.")
        return None


class Permissions(BaseModel):
    read: bool
    write: bool
    owner: bool

    @classmethod
    def default(cls) -> Self:
        return cls(read=True, write=False, owner=False)

    def __str__(self):
        return ",".join([k for (k, v) in self.model_dump().items() if v])


class S3KeySpec(BaseModel):
    bucket: str
    expiration: datetime
    prefixes: list[str] | None
    permissions: Permissions
    name: str | None = None
    region: str = "us-east-1"


class S3Key(BaseModel):
    spec: S3KeySpec
    access_key_id: str
    secret_access_key: str | None

    def valid_paths(self) -> str:
        """Prints the valid S3 paths for this key."""
        prefixes = self.spec.prefixes or []
        if len(prefixes) == 1:
            prefix = prefixes[0]
        else:
            prefix = "{" + ",".join(prefixes) + "}"
        return f"s3://{self.spec.bucket}/{prefix}"
