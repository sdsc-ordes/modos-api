from enum import Enum
from typing_extensions import Annotated

import typer


class RdfFormat(str, Enum):
    """Enumeration of RDF formats."""

    TURTLE = "turtle"
    RDF_XML = "xml"
    JSON_LD = "json-ld"


OBJECT_PATH_ARG = Annotated[
    str,
    typer.Argument(
        ...,
        help="Path to the digital object. Remote paths should have format s3://bucket/path",
    ),
]
