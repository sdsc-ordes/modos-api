"""Tests for the remote use of multi-omics digital object (modo) API"""

from modos.api import MODO

import modos_schema.datamodel as model
import pytest

## Instantiate multiple MODOs


@pytest.mark.slow
def test_multi_modos(setup):
    minio_endpoint = setup["minio"].get_config()["endpoint"]
    minio_creds = {"secret": "minioadmin", "key": "minioadmin"}
    for _ in range(3):
        MODO(
            "s3://test/ex",
            services={"s3": f"http://{minio_endpoint}"},
            s3_kwargs=minio_creds,
        )


## Add element


@pytest.mark.slow
def test_add_element(assay, remote_modo):
    remote_modo.add_element(assay)
    assert "assay/test_assay" in remote_modo.metadata.keys()


@pytest.mark.slow
def test_add_data(data_entity, remote_modo):
    remote_modo.add_element(data_entity, source_file="data/ex/demo1.cram")
    assert "demo1.cram" in [fi.name for fi in remote_modo.list_files()]
    assert "demo1.cram.crai" in [fi.name for fi in remote_modo.list_files()]


## Remove element


@pytest.mark.slow
def test_remove_element(sample, remote_modo):
    remote_modo.add_element(sample)
    assert "sample/test_sample" in remote_modo.list_samples()
    remote_modo.remove_element("sample/test_sample")
    assert "sample/test_sample" not in remote_modo.list_samples()


## Remove modo


@pytest.mark.slow
def test_remove_modo(setup):
    # NOTE: We build a new modo to prevent remote_modo from being deleted
    # in following tests.
    minio_client = setup["minio"].get_client()
    minio_endpoint = setup["minio"].get_config()["endpoint"]
    minio_creds = {"secret": "minioadmin", "key": "minioadmin"}
    modo = MODO(
        "s3://test/remove_ex",
        services={"s3": f"http://{minio_endpoint}"},
        s3_kwargs=minio_creds,
    )
    objects = minio_client.list_objects("test")
    assert "remove_ex/" in [o.object_name for o in objects]
    modo.remove_object()
    objects = minio_client.list_objects("test")
    assert "remove_ex/" not in [o.object_name for o in objects]


## Update element


@pytest.mark.slow
def test_update_element(sample, remote_modo):
    remote_modo.add_element(sample)
    test_sample = model.Sample(
        id="sample/test_sample", description="A fake sample for test purposes"
    )
    remote_modo.update_element("sample/test_sample", test_sample)
    assert (
        remote_modo.metadata["sample/test_sample"].get("description")
        == "A fake sample for test purposes"
    )


@pytest.mark.slow
def test_update_data_path_move(remote_modo, data_entity):
    data1 = model.DataEntity(
        id="data/test_data", data_format="CRAM", data_path="demo2.cram"
    )
    assert not remote_modo.storage.exists("demo2.cram")
    remote_modo.update_element("data/test_data", data1)
    assert remote_modo.storage.exists("demo2.cram")
    assert not remote_modo.storage.exists("demo1.cram")


@pytest.mark.slow
def test_update_source_file(remote_modo):
    data1 = model.DataEntity(
        id="data/test_data", data_format="CRAM", data_path="demo2.cram"
    )
    old_checksum = remote_modo.metadata.get("data/test_data").get(
        "data_checksum"
    )
    remote_modo.update_element(
        "data/test_data", data1, source_file="data/ex/demo1.cram.crai"
    )
    new_checksum = remote_modo.metadata.get("data/test_data").get(
        "data_checksum"
    )
    assert new_checksum != old_checksum


@pytest.mark.slow
def test_update_source_file_and_data_path(remote_modo):
    data2 = model.DataEntity(
        id="data/test_data", data_format="CRAM", data_path="demo1.cram"
    )
    remote_modo.update_element(
        "data/test_data", data2, source_file="data/ex/demo1.cram"
    )
    assert remote_modo.storage.exists("demo1.cram")
    assert not remote_modo.storage.exists("demo2.cram")


# Upload/download entire modo
@pytest.mark.slow
def test_upload_modo(setup, test_modo):
    minio_client = setup["minio"].get_client()
    minio_endpoint = setup["minio"].get_config()["endpoint"]
    minio_creds = {"secret": "minioadmin", "key": "minioadmin"}
    test_modo.upload(
        "s3://test/upload_ex", f"http://{minio_endpoint}", minio_creds
    )
    objects = minio_client.list_objects("test")
    assert "upload_ex/" in [o.object_name for o in objects]


@pytest.mark.slow
def test_download_modo(remote_modo, tmp_path):
    remote_modo.download(tmp_path / "download_ex")
    assert (tmp_path / "download_ex").exists()
