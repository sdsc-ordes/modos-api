"""Tests for the local use of multi-omics digital object (modo) CLI"""

from typer.testing import CliRunner

from linkml_runtime.dumpers import json_dumper
from modos.api import MODO
from modos.cli import cli

runner = CliRunner()

## Initialize modo / modos create


def test_create_modo(tmp_path):
    result = runner.invoke(
        cli,
        [
            "create",
            "-m",
            '{"id":"test", "creation_date": "2024-05-14", "last_update_date": "2024-05-14"}',
            str(tmp_path) + "/test",
        ],
    )
    assert result.exit_code == 0


def test_create_modo_from_yaml(tmp_path):
    result = runner.invoke(
        cli, ["create", "-f", "data/ex_config.yaml", str(tmp_path) + "/test"]
    )
    assert result.exit_code == 0


## Add element / modos add


def test_add_element(tmp_path, assay):
    modo = MODO(tmp_path)
    assay_json = json_dumper.dumps(assay)
    result = runner.invoke(
        cli, ["add", "-e", assay_json, str(tmp_path), "assay"]
    )
    assert result.exit_code == 0
    assert "assay/test_assay" in modo.metadata.keys()


def test_add_data(tmp_path, data_entity):
    modo = MODO(tmp_path)
    result = runner.invoke(
        cli,
        [
            "add",
            "-e",
            json_dumper.dumps(data_entity),
            "-s",
            "data/ex/demo1.cram",
            str(tmp_path),
            "data",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "demo1.cram") in modo.list_files()
    assert (tmp_path / "demo1.cram.crai") in modo.list_files()


def test_add_to_parent(tmp_path, test_modo, sample):
    result = runner.invoke(
        cli,
        [
            "add",
            "-e",
            sample._as_json,
            "-p",
            "data/demo1",
            str(tmp_path),
            "sample",
        ],
    )
    assert result.exit_code == 0
    assert "sample/test_sample" in test_modo.metadata["data/demo1"].get(
        "has_sample"
    )


## Remove element


def test_remove_element(test_modo, tmp_path):
    assert "sample/sample1" in test_modo.list_samples()
    result = runner.invoke(cli, ["remove", str(tmp_path), "sample/sample1"])
    assert result.exit_code == 0
    assert "sample/sample1" not in test_modo.list_samples()


def test_remove_element_link_list(test_modo, tmp_path):
    assert "sample/sample1" in test_modo.zarr["data/demo1"].attrs.get(
        "has_sample"
    )
    result = runner.invoke(cli, ["remove", str(tmp_path), "sample/sample1"])
    assert result.exit_code == 0
    assert test_modo.zarr["data/demo1"].attrs["has_sample"] is None


## Remove modo


def test_remove_modo(test_modo, tmp_path):
    assert test_modo.path.exists()
    result = runner.invoke(
        cli, ["remove", "--force", str(tmp_path), test_modo.path.name]
    )
    assert result.exit_code == 0
    assert not test_modo.path.exists()


def test_not_remove_modo_without_force(test_modo, tmp_path):
    result = runner.invoke(cli, ["remove", str(tmp_path), test_modo.path.name])
    assert result.exit_code == 1
    assert isinstance(result.exception, ValueError)


## Encryption


def test_encrypt_modo(test_modo, c4gh_keypair, tmp_path):
    pk_path = c4gh_keypair["public_key"]
    result = runner.invoke(
        cli,
        [
            "c4gh",
            "encrypt",
            "--public-key",
            pk_path,
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "demo1.cram.c4gh").exists()
    assert not (tmp_path / "demo1.cram").exists()


## Decryption


def test_decrypt_modo(test_modo, c4gh_keypair, tmp_path):
    sk_path = c4gh_keypair["private_key"]
    result = runner.invoke(
        cli,
        [
            "c4gh",
            "decrypt",
            "--secret-key",
            sk_path,
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert not (tmp_path / "demo1.cram.c4gh").exists()
    assert (tmp_path / "demo1.cram").exists()
