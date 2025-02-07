"""Common fixtures for testing"""

import modos_schema.datamodel as model
import pytest
import shutil

from modos.api import MODO
from pathlib import Path
from testcontainers.minio import MinioContainer

## Add --runslow option
# see: https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


## Test instances


# A test MODO
@pytest.fixture
def test_modo(tmp_path):
    modo = MODO.from_file(Path("data", "ex_config.yaml"), tmp_path)
    return modo


# different schema entities
@pytest.fixture
def data_entity():
    return model.DataEntity(
        id="test_data",
        name="test_data",
        data_path="demo1.cram",
        data_format="CRAM",
    )


@pytest.fixture
def assay():
    return model.Assay(
        id="test_assay", name="test_assay", omics_type="GENOMICS"
    )


@pytest.fixture
def sample():
    return model.Sample(
        id="test_sample",
        name="test_sample",
        cell_type="Leukocytes",
        taxon_id="9606",
    )


## testcontainers setup
# minio

minio = MinioContainer(
    image="minio/minio:RELEASE.2025-02-03T21-03-04Z"
).with_env("AWS_REQUEST_CHECKSUM_CALCULATION", "WHEN_REQUIRED")


@pytest.fixture(scope="module")
def setup(request):
    minio.start()

    def remove_container():
        minio.stop()

    request.addfinalizer(remove_container)
    client = minio.get_client()
    client.make_bucket("test")
    yield {"minio": minio}


@pytest.fixture()
def remote_modo(setup):
    minio_endpoint = setup["minio"].get_config()["endpoint"]
    minio_creds = {"secret": "minioadmin", "key": "minioadmin"}
    return MODO(
        "s3://test/ex",
        services={"s3": f"http://{minio_endpoint}"},
        s3_kwargs=minio_creds,
    )
