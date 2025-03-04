"""Functions related to server storage handling"""

from dataclasses import field
from typing import Mapping, Optional

from pydantic import HttpUrl, validate_call
from pydantic.dataclasses import dataclass
import requests


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

    def list(self) -> dict[str, HttpUrl]:
        """List available endpoints."""
        if self.modos:
            return requests.get(url=str(self.modos)).json()
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
    return requests.get(url=f"{url}/list").json()["modos"]


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
    meta = requests.get(url=f"{url}/meta").json()
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
    return requests.get(
        url=f"{url}/get",
        params={"query": query, "exact_match": exact_match},
    ).json()
