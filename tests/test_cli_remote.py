"""Tests for the remote use of multi-omics digital object (modo) CLI"""

from typer.testing import CliRunner

from modos.cli import cli
import pytest
from pytest_httpserver import HTTPServer

runner = CliRunner()


@pytest.mark.slow
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
            "s3://test/ex",
        ],
        env={
            "AWS_ACCESS_KEY_ID": "minioadmin",
            "AWS_SECRET_ACCESS_KEY": "minioadmin",
            "MODOS_ENDPOINT": httpserver.url_for("/"),
        },
    )
    assert result.exit_code == 0


@pytest.mark.slow
def test_list_modo(httpserver: HTTPServer):
    httpserver.expect_request("/list").respond_with_json(
        {"modos": ["s3://test/ex"]}
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
