"""Common fixtures for testing"""

import modo_schema.datamodel as model
import pytest
import shutil

from modo.api import MODO
from modo.io import build_modo_from_file
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
    modo = build_modo_from_file(Path("data", "ex_config.yaml"), tmp_path)
    # TODO: This should be automatically copied. Remove when issue is solved!
    shutil.copyfile(
        Path("data", "ex", "demo1.cram.crai"), tmp_path / "demo1.cram.crai"
    )
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

minio = MinioContainer()


@pytest.fixture(scope="module")
def setup(request):
    minio.start()

    def remove_container():
        minio.stop()

    request.addfinalizer(remove_container)
    client = minio.get_client()
    client.make_bucket("test")


@pytest.fixture()
def remote_modo(setup):
    endpoint = minio.get_config()["endpoint"]
    return MODO(
        "test/ex",
        s3_endpoint="http://" + endpoint,
        s3_kwargs={"secret": "minioadmin", "key": "minioadmin"},
    )