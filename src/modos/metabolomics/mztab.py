"""Module for extracting metabolomics metadata from mzTab-M 2.0 files."""

from pathlib import Path
import re

import pandas as pd
from pyteomics.mztab import MzTab
import modos_schema.datamodel as model


def load_mztab(path: Path) -> MzTab:
    return MzTab(str(path))


def get_samples(mz: MzTab) -> list[model.Sample]:
    samples = []
    for _, sample in mz.samples.items():
        samples.append(
            model.Sample(
                id=sample["name"],
                description=sample["description"],
                taxon_id=sample.get("species", None),
                cell_type=sample.get("cell_type", None),
                source_material=sample.get("tissue", None),
            )
        )
    return samples


def get_assay(mz: MzTab, data_id: str) -> model.Assay:
    meta = mz.metadata
    assay = model.Assay(
        id=meta["mzTab-ID"],
        name=meta.get("title", None),
        description=meta.get("description", None),
        has_data=data_id,
        has_sample=[sample["name"] for sample in mz.samples.values()],
        omics_type="METABOLOMICS"
        if re.match(r".*-M", mz.version)
        else "PROTEOMICS",
        sample_processing=meta.get("sample_processing", None),
    )
    return assay


def extract_metadata(
    instance: model.MassSpectrometryResults, base_path: Path
) -> list[model.Assay | model.Sample]:
    mz = load_mztab(base_path / instance.data_path)
    elems = []
    elems.extend(get_samples(mz))
    elems.append(get_assay(mz, instance.id))
    return elems


def extract_tables(path: Path) -> dict[str, pd.DataFrame]:
    mz = load_mztab(path)
    return {table: mz[table] for table in ("SME", "SMF", "SML")}
