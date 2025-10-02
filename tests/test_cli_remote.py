"""Tests for the remote use of multi-omics digital object (modo) CLI"""

from typer.testing import CliRunner

from modos.cli import cli
import pytest

runner = CliRunner()


@pytest.mark.slow
def test_create_modo_auth(setup):
    minio_endpoint = setup["minio"].get_config()["endpoint"]
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
            "AWS_SECRET": "minioadmin",
            "MODOS_ENDPOINT": f"http://{minio_endpoint}",
        },
    )
    assert result.exit_code == 0


@pytest.mark.slow
def test_show_modo_anon(setup):
    endpoint = setup["minio"].get_config()["endpoint"]
    result = runner.invoke(
        cli,
        [
            "--endpoint",
            f"http://{endpoint}",
            "--anon",
            "create",
            "-m",
            '{"id":"test", "creation_date": "2024-05-14", "last_update_date": "2024-05-14"}',
            "s3://test/ex",
        ],
    )
    assert result.exit_code == 0
