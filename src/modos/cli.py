"""Basic CLI interface to create and interact with digital objects."""

# Use typer for CLI

from enum import Enum
import os
from pathlib import Path
from typing import Optional
from typing_extensions import Annotated

from linkml_runtime.loaders import json_loader
from loguru import logger
import modos_schema.datamodel as model
from pydantic import HttpUrl
import sys
import typer
from types import SimpleNamespace
import zarr

from modos import __version__
from modos.api import MODO
from modos.codes import get_slot_matcher, SLOT_TERMINOLOGIES
from modos.helpers.schema import UserElementType
from modos.genomics.htsget import HtsgetConnection
from modos.genomics.region import Region
from modos.io import parse_instance, parse_attributes
from modos.logging import setup_logging
from modos.prompt import SlotPrompter
from modos.remote import EndpointManager
from modos.prompt import fuzzy_complete
from modos.remote import list_remote_items
from modos.storage import connect_s3


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

    endpoint = EndpointManager(ctx.obj.endpoint)

    # Initialize object's directory
    if endpoint.s3:
        fs = connect_s3(endpoint.s3, {"anon": True})  # type: ignore
        if fs.exists(object_path):
            raise ValueError(f"Remote directory already exists: {object_path}")
    elif Path(object_path).exists():
        raise ValueError(f"Directory already exists: {object_path}")

    # Obtain object's metadata and create object
    if from_file and meta:
        raise ValueError("Only one of --from-file or --data can be used.")
    elif from_file:
        _ = MODO.from_file(from_file, object_path, endpoint=endpoint.modos)
        return
    elif meta:
        obj = json_loader.loads(meta, target_class=model.MODO)
    else:
        filled = SlotPrompter(endpoint, suggest=False).prompt_for_slots(
            model.MODO
        )
        obj = model.MODO(**filled)

    attrs = obj.__dict__
    # Dump object to zarr metadata
    MODO(path=object_path, endpoint=endpoint.modos, **attrs)


@cli.command()
def remove(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    element_id: Annotated[
        Optional[str],
        typer.Argument(
            ...,
            help="The identifier within the modo. Use modos show to check it. Leave empty to remove the whole object.",
        ),
    ] = None,
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
    if (element_id is None) or (element_id == modo.path.name):
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
                    logger.warning(f"Stop removing element {element_id}!")
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
            help="Read instance metadata from a file. The file must be in json or yaml format.",
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
    endpoint = EndpointManager(ctx.obj.endpoint)

    if from_file and element:
        raise ValueError("Only one of --from-file or --element can be used.")
    elif from_file:
        obj = parse_instance(from_file, target_class=target_class)
    elif element:
        obj = json_loader.loads(element, target_class=target_class)
    else:
        exclude = {"id": [Path(id).name for id in modo.metadata.keys()]}
        filled = SlotPrompter(endpoint).prompt_for_slots(target_class, exclude)
        obj = target_class(**filled)

    modo.add_element(obj, source_file=source_file, part_of=parent)


@cli.command()
def enrich(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
):
    """Enrich metadata of a digital object using file contents."""

    typer.echo(f"Enriching metadata for {object_path}.", err=True)
    modo = MODO(object_path, endpoint=ctx.obj.endpoint)
    # Attempt to extract metadata from files
    modo.enrich_metadata()
    zarr.consolidate_metadata(modo.zarr.store)


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
def list(
    ctx: typer.Context,
):
    """List remote modos on the endpoint."""
    if ctx.obj.endpoint is None:
        raise ValueError("Must provide an endpoint using modos --endpoint")

    for item in list_remote_items(ctx.obj.endpoint):
        print(item)


@cli.command()
def search_codes(
    ctx: typer.Context,
    slot: Annotated[
        str,
        typer.Argument(
            ...,
            help=f"The slot to search for codes. Possible values are {', '.join(SLOT_TERMINOLOGIES.keys())}",
        ),
    ],
    query: Annotated[
        Optional[str],
        typer.Option(
            "--query", "-q", help="Predefined text to use when search codes."
        ),
    ] = None,
    top: Annotated[
        int,
        typer.Option(
            "--top",
            "-t",
            help="Show at most N codes when using a prefedined query.",
        ),
    ] = 50,
):
    """Search for terminology codes using free text."""
    matcher = get_slot_matcher(
        slot,
        EndpointManager(ctx.obj.endpoint).fuzon,
    )
    matcher.top = top
    if query:
        matches = matcher.find_codes(query)
        out = "\n".join([f"{m.uri} | {m.label}" for m in matches])
    else:
        out = fuzzy_complete(
            prompt_txt=f'Browsing terms for slot "{slot}". Use tab to cycle suggestions.\n> ',
            matcher=matcher,
        )
    print(out)


@cli.command()
def stream(
    ctx: typer.Context,
    file_path: Annotated[
        str,
        typer.Argument(
            ...,
            help="The s3 path of the file to stream . Use modos show --files to check it.",
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
    """Stream genomic file from a remote modo into stdout."""
    _region = Region.from_ucsc(region) if region else None

    # NOTE: bucket is not included in htsget paths
    source = Path(*Path(file_path.removeprefix("s3://")).parts[1:])
    endpoint = EndpointManager(ctx.obj.endpoint)

    if not endpoint:
        raise ValueError("Streaming requires a remote endpoint.")

    if not endpoint.htsget:
        raise ValueError("No htsget service found.")

    con = HtsgetConnection(endpoint.htsget, source, _region)
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
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force deletion of elements that are missing in the config_file.",
        ),
    ] = False,
):
    """Update a modo based on a yaml file."""

    typer.echo(f"Updating {object_path}.", err=True)
    endpoint = ctx.obj.endpoint
    if force:
        _ = MODO.from_file(
            config_path=config_file,
            object_path=object_path,
            endpoint=endpoint,
            no_remove=False,
        )
    else:
        element_list = parse_attributes(Path(config_file))
        config_ids = [ele["element"].get("id") for ele in element_list]
        _ = MODO.from_file(
            config_path=config_file,
            object_path=object_path,
            endpoint=endpoint,
            no_remove=True,
        )
        modo_id = _.zarr["/"].attrs["id"]
        meta_ids = {Path(id).name: id for id in _.metadata.keys()}
        old_ids = [
            id
            for id in meta_ids.keys()
            if id not in config_ids and id != modo_id
        ]
        for old_id in old_ids:
            delete = typer.confirm(
                f"Object contains element '{old_id}' which was not in config_file.\n Delete {old_id} ?"
            )
            if not delete:
                print(
                    f"Keeping {old_id} in {modo_id}. Consider updating your config_file."
                )
                continue
            _.remove_element(meta_ids[old_id])


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
    debug: Optional[bool] = typer.Option(
        None,
        "--debug",
        help="Enable debug logging.",
    ),
):
    """Multi-Omics Digital Objects command line interface."""
    if debug:
        setup_logging(level="DEBUG", diagnose=True, backtrace=True, time=True)
    else:
        setup_logging()


# Generate a click group to autogenerate docs via sphinx-click:
# https://github.com/tiangolo/typer/issues/200#issuecomment-795873331

typer_click_object = typer.main.get_command(cli)
