"""Introspection utilities for the MODO schema.

This module provides helpers for accessing the schema structure
and for converting instances to different representations.
"""

from enum import Enum
from functools import lru_cache, reduce
from hashlib import file_digest
from io import RawIOBase
import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional, Union
from urllib.parse import urlparse

import zarr
from linkml_runtime.dumpers import rdflib_dumper, json_dumper
from linkml_runtime.utils.schemaview import SchemaView
from rdflib import Graph
from rdflib.term import URIRef

import modos_schema.datamodel as model
import modos_schema.schema as schema
import zarr.hierarchy

from modos.genomics.formats import (
    GenomicFileSuffix,
    add_suffix,
    get_index,
    is_encrypted,
    remove_suffix,
)
from modos.genomics.c4gh import encrypt_file, decrypt_file

SCHEMA_PATH = Path(schema.__path__[0]) / "modos_schema.yaml"


def class_from_name(name: str):
    class_names = list(load_schema().all_classes().keys())
    if name not in class_names:
        raise ValueError(f"Unknown class name: {name}")
    return getattr(model, name)


def dict_to_instance(element: Mapping[str, Any]) -> Any:
    elem_type = element.get("@type")
    target_class = class_from_name(elem_type)
    return target_class(
        **{k: v for k, v in element.items() if k not in "@type"}
    )


def update_metadata_from_model(
    group: zarr.hierarchy.group,
    element: model.DataEntity
    | model.Sample
    | model.Assay
    | model.ReferenceGenome,
):
    """Update the metadata of a zarr group with the metadata of a model element."""
    new = json.loads(json_dumper.dumps(element))

    # in the zarr store, empty properties are not stored
    # in the linkml model, they present as empty lists/None.
    new_items = {
        field: value
        for field, value in new.items()
        if (field, value) not in group.attrs.items()
        and field != "id"
        and value is not None
        and value != []
    }
    if not len(new_items):
        return
    group.attrs.update(**new_items)


def is_full_id(element_id: str) -> bool:
    """Checks if an element_id contains the element type as prefix.

    Examples
    --------
    >>> is_full_id("sample1")
    False
    >>> is_full_id("data/test")
    True
    >>> is_full_id("/assay/test_assay")
    True
    """
    etypes = [elem.value + "/" for elem in ElementType]
    extended_etypes = etypes + ["/" + etype for etype in etypes]
    return element_id.startswith(tuple(extended_etypes))


def set_haspart_relationship(
    child_class: str,
    child_path: str,
    parent_group: zarr.hierarchy.Group,
):
    """Add element to the hasPart attribute of a parent zarr group"""
    parent_type = getattr(
        model,
        parent_group.attrs.get("@type"),
    )

    has_prop = get_haspart_property(child_class)
    parent_slots = parent_type.__match_args__
    if has_prop not in parent_slots:
        raise ValueError(
            f"Cannot make {child_path} part of {parent_group.name}: {parent_type} does not have property {has_prop}"
        )
    # has_part is multivalued
    if has_prop not in parent_group.attrs:
        parent_group.attrs[has_prop] = []

    if isinstance(parent_group.attrs[has_prop], str):
        parent_group.attrs[has_prop] = [parent_group.attrs[has_prop]]

    parent_group.attrs[has_prop] += [child_path]


def update_haspart_id(
    element: model.DataEntity
    | model.Sample
    | model.Assay
    | model.ReferenceGenome
    | model.MODO,
):
    """update the id of the has_part property of an element to use the full id including its type"""
    haspart_names = load_schema().slot_children("has_part")
    haspart_list = [
        haspart for haspart in haspart_names if haspart in vars(element).keys()
    ]
    if len(haspart_list) > 0:
        for has_part in haspart_list:
            haspart_type = get_slot_range(has_part)
            type_name = ElementType.from_model_name(haspart_type).value
            updated_ids = [
                id if is_full_id(id) else f"{type_name}/{id}"
                for id in getattr(element, has_part)
            ]
            setattr(element, has_part, updated_ids)
    return element


