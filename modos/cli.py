"""Basic CLI interface to create and interact with digital objects."""

# Use typer for CLI

from datetime import date
from enum import Enum
import os
from pathlib import Path
from typing import Any, List, Mapping, Optional
from typing_extensions import Annotated

import click
from linkml_runtime.loaders import json_loader
import modos_schema.datamodel as model
from pydantic import validate_call, HttpUrl
import sys
import typer
from types import SimpleNamespace
import zarr

from .api import MODO
from .helpers.schema import (
    UserElementType,
    get_enum_values,
    get_slots,
    get_slot_range,
    load_schema,
)

from . import __version__
from .genomics.htsget import HtsgetConnection
from .genomics.region import Region
from .io import parse_instance
from .remote import EndpointManager
from .storage import connect_s3


class RdfFormat(str, Enum):
    """Enumeration of RDF formats."""

    TURTLE = "turtle"
    RDF_XML = "xml"
    JSON_LD = "json-ld"


cli = typer.Typer(add_completion=False)

OBJECT_PATH_ARG = Annotated[
    str,
    typer.Argument(
        ...,
        help="Path to the digital object. Remote paths should have format s3://bucket/path",
    ),
]


def prompt_for_slot(slot_name: str, prefix: str = "", optional: bool = False):
    """Prompt for a slot value."""
    slot_range = get_slot_range(slot_name)
    choices, default = None, None
    if slot_range == "datetime":
        default = date.today()
    elif load_schema().get_enum(slot_range):
        choices = click.Choice(get_enum_values(slot_range))
    elif optional:
        default = ""

    output = typer.prompt(
        f"{prefix}Enter a value for {slot_name}", default=default, type=choices
    )
    if output == "":
        output = None

    return output


def prompt_for_slots(
    target_class: type,
    exclude: Optional[Mapping[str, List]] = None,
    # add dict with exclude
) -> dict[str, Any]:
    """Prompt the user to provide values for the slots of input class.
    values of required fields can be excluded to repeat the prompt.

    Parameters
        ----------
        target_class
            Class to build
        exclude
            Mapping with the name of a slot as key  and list of invalid entries as values.
    """

    entries = {}
    required_slots = set(get_slots(target_class, required_only=True))
    optional_slots = (
        set(get_slots(target_class, required_only=False)) - required_slots
    )

    # Always require identifiers if possible
    if "id" in optional_slots:
        optional_slots.remove("id")
        required_slots.add("id")

    for slot_name in required_slots:
        entries[slot_name] = prompt_for_slot(slot_name, prefix="(required) ")
        if entries[slot_name] is None:
            raise ValueError(f"Missing required slot: {slot_name}")
        if exclude and entries.get(slot_name) in exclude.get(slot_name, []):
            print(
                f"Invalid value: {slot_name} must differ from {exclude[slot_name]}."
            )
            entries[slot_name] = prompt_for_slot(
                slot_name, prefix="(required) "
            )

    if optional_slots:
        for slot_name in optional_slots:
            entries[slot_name] = prompt_for_slot(
                slot_name,
                prefix="(optional) ",
                optional=True,
            )
    return entries


# Create command
@cli.command()
def create(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    from_file: Annotated[
        Optional[Path],
        typer.Option(
            "--from-file",
            "-f",
            help="Create a modo from a file. The file must be in json or yaml format.",
        ),
    ] = None,
    meta: Annotated[
        Optional[str],
        typer.Option(
            "--meta",
            "-m",
            help="Create instance from metadata provided as a json string.",
        ),
    ] = None,
):
    """Create a modo interactively or from a file."""
    typer.echo("Creating a digital object.", err=True)

    endpoint = ctx.obj.endpoint
    # Initialize object's directory
    if endpoint:
        s3 = EndpointManager(endpoint).s3
        fs = connect_s3(s3, {"anon": True})  # type: ignore
        if fs.exists(object_path):
            raise ValueError(f"Remote directory already exists: {object_path}")
    elif Path(object_path).exists():
        raise ValueError(f"Directory already exists: {object_path}")

    # Obtain object's metadata and create object
    if from_file and meta:
        raise ValueError("Only one of --from-file or --data can be used.")
    elif from_file:
        _ = MODO.from_file(from_file, object_path, endpoint=endpoint)
        return
    elif meta:
        obj = json_loader.loads(meta, target_class=model.MODO)
    else:
        filled = prompt_for_slots(model.MODO)
        obj = model.MODO(**filled)

    attrs = obj.__dict__
    # Dump object to zarr metadata
    MODO(path=object_path, endpoint=endpoint, **attrs)


@cli.command()
def remove(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    element_id: Annotated[
        str,
        typer.Argument(
            ...,
            help="The identifier within the modo. Use modos show to check it.",
        ),
    ],
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip confirmation for file deletion and allow deletion of the root object.",
        ),
    ] = False,
):
    """Removes an element and its files from the modo."""
    modo = MODO(object_path, endpoint=ctx.obj.endpoint)
    if element_id == modo.path.name:
        if force:
            modo.remove_object()
        else:
            raise ValueError(
                "Cannot delete root object. If you want to delete the entire MODOS, use --force."
            )
    else:
        element = modo.zarr[element_id]
        rm_path = element.attrs.get("data_path", [])
        if isinstance(element, zarr.hierarchy.Group) and len(rm_path) > 0:
            if not force:
                delete = typer.confirm(
                    f"Removing {element_id} will permanently delete {rm_path}.\n Please confirm that you want to continue?"
                )
                if not delete:
                    print(f"Stop removing element {element_id}!")
                    raise typer.Abort()
        modo.remove_element(element_id)


