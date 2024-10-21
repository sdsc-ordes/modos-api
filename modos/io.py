from pathlib import Path
import re
from typing import List

from linkml_runtime.loaders import (
    json_loader,
    yaml_loader,
    csv_loader,
    rdf_loader,
)
import modos_schema.datamodel as model
import pysam

from modos.genomics.cram import extract_cram_metadata
from modos.metabolomics.mztab import extract_mztab_metadata
from modos.helpers.schema import dict_to_instance

ext2loader = {
    "json": json_loader,
    r"ya?ml": yaml_loader,
    "csv": csv_loader,
    r"rdf|ttl|nt(riples)?": rdf_loader,
}


def get_loader(path: Path):
    """Get a loader based on the file extension using regex."""
    ext = path.suffix[1:]
    for pattern, loader in ext2loader.items():
        if re.match(pattern, ext):
            return loader
    return None


def parse_instance(path: Path, target_class):
    """Load a model of target_class from a file."""
    loader = get_loader(path)
    if not loader:
        raise ValueError(f"Unsupported file format: {path}")
    return loader.load(str(path), target_class)


def parse_attributes(path: Path) -> List[dict]:
    """Load model specification from file into a list of dictionaries. Model types must be specified as @type"""
    loader = get_loader(path)
    if not loader:
        raise ValueError(f"Unsupported file format: {path}")
    elems = loader.load_as_dict(str(path))
    if not isinstance(elems, list):
        elems = [elems]
    return elems


def parse_multiple_instances(path: Path) -> List:
    """Load one or more model from file. Model types must be specified as @type"""
    elems = parse_attributes(path)
    instances = []
    for elem in elems:
        instances.append(dict_to_instance(elem))
    return instances


def extract_metadata(instance, base_path: Path) -> List:
    """Extract metadata from files associated to a model instance"""
    if not isinstance(instance, model.DataEntity):
        raise ValueError(f"{instance} is not a DataEntity, cannot extract")

    match str(instance.data_format):
        case "mzTab":
            return extract_mztab_metadata(instance, base_path)
        case "CRAM":
            return extract_cram_metadata(instance, base_path)
        case _:
            raise NotImplementedError(
                f"Metadata extraction not implemented for this format: {instance.data_format}"
            )