def set_data_path(
    element: model.DataEntity, source_file: Optional[Union[Path, str]] = None
) -> model.DataEntity:
    """Set the data_path attribute, if it is not specified to the modo root."""
    if source_file and not element.get("data_path"):
        element["data_path"] = Path(source_file).name
    return element


class DataElement:
    """Facade class to wrap model DataEntity to facilitate file handling (including index files)."""

    def __init__(self, model: model.DataEntity, storage):
        self.model = model
        self.storage = storage

    def _set_metadata(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self.model, key, value)

    def _update_checksum(self, source_path: Path):
        with open(source_path, "rb") as src:
            source_checksum = compute_checksum(src)
        if source_checksum != self.model.data_checksum:
            self.model.data_checksum = source_checksum

    @property
    def is_genomic(self) -> bool:
        """Check if the data element is genomic."""
        return (
            self.model.data_format.code.text
            in GenomicFileSuffix.list_formats()
        )

    def add_file(self, source_path: Path, target_path: Path):
        """Add a file to target_path to the storage.
        If existing also add the index file and update data_path and checksum in metadata"""
        with open(source_path, "rb") as src:
            self.storage.put(src, target_path)

        source_idx = get_index(source_path)
        if source_idx:
            target_idx = get_index(target_path)
            with open(source_idx, "rb") as src:
                self.storage.put(src, target_idx)

        self._update_checksum(source_path)
        self._set_metadata(data_path=str(target_path))

    def move_file(self, target_path: Path):
        """Move a file from the path specified in metadata to the target_path.
        If existing also move the index file."""
        source_path = Path(self.model.data_path)
        self.storage.move(source_path, target_path)
        source_idx = get_index(source_path)
        if source_idx:
            target_idx = get_index(target_path)
            self.storage.move(source_idx, target_idx)

    def remove_file(self, rm_path: Path):
        """Remove a file and its related index from the storage."""
        self.storage.remove(rm_path)
        rm_idx = get_index(rm_path)
        if rm_idx:
            self.storage.remove(rm_idx)

    def update_file(
        self,
        new_path: Path,
        source_file: Path | None = None,
    ):
        """Update file, its corresponding index file and metadata, based on new data_path and source_file.

        There are four cases:
        1. Neither path nor contents changed --> do nothing.
        2. Only contents changed --> overwrite the file(s).
        3. Only path changed -> move file(s).
        4. Both path and contents changed -> add new file(s) and remove old ones.

        Parameters
        ----------
        new_path
            Path to where the file should be placed.
        source_file
            Path to the file that shall be added. If None the file already associated to the DataElement will be used.

        """
        old_path = Path(self.model.data_path)
        path_has_changed = new_path != old_path

        if source_file:
            old_checksum = self.model.data_checksum
            self._update_checksum(source_file)
            checksum_has_changed = old_checksum != self.model.data_checksum
        else:
            checksum_has_changed = False

        match path_has_changed, checksum_has_changed:
            case False, False:
                pass
            case False, True:
                self.add_file(Path(source_file), new_path)
            case True, False:
                self.move_file(new_path)
            case True, True:
                self.add_file(Path(source_file), new_path)
                self.remove_file(self.storage.path / old_path)

    def encrypt(
        self,
        recipient_pubkeys: list[os.PathLike] | os.PathLike,
        seckey_path: Optional[os.PathLike] = None,
        passphrase: Optional[str] = None,
        delete: bool = True,
    ):
        """
        Encrypt data path linked to the DataElement.
        Works for genomic files and their index files.
        """
        if not self.is_genomic:
            return

        data_path = Path(self.model.data_path)
        if is_encrypted(self.storage.path / data_path):
            return
        encrypted_path = add_suffix(data_path, ".c4gh")
        idx_path = get_index(data_path)
        for file_path in filter(None, [data_path, idx_path]):
            out_path = add_suffix(file_path, ".c4gh")
            encrypt_file(
                recipient_pubkeys=recipient_pubkeys,
                infile=self.storage.path / file_path,
                outfile=self.storage.path / out_path,
                seckey_path=seckey_path,
                passphrase=passphrase,
            )
            if delete:
                self.storage.remove(self.storage.path / file_path)
        self._update_checksum(self.storage.path / encrypted_path)
        self._set_metadata(data_path=str(encrypted_path))

    def decrypt(
        self,
        seckey_path: os.PathLike,
        sender_pubkey: Optional[os.PathLike] = None,
        passphrase: Optional[str] = None,
    ):
        """
        Decrypt data path linked to the DataElement.
        Works for genomic files and their index files.
        """
        data_path = Path(self.model.data_path)
        if not is_encrypted(self.storage.path / data_path):
            return
        if data_path.suffix != ".c4gh":
            raise ValueError(
                f"File {data_path} has unknown suffix.\n Please rename to .c4gh before decryption."
            )
        decrypted_path = remove_suffix(data_path, ".c4gh")
        idx_path = get_index(decrypted_path)
        if idx_path:
            idx_path = add_suffix(idx_path, ".c4gh")
        for file_path in filter(None, [data_path, idx_path]):
            out_path = remove_suffix(file_path, ".c4gh")
            decrypt_file(
                seckey_path=seckey_path,
                infile=self.storage.path / file_path,
                outfile=self.storage.path / out_path,
                sender_pubkey=sender_pubkey,
                passphrase=passphrase,
            )
            self.storage.remove(self.storage.path / file_path)
        self._update_checksum(self.storage.path / decrypted_path)
        self._set_metadata(data_path=str(decrypted_path))