@cli.command()
def add(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    element_type: Annotated[
        UserElementType,
        typer.Argument(
            ...,
            help="Type of element to add to the digital object.",
        ),
    ],
    parent: Annotated[
        Optional[str],
        typer.Option(
            "--parent", "-p", help="Parent object in the zarr store."
        ),
    ] = None,
    element: Annotated[
        Optional[str],
        typer.Option(
            "--element",
            "-e",
            help="Create instance from element metadata provided as a json string.",
        ),
    ] = None,
    from_file: Annotated[
        Optional[Path],
        typer.Option(
            "--from-file",
            "-f",
            help="Include a data file associated with the instance. The file must be in json or yaml format.",
        ),
    ] = None,
    source_file: Annotated[
        Optional[Path],
        typer.Option(
            "--source-file",
            "-s",
            help="Specify a data file (if any) to copy into the digital object and associate with the instance.",
        ),
    ] = None,
):
    """Add elements to a modo."""

    typer.echo(f"Updating {object_path}.", err=True)
    modo = MODO(object_path, endpoint=ctx.obj.endpoint)
    target_class = element_type.get_target_class()

    if from_file and element:
        raise ValueError("Only one of --from-file or --element can be used.")
    elif from_file:
        obj = parse_instance(from_file, target_class=target_class)
    elif element:
        obj = json_loader.loads(element, target_class=target_class)
    else:
        exclude = {"id": [Path(id).name for id in modo.metadata.keys()]}
        filled = prompt_for_slots(target_class, exclude)
        obj = target_class(**filled)

    modo.add_element(obj, source_file=source_file, part_of=parent)


@cli.command()
def show(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    element_id: Annotated[
        Optional[str],
        typer.Argument(
            ...,
            help="The identifier within the modo. Use modos show to check it.",
        ),
    ] = None,
    zarr: Annotated[
        bool,
        typer.Option(
            "--zarr",
            "-z",
            help="Show the structure of the zarr archive",
        ),
    ] = False,
    files: Annotated[
        bool,
        typer.Option(
            "--files",
            "-f",
            help="Show data files in the digital object.",
        ),
    ] = False,
):
    """Show the contents of a modo."""
    endpoint = ctx.obj.endpoint
    if endpoint:
        obj = MODO(object_path, endpoint=endpoint)
    elif os.path.exists(object_path):
        obj = MODO(object_path)
    else:
        raise ValueError(f"{object_path} does not exists")
    if zarr:
        out = obj.list_arrays(element_id)
    elif files:
        out = "\n".join([str(path) for path in obj.list_files()])
    else:
        out = obj.show_contents(element_id)

    print(out)


@cli.command()
def publish(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    output_format: Annotated[RdfFormat, typer.Option(...)] = RdfFormat.TURTLE,
    base_uri: Annotated[Optional[str], typer.Option(...)] = None,
):
    """Export a modo as linked data. Turns all paths into URIs."""
    obj = MODO(object_path, endpoint=ctx.obj.endpoint)
    print(
        obj.knowledge_graph(uri_prefix=base_uri).serialize(
            format=output_format
        )
    )


@cli.command()
def stream(
    ctx: typer.Context,
    file_path: Annotated[
        str,
        typer.Argument(
            ...,
            help="The path to the file to stream . Use modos show --files to check it.",
        ),
    ],
    region: Annotated[
        Optional[str],
        typer.Option(
            "--region",
            "-r",
            help="Restrict stream to genomic region (chr:start-end).",
        ),
    ] = None,
):
    """Stream genomic file from a remote modo into stdout.


    Example:
    modos -e http://modos.example.org stream  my-bucket/ex-modo/demo1.cram
    """
    _region = Region.from_ucsc(region) if region else None

    # NOTE: bucket is not included in htsget paths
    source = Path(*Path(file_path).parts[1:])
    endpoint = ctx.obj.endpoint

    if not endpoint:
        raise ValueError("Streaming requires a remote endpoint.")

    htsget_endpoint = EndpointManager(endpoint).htsget  # type: ignore
    if not htsget_endpoint:
        raise ValueError("No htsget service found.")

    con = HtsgetConnection(htsget_endpoint, source, _region)
    with con.open() as f:
        for chunk in f:
            sys.stdout.buffer.write(chunk)


@cli.command()
def update(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    config_file: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="File defining the updated modo. The file must be in json or yaml format.",
        ),
    ],
    no_remove: Annotated[
        bool,
        typer.Option(
            "--no-remove",
            "-n",
            help="Do not remove elements that are missing in the config_file.",
        ),
    ] = False,
):
    """Update a modo based on a yaml file."""

    typer.echo(f"Updating {object_path}.", err=True)
    endpoint = ctx.obj.endpoint
    _ = MODO.from_file(
        config_path=config_file,
        object_path=object_path,
        endpoint=endpoint,
        no_remove=no_remove,
    )


def version_callback(value: bool):
    """Prints version and exits"""
    if value:
        print(f"modos {__version__}")
        # Exits successfully
        raise typer.Exit()


def endpoint_callback(ctx: typer.Context, url: HttpUrl):
    """Validates modos server url"""
    ctx.obj = SimpleNamespace(endpoint=url)


@cli.callback()
def callback(
    ctx: typer.Context,
    endpoint: Optional[str] = typer.Option(
        None,
        callback=endpoint_callback,
        envvar="MODOS_ENDPOINT",
        help="URL of modos server.",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        help="Print version of modos client",
    ),
):
    """Multi-Omics Digital Objects command line interface."""
    ...


# Generate a click group to autogenerate docs via sphinx-click:
# https://github.com/tiangolo/typer/issues/200#issuecomment-795873331

typer_click_object = typer.main.get_command(cli)
