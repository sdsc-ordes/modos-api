from __future__ import annotations
from abc import ABC, abstractmethod
import io
from loguru import logger
import os
from pathlib import Path
import re
import shutil
from typing import Any, ClassVar, Generator, Optional

import obstore as obs
from obstore.store import S3Store
from pydantic import Field, HttpUrl
from pydantic.dataclasses import dataclass
import zarr
import zarr.hierarchy as zh
from zarr.storage import ObjectStore


from modos.helpers.schema import ElementType

ZARR_ROOT = Path("data.zarr")


class Storage(ABC):
    @property
    @abstractmethod
    def path(self) -> Path: ...

    @property
    @abstractmethod
    def zarr(self) -> zh.Group: ...

    @abstractmethod
    def exists(self, target: Path) -> bool: ...

    @abstractmethod
    def list(
        self,
        target: Optional[Path] = None,
    ) -> Generator[Path, None, None]:
        """List files in the storage.

        Parameters
        ----------
        target:
            path to a directory to list relative to storage.path.
            If None, list all files in storage.
        """
        ...

    @abstractmethod
    def move(self, rel_source: Path, target: Path):
        """Move a file within storage.

        Parameters
        -----------------
        rel_source:
            source path to the file to move relative to storage.path
        target:
            target path within storage
        """
        ...

    @abstractmethod
    def open(self, target: Path) -> io.BufferedReader: ...

    @abstractmethod
    def put(self, source: io.BufferedReader, target: Path): ...

    @abstractmethod
    def remove(self, target: Path): ...

    def transfer(self, other: Storage):
        """Transfer all contents of one storage to another one."""
        for path in self.list():
            item = path.relative_to(self.path)
            with self.open(item) as src:
                other.put(src, item)

    def empty(self) -> bool:
        return len(self.zarr.attrs.keys()) == 0


class LocalStorage(Storage):
    def __init__(self, path: Path):
        self._path = Path(path)
        if (self.path / ZARR_ROOT).exists():
            self._zarr = zarr.convenience.open(str(self.path / ZARR_ROOT))
        else:
            self.path.mkdir(exist_ok=True)
            zarr_store = zarr.storage.DirectoryStore(
                str(self.path / ZARR_ROOT)
            )
            self._zarr = init_zarr(zarr_store)

    @property
    def zarr(self) -> zh.Group:
        return self._zarr

    @property
    def path(self) -> Path:
        return self._path

    def exists(self, target: Path) -> bool:
        return (self.path / target).exists()

    def list(
        self, target: Optional[Path] = None
    ) -> Generator[Path, None, None]:
        path = self.path / (target or "")
        for path in path.glob("*"):
            if path.is_file():
                yield path
            for file in path.rglob("*"):
                if file.is_file():
                    yield file

    def move(self, rel_source: Path, target: Path):
        shutil.move(self.path / rel_source, self.path / target)

    def open(self, target: Path) -> io.BufferedReader:
        return open(self.path / target, "rb")

    def put(self, source: io.BufferedReader, target: Path):
        os.makedirs(self.path / target.parent, exist_ok=True)

        with open(self.path / target, "wb") as f:
            while chunk := source.read(8192):
                f.write(chunk)

    def remove(self, target: Path):
        if target.exists():
            target.unlink()
            logger.info(f"Permanently deleted {target} from filesystem.")


@dataclass
class S3Path:
    """Pydantic Model for S3 URLs. Performs validation against amazon's official naming rules [1]_ [2]_

    .. [1] https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
    .. [2] https://gist.github.com/rajivnarayan/c38f01b89de852b3e7d459cfde067f3f


    Examples
    --------
    >>> S3Path(url="s3://test/ex")
    S3Path(url='s3://test/ex')
    >>> S3Path(url='s3://?invalid-bucket-name!/def') # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      ...
    pydantic_core._pydantic_core.ValidationError: 1 validation error for S3Path
    """

    _s3_pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"^s3://"
        r"(?=[a-z0-9])"  # Bucket name must start with a letter or digit
        r"(?!(^xn--|sthree-|sthree-configurator|.+-s3alias$))"  # Bucket name must not start with xn--, sthree-, sthree-configurator or end with -s3alias
        r"(?!.*\.\.)"  # Bucket name must not contain two adjacent periods
        r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]"  # Bucket naming constraints
        r"(?<!\.-$)"  # Bucket name must not end with a period followed by a hyphen
        r"(?<!\.$)"  # Bucket name must not end with a period
        r"(?<!-$)"  # Bucket name must not end with a hyphen
        r"(/([a-zA-Z0-9._-]+/?)*)?$"  # key naming constraints
    )
    url: str = Field(
        ...,
        json_schema_extra={"strip_whitespace": True},  # type: ignore
        pattern=_s3_pattern,
        min_length=8,
        max_length=1023,
    )

    def s3_url_parts(self):
        path_parts = self.url[5:].split("/")
        bucket = path_parts.pop(0)
        key = "/".join(path_parts)
        return (bucket, key)

    @property
    def bucket(self) -> str:
        return self.s3_url_parts()[0]

    @property
    def key(self) -> str:
        return self.s3_url_parts()[1]


