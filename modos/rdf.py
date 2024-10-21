from linkml_runtime.loaders import json_loader
import rdflib
from .helpers.schema import (
    get_slot_range,
    instance_to_graph,
    load_prefixmap,
    load_schema,
)
from modos.helpers.schema import (
    is_uri,
    class_from_name,
)


def attrs_to_graph(meta: dict, uri_prefix: str) -> rdflib.Graph:
    """Convert a attribute dictionary to an RDF graph of metadata."""
    kg = rdflib.Graph()
    for prefix in load_prefixmap().values():
        kg.bind(prefix.prefix_prefix, prefix.prefix_reference, replace=True)

    # Assuming the dict is flat, i.e. all subjects are top level
    for subject, attrs in meta.items():
        if not is_uri(subject):
            subject = f"{uri_prefix}{subject}"
        for key, value in attrs.items():
            if key == "@type":
                continue
            # Check if slot value should be a URI
            # we need to ensure it is one
            slot_range = get_slot_range(key)
            if not slot_range:
                continue
            uri_value = any(
                [
                    "uri" in slot_range,
                    slot_range in load_schema().all_classes(),
                    key == "data_path",
                ]
            )
            if uri_value:
                # multivalued slots have a list of values
                if isinstance(value, list):
                    fixed = []
                    for item in value:
                        if is_uri(item):
                            fixed.append(item)
                        else:
                            fixed.append(f"{uri_prefix}{item}")
                else:
                    if is_uri(value):
                        fixed = value
                    else:
                        fixed = f"{uri_prefix}{value}"
                attrs[key] = fixed
        attrs["id"] = subject
        instance = json_loader.loads(
            attrs,
            target_class=class_from_name(attrs["@type"]),
        )
        kg += instance_to_graph(instance)
    return kg
