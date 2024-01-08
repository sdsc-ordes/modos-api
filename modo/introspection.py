"""Introspection utilities for the SMOC schema.

This module provides utilities for accessing the schema structure
and for converting instances to different representations.
"""
from functools import lru_cache, reduce
from pathlib import Path
from typing import Any, Optional

from linkml_runtime.dumpers import rdflib_dumper
from linkml_runtime.utils.schemaview import SchemaView
from rdflib import Graph
from rdflib.term import URIRef

import smoc_schema.schema as schema

SCHEMA_PATH = Path(schema.__path__[0]) / "smoc_schema.yaml"


@lru_cache(1)
def load_schema() -> SchemaView:
    """Return a view over the schema structure."""
    return SchemaView(SCHEMA_PATH)


@lru_cache(1)
def load_prefixmap() -> Any:
    """Load the prefixmap."""
    return SchemaView(SCHEMA_PATH, merge_imports=False).schema.prefixes


def get_slots(target_class: str, required_only=False) -> list[str]:
    """Return a list of required slots for a class."""
    required = []
    class_slots = load_schema().get_class(target_class).slots
    if not class_slots:
        return required

    # NOTE: May need to check inheritance and slot_usage
    for slot_name in class_slots:
        if not required_only or load_schema().get_slot(slot_name).required:
            required.append(slot_name)

    return required


def instance_to_graph(instance) -> Graph:
    # NOTE: This is a hack to get around the fact that the linkml
    # stores strings instead of URIRefs for prefixes.
    prefixes = {
        p.prefix_prefix: URIRef(p.prefix_reference)
        for p in load_prefixmap().values()
    }
    return rdflib_dumper.as_rdf_graph(
        instance,
        prefix_map=prefixes,
        schemaview=load_schema(),
    )


def get_slot_range(slot_name: str) -> str:
    """Return the range of a slot."""
    return load_schema().get_slot(slot_name).range


def get_class_uri(class_name: str) -> str:
    """Return the URI of a class."""
    return load_schema().get_class(class_name).uri


def get_class(class_name: str):
    """Return the URI of a class."""
    return load_schema().get_class(class_name)


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
        has_prop = load_schema().get_slot(prop_name)
        targets = has_prop.range
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