class S3Storage(Storage):
    def __init__(
        self,
        path: str,
        s3_endpoint: HttpUrl,
        s3_kwargs: Optional[dict[str, Any]] = None,
    ):
        """S3 storage based on s3fs.

        Parameters
        ----------
        path:
            S3 path to the object (format: s3://bucket/name).
        s3_endpoint:
            URL to the S3 endpoint.
        s3_kwargs:
            Additional keyword arguments passed to obstore.S3Store.
            To use public access buckets without authentification, pass {"skip_signature": True}.
        """
        self._path = S3Path(url=path)
        self.endpoint = s3_endpoint
        s3_opts = s3_kwargs or {}
        self.store = connect_s3(path, s3_endpoint, s3_opts)
        if self.exists(str(self._path / ZARR_ROOT)):
            zarr_s3_opts = s3_opts | {"endpoint_url": str(s3_endpoint)}

            self._zarr = zarr.convenience.open(
                f"{self._path.url}/{ZARR_ROOT}",
                storage_options=zarr_s3_opts,
            )
        else:
            self.zarr_store = ObjectStore(store=self.store)
            self._zarr = init_zarr(self.zarr_store)

    @property
    def path(self) -> Path:
        return Path(f"{self._path.bucket}/{self._path.key}")

    @property
    def zarr(self) -> zh.Group:
        return self._zarr

    def exists(self, target: Path = ZARR_ROOT) -> bool:
        try:
            _ = obs.get(self.store, target)
            return True
        except FileNotFoundError:
            return False

    def list(
        self, target: Optional[Path] = None
    ) -> Generator[Path, None, None]:
        path = self.path / (target or "")
        for key in self.store.list(f"{path}/"):
            yield Path(key)

    def open(self, target: Path) -> io.BufferedReader:
        return obs.open_reader(self.store, path=str(self.path / target))

    def remove(self, target: Path):
        if self.exists(target):
            self.store.delete(str(target))
            logger.info(
                f"Permanently deleted {target} from remote filesystem."
            )

    def put(self, source: io.BufferedReader, target: Path):
        out_file = f"{self.path}/{target.as_posix()}"
        self.store.put(
            out_file, mode="wb", chunk_size=8192, use_multipart=True
        )

    def move(self, rel_source: Path, target: Path):
        self.store.rename(str(self.path / rel_source), str(self.path / target))


# Initialize object's directory given the metadata graph
def init_zarr(zarr_store: zarr.storage.Store) -> zh.Group:
    """Initialize object's directory and metadata structure."""
    data = zh.group(store=zarr_store)
    elem_types = [t.value for t in ElementType]
    for elem_type in elem_types:
        data.create_group(elem_type)

    return data


def connect_s3(
    path: str, endpoint: HttpUrl, s3_kwargs: dict[str, Any]
) -> S3Store:
    return S3Store.from_url(
        path,
        endpoint=str(endpoint),
        client_options={"allow_http": True},
        **s3_kwargs,
    )


def add_metadata_group(parent_group: zh.Group, metadata: dict) -> None:
    """Add input metadata dictionary to an existing zarr group."""
    # zarr groups cannot have slashes in their names
    group_name = metadata["id"].replace("/", "_")
    parent_group.create_group(group_name)
    # Fill attrs in the subject group for each predicate
    for key, value in metadata.items():
        if key == "id":
            continue
        parent_group[group_name].attrs[key] = value


def add_data(group: zh.Group, data) -> None:
    """Add a numpy array to an existing zarr group."""
    group.create_dataset("data", data=data)


def list_zarr_items(
    group: zh.Group,
) -> list[zh.Group | zarr.core.Array]:
    """Recursively list all zarr groups and arrays"""
    found = []

    def list_all(path: str, elem):
        found.append((path, elem))

    group.visititems(list_all)
    return found