def compute_checksum(file_obj: RawIOBase) -> str:
    """Generate the BLAKE2b checksum of the file_obj digest."""
    digest = file_digest(file_obj, "blake2b")
    return digest.hexdigest()


class UserElementType(str, Enum):
    """Enumeration of element types exposed to the user."""

    SAMPLE = "sample"
    ASSAY = "assay"
    DATA_ENTITY = "data"
    REFERENCE_GENOME = "reference"

    def get_target_class(
        self,
    ) -> type:
        """Return the target class for the element type."""
        match self:
            case UserElementType.SAMPLE:
                return model.Sample
            case UserElementType.ASSAY:
                return model.Assay
            case UserElementType.DATA_ENTITY:
                return model.DataEntity
            case UserElementType.REFERENCE_GENOME:
                return model.ReferenceGenome
            case _:
                raise ValueError(f"Unknown element type: {self}")

    @classmethod
    def from_object(cls, obj):
        """Return the element type from an object."""
        match obj:
            case model.Sample():
                return UserElementType.SAMPLE
            case model.Assay():
                return UserElementType.ASSAY
            case model.DataEntity():
                return UserElementType.DATA_ENTITY
            case model.ReferenceGenome():
                return UserElementType.REFERENCE_GENOME
            case _:
                raise ValueError(f"Unknown object type: {type(obj)}")


