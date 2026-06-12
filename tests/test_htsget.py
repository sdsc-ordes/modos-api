"""Tests for the htsget client."""

import base64
from pathlib import Path

from crypt4gh.keys import get_public_key
from modos import remote
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


def test_ticket_sends_client_public_key(
    httpserver, c4gh_keypair, monkeypatch, tmp_path
):
    """The ticket request carries the client public key when encrypted."""
    # Avoid touching the real token cache (keep auth out of the way).
    monkeypatch.setattr(remote, "get_cache_dir", lambda: tmp_path)
    httpserver.expect_request("/reads/file").respond_with_json(
        {"htsget": {"urls": []}}
    )

    con = HtsgetConnection(
        host=httpserver.url_for("/"),
        path=Path("file.cram"),
        region=None,
        secret_key=c4gh_keypair["private_key"],
    )
    _ = con.ticket

    request, _ = httpserver.log[0]
    assert "Client-Public-Key" in request.headers
    sent = base64.b64decode(request.headers["Client-Public-Key"])
    assert sent == get_public_key(str(c4gh_keypair["public_key"]))


def test_ticket_omits_client_public_key_when_plaintext(
    httpserver, monkeypatch, tmp_path
):
    """No client key header is sent for a plaintext connection."""
    monkeypatch.setattr(remote, "get_cache_dir", lambda: tmp_path)
    httpserver.expect_request("/reads/file").respond_with_json(
        {"htsget": {"urls": []}}
    )

    con = HtsgetConnection(
        host=httpserver.url_for("/"), path=Path("file.cram"), region=None
    )
    _ = con.ticket

    request, _ = httpserver.log[0]
    assert "Client-Public-Key" not in request.headers


def test_open_decrypts_encrypted_stream(c4gh_keypair, tmp_path):
    """open() returns plaintext when a secret key is configured."""
    from modos.genomics.c4gh import encrypt_file

    payload = b"##fileformat=VCFv4.3\nchr1\t1\t.\tA\tT\t.\t.\t.\n" * 50
    plain_path = tmp_path / "payload.vcf"
    plain_path.write_bytes(payload)
    enc_path = tmp_path / "payload.vcf.c4gh"
    encrypt_file(c4gh_keypair["public_key"], plain_path, enc_path)

    block = base64.b64encode(enc_path.read_bytes()).decode()
    con = HtsgetConnection(
        host="http://localhost:8000",
        path=Path("payload.vcf"),
        region=None,
        secret_key=c4gh_keypair["private_key"],
    )
    # Inject the ticket directly to avoid an HTTP round-trip (cached_property).
    con.__dict__["ticket"] = {
        "htsget": {"urls": [{"url": f"data:;base64,{block}"}]}
    }

    with con.open() as handle:
        assert handle.read() == payload


def test_open_wraps_decryption_failure(c4gh_keypair):
    """A stream that is not valid crypt4gh raises a clear error."""
    import pytest

    block = base64.b64encode(b"not encrypted data").decode()
    con = HtsgetConnection(
        host="http://localhost:8000",
        path=Path("payload.vcf"),
        region=None,
        secret_key=c4gh_keypair["private_key"],
    )
    con.__dict__["ticket"] = {
        "htsget": {"urls": [{"url": f"data:;base64,{block}"}]}
    }

    with pytest.raises(ValueError, match="decrypt"):
        con.open()
