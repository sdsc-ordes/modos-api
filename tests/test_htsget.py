"""Tests for the htsget client."""

from pathlib import Path

from modos.genomics.htsget import HtsgetConnection, build_htsget_url
from modos.genomics.region import Region


def test_build_url_adds_encryption_scheme_when_encrypted():
    url = build_htsget_url(
        "http://localhost:8000",
        Path("file.cram"),
        Region("chr1", 0, 1000),
        encrypted=True,
    )
    assert url.endswith("&encryptionScheme=C4GH")


def test_build_url_omits_encryption_scheme_by_default():
    url = build_htsget_url("http://localhost:8000", Path("file.cram"), None)
    assert "encryptionScheme" not in url


def test_connection_url_reflects_secret_key(tmp_path):
    encrypted = HtsgetConnection(
        host="http://localhost:8000",
        path=Path("file.cram"),
        region=None,
        secret_key=tmp_path / "key.sec",
    )
    plain = HtsgetConnection(
        host="http://localhost:8000", path=Path("file.cram"), region=None
    )
    assert "encryptionScheme=C4GH" in encrypted.url
    assert "encryptionScheme" not in plain.url
