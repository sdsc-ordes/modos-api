"""Tests consistency of modos metadata structure."""

from modos.api import MODO


def test_haspart_id_modos_init(tmp_path):
    modo = MODO.from_file("data/ex_config.yaml", tmp_path)
    assert "assay/assay1" in modo.metadata.keys()


def test_haspart_id_add_element(test_modo, assay):
    test_modo.add_element(assay)
    assert "assay/test_assay" in test_modo.metadata["ex"]["has_assay"]