class ElementType(str, Enum):
    """Enumeration of all element types."""

    SAMPLE = "sample"
    ASSAY = "assay"
    DATA_ENTITY = "data"
    REFERENCE_GENOME = "reference"
    REFERENCE_SEQUENCE = "sequence"

    def get_target_class(
        self,
    ) -> type:
        """Return the target class for the element type."""
        match self:
            case ElementType.SAMPLE:
                return model.Sample
            case ElementType.ASSAY:
                return model.Assay
            case ElementType.DATA_ENTITY:
                return model.DataEntity
            case ElementType.REFERENCE_GENOME:
                return model.ReferenceGenome
            case ElementType.REFERENCE_SEQUENCE:
                return model.ReferenceSequence
            case _:
                raise ValueError(f"Unknown element type: {self}")

    @classmethod
    def from_object(cls, obj):
        """Return the element type from an object."""
        match obj:
            case model.Sample():
                return ElementType.SAMPLE
            case model.Assay():
                return ElementType.ASSAY
            case model.DataEntity():
                return ElementType.DATA_ENTITY
            case model.ReferenceGenome():
                return ElementType.REFERENCE_GENOME
            case model.ReferenceSequence():
                return ElementType.REFERENCE_SEQUENCE
            case _:
                raise ValueError(f"Unknown object type: {type(obj)}")

    @classmethod
    def from_model_name(cls, name: str):
        """Return the element type from an object name."""
        match name:
            case "Sample":
                return ElementType.SAMPLE
            case "Assay":
                return ElementType.ASSAY
            case "DataEntity":
                return ElementType.DATA_ENTITY
            case "ReferenceGenome":
                return ElementType.REFERENCE_GENOME
            case "ReferenceSequence":
                return ElementType.REFERENCE_SEQUENCE
            case _:
                raise ValueError(f"Unknown object type: {name}")


def is_uri(text: str):
    """Checks if input is a valid URI."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False


@lru_cache(1)
def load_schema() -> SchemaView:
    """Return a view over the schema structure."""
    return SchemaView(SCHEMA_PATH)


@lru_cache(1)
def load_prefixmap() -> Any:
    """Load the prefixmap."""
    return SchemaView(SCHEMA_PATH, merge_imports=False).schema.prefixes


def get_slots(target_class: type, required_only=False) -> list[str]:
    """Return a list of required slots for a class."""
    slots = []
    class_slots = target_class.__match_args__

    for slot_name in class_slots:
        if not required_only or load_schema().get_slot(slot_name).required:
            slots.append(slot_name)

    return slots


def instance_to_graph(instance) -> Graph:
    # NOTE: This is a hack to get around the fact that the linkml
    # stores strings instead of URIRefs for prefixes.
    prefixes = {
        p.prefix_prefix: URIRef(p.prefix_reference)
        for p in load_prefixmap().values()
    }
    g = rdflib_dumper.as_rdf_graph(
        instance,
        prefix_map=prefixes,
        schemaview=load_schema(),
    )
    # NOTE: This is a hack to get around the fact that the linkml's
    # rdf dumper does not iunclude schema:identifier in the graph.
    # Patch schema -> http://schema.org (rdflib's default is https)
    g.bind("schema", "http://schema.org/", replace=True)
    try:
        id_slot = (
            load_schema().get_identifier_slot(type(instance).__name__).slot_uri
        )
        g.add(
            (
                URIRef(instance.id),
                g.namespace_manager.expand_curie(str(id_slot)),
                URIRef(instance.id),
            )
        )
    except AttributeError:
        pass
    return g


def get_slot_range(slot_name: str) -> str:
    """Return the class-independent range of a slot."""
    return load_schema().get_slot(slot_name).range


def get_enum_values(enum_name: str) -> Optional[list[str]]:
    return list(load_schema().get_enum(enum_name).permissible_values.keys())


def get_haspart_property(child_class: str) -> Optional[str]:
    """Return the name of the "has_part" property for a target class.
    If no such property is in the schema, return None.

    Examples
    --------
    >>> get_haspart_property('AlignmentSet')
    'has_data'
    >>> get_haspart_property('Assay')
    'has_assay'
    """

    # find all subproperties of has_part
    prop_names = load_schema().slot_children("has_part")
    for prop_name in prop_names:
        targets = get_slot_range(prop_name)
        if isinstance(targets, str):
            targets = [targets]
        # When considering the slot range,
        # include subclasses or targets
        sub_targets = map(load_schema().get_children, targets)
        sub_targets = reduce(lambda x, y: x + y, sub_targets)
        all_targets = targets + [t for t in sub_targets if t]
        if child_class in all_targets:
            return prop_name
    return None
