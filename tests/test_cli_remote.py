"""Tests for the remote use of multi-omics digital object (modo) CLI"""

from typer.testing import CliRunner

from modos.cli import cli
import pytest
from pytest_httpserver import HTTPServer

runner = CliRunner()


@pytest.mark.remote
def test_create_modo_auth(setup, httpserver: HTTPServer):
    minio_endpoint = setup["minio"].get_config()["endpoint"]
    httpserver.expect_request("/").respond_with_json(
        {"status": "success", "s3": f"http://{minio_endpoint}"}
    )
    result = runner.invoke(
        cli,
        [
            "create",
            "-m",
            '{"id":"test", "creation_date": "2024-05-14", "last_update_date": "2024-05-14"}',
            "s3://test/ex_create",
        ],
        env={
            "AWS_ACCESS_KEY_ID": "minioadmin",
            "AWS_SECRET_ACCESS_KEY": "minioadmin",
            "MODOS_ENDPOINT": httpserver.url_for("/"),
        },
    )
    assert result.exit_code == 0


@pytest.mark.remote
def test_list_modo(httpserver: HTTPServer):
    httpserver.expect_request("/list").respond_with_json(
        {"data": ["s3://test/ex"]}
    )
    result = runner.invoke(
        cli,
        [
            "--endpoint",
            httpserver.url_for("/"),
            "--anon",
            "remote",
            "list",
        ],
    )
    assert result.exit_code == 0


def test_cli_stream_threads_secret_key(monkeypatch, tmp_path):
    """`modos remote stream` forwards the secret key to HtsgetConnection."""
    import io

    import modos.genomics.htsget as htsget_mod
    import modos.remote as remote_mod

    captured = {}

    class FakeConnection:
        def __init__(
            self, host, path, region=None, secret_key=None, passphrase=None
        ):
            captured["secret_key"] = secret_key
            captured["passphrase"] = passphrase

        def open(self):
            return io.BytesIO(b"")

    class FakeEndpoint:
        def __init__(self, *args, **kwargs):
            pass

        def __bool__(self):
            return True

        htsget = "http://htsget"

    monkeypatch.setattr(htsget_mod, "HtsgetConnection", FakeConnection)
    monkeypatch.setattr(remote_mod, "EndpointManager", FakeEndpoint)

    key = tmp_path / "key.sec"
    key.write_text("")
    pw = tmp_path / "pw.txt"
    pw.write_text("hunter2")
    result = runner.invoke(
        cli,
        [
            "--endpoint",
            "http://example.org",
            "remote",
            "stream",
            "--secret-key",
            str(key),
            "--passphrase",
            str(pw),
            "s3://bucket/ex",
            "demo1.cram",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["secret_key"] == key
    assert captured["passphrase"] == "hunter2"
