"""Functions related to server storage handling"""

from __future__ import annotations
import base64
from dataclasses import field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
import os
from pathlib import Path
from typing import Mapping, Optional
import warnings

from pydantic import HttpUrl, validate_call
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
            if self.jwt.is_expired():
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
      's3: Url('http://s3.example.org/'),
      'htsget': Url('http://htsget.example.org/')
    }
    >>> ex.htsget # doctest: +SKIP
    HttpUrl('http://htsget.example.org/')
    >>> ex = EndpointManager(services={"s3": "http://s3.example.org"})
    >>> ex.s3
    HttpUrl('http://s3.example.org/')

    """

    modos: Optional[HttpUrl] = None
    services: dict[str, HttpUrl] = field(default_factory=dict)

    @property
    def session(self):
        return get_session()

    def list(self) -> dict[str, HttpUrl]:
        """List available endpoints."""
        if self.modos:
            return self.session.get(url=str(self.modos)).json()
        elif self.services:
            return self.services
        else:
            return {}

    @property
    def s3(self) -> Optional[HttpUrl]:
        return self.list().get("s3")

    @property
    def fuzon(self) -> Optional[HttpUrl]:
        return self.list().get("fuzon")

    @property
    def htsget(self) -> Optional[HttpUrl]:
        return self.list().get("htsget")

    @property
    def refget(self) -> Optional[HttpUrl]:
        return self.list().get("refget")


@validate_call
def list_remote_items(url: HttpUrl) -> list[HttpUrl]:
    session = get_session()
    return session.get(url=f"{url}/list").json()["modos"]


@validate_call
def get_metadata_from_remote(
    url: HttpUrl, modo_id: Optional[str] = None
) -> Mapping:
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
def get_s3_path(url: HttpUrl, query: str, exact_match: bool = False) -> list:
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


@dataclass
class JWT:
    """Handles storage of JWT tokens for authentication."""

    access_token: str
    _expires_at: Optional[datetime] = None

    @property
    def expires_at(self):
        if not self._expires_at:
            payload = self.decode()
            self._expires_at = datetime.fromtimestamp(
                float(payload["exp"]), tz=timezone.utc
            )
        return self._expires_at

    @staticmethod
    def path() -> Path:
        from platformdirs import user_cache_dir

        cache = user_cache_dir("modos", "sdsc", ensure_exists=True)
        return Path(cache) / "token.jwt"

    def to_cache(self):
        """Store JWT in cache directory."""
        with open(JWT.path(), "w") as f:
            _ = f.write(self.access_token)
        os.chmod(JWT.path(), 0o600)

    @classmethod
    def from_cache(cls) -> JWT | None:
        """Load JWT from cache directory if it exists."""

        if not JWT.path().exists():
            return None

        with open(JWT.path(), "r") as f:
            return cls(f.read().strip())

    def decode(self) -> dict[str, str]:
        # Question: Do we also need header and signature?
        header, payload, signature = self.access_token.split(".")
        padded_payload = payload + "=" * (-len(payload) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded_payload)
        return json.loads(decoded_bytes)

    def is_expired(self, skew: int = 30) -> bool:
        return datetime.now(timezone.utc) >= (
            self.expires_at - timedelta(seconds=skew)
        )

    def refresh(self) -> JWT | None:
        warnings.warn("Token refresh is not yet implemented.")
        return None
