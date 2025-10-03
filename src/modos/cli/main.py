"""Basic CLI interface to create and interact with digital objects."""

# Use typer for CLI

import os
from pathlib import Path
from typing import Optional
from typing_extensions import Annotated

from loguru import logger
from pydantic import HttpUrl
import typer

from modos import __version__
from modos.cli.codes import codes
from modos.cli.c4gh import c4gh
from modos.cli.common import OBJECT_PATH_ARG, RdfFormat
from modos.cli.remote import remote
from modos.helpers.enums import UserElementType


cli = typer.Typer(add_completion=False)
cli.add_typer(
    c4gh,
    name="c4gh",
    short_help="Local encryption via crypt4gh.",
    rich_help_panel="Command groups",
)
cli.add_typer(
    remote,
    name="remote",
    short_help="Remote object management.",
    rich_help_panel="Command groups",
)
cli.add_typer(
    codes,
    name="codes",
    short_help="Terminology codes utilities.",
    rich_help_panel="Command groups",
)


def version_callback(value: bool):
    """Prints version and exits."""
    if value:
        print(f"modos {__version__}")
        # Exits successfully
        raise typer.Exit()


def anon_callback(ctx: typer.Context, anon: bool):
    """Validates modos server url"""
    ctx.ensure_object(dict)
    ctx.obj.setdefault("s3_kwargs", {})["anon"] = anon
    return anon


def endpoint_callback(ctx: typer.Context, url: HttpUrl):
    """Validates modos server url"""
    ctx.ensure_object(dict)
    ctx.obj["endpoint"] = url
    return url


@cli.command(rich_help_panel="Read")
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
    from modos.api import MODO

    endpoint = ctx.obj["endpoint"]
    if endpoint:
        obj = MODO(
            object_path,
            endpoint=endpoint,
            s3_kwargs=ctx.obj["s3_kwargs"],
        )
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


@cli.command(rich_help_panel="Read")
def publish(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    output_format: Annotated[RdfFormat, typer.Option(...)] = RdfFormat.TURTLE,
    base_uri: Annotated[Optional[str], typer.Option(...)] = None,
):
    """Export a modo as linked data. Turns all paths into URIs."""
    from modos.api import MODO

    obj = MODO(
        object_path,
        endpoint=ctx.obj["endpoint"],
        s3_kwargs=ctx.obj["s3_kwargs"],
    )
    print(
        obj.knowledge_graph(uri_prefix=base_uri).serialize(
            format=output_format
        )
    )


@cli.callback()
def callback(
    ctx: typer.Context,
    endpoint: Optional[str] = typer.Option(
        None,
        callback=endpoint_callback,
        envvar="MODOS_ENDPOINT",
        help="URL of modos server.",
    ),
    anon: Optional[bool] = typer.Option(
        False,
        "--anon",
        callback=anon_callback,
        envvar="MODOS_ANON",
        help="Use anonymous access for S3 connections.",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        help="Print version of modos client.",
    ),
    debug: Optional[bool] = typer.Option(
        None,
        "--debug",
        help="Enable debug logging.",
    ),
):
    """Multi-Omics Digital Objects command line interface."""
    from modos.logging import setup_logging

    if debug:
        setup_logging(level="DEBUG", diagnose=True, backtrace=True, time=True)
    else:
        setup_logging()


# Create command
@cli.command(rich_help_panel="Write")
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
    from linkml_runtime.loaders import json_loader
    import modos_schema.datamodel as model

    from modos.api import MODO
    from modos.prompt import SlotPrompter
    from modos.remote import EndpointManager
    from modos.storage import connect_s3

    typer.echo("Creating a digital object.", err=True)

    endpoint = EndpointManager(ctx.obj["endpoint"])

    # Initialize object's directory
    if endpoint.s3:
        fs = connect_s3(endpoint.s3, ctx.obj["s3_kwargs"])  # type: ignore
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
    MODO(
        path=object_path,
        endpoint=endpoint.modos,
        s3_kwargs=ctx.obj["s3_kwargs"],
        **attrs,
    )


@cli.command(rich_help_panel="Write")
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
    from modos.api import MODO
    import zarr

    modo = MODO(
        object_path,
        endpoint=ctx.obj["endpoint"],
        s3_kwargs=ctx.obj["s3_kwargs"],
    )
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


@cli.command(rich_help_panel="Write")
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
    from linkml_runtime.loaders import json_loader
    from modos.api import MODO
    from modos.io import parse_instance
    from modos.prompt import SlotPrompter
    from modos.remote import EndpointManager

    typer.echo(f"Updating {object_path}.", err=True)
    modo = MODO(
        object_path,
        endpoint=ctx.obj["endpoint"],
        s3_kwargs=ctx.obj["s3_kwargs"],
    )
    target_class = element_type.get_target_class()
    endpoint = EndpointManager(ctx.obj["endpoint"])

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


@cli.command(rich_help_panel="Write")
def enrich(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
):
    """Enrich metadata of a digital object using file contents."""
    from modos.api import MODO
    import zarr

    typer.echo(f"Enriching metadata for {object_path}.", err=True)
    modo = MODO(
        object_path,
        endpoint=ctx.obj["endpoint"],
        s3_kwargs=ctx.obj["s3_kwargs"],
    )
    # Attempt to extract metadata from files
    modo.enrich_metadata()
    zarr.consolidate_metadata(modo.zarr.store)


@cli.command(rich_help_panel="Write")
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
    from modos.api import MODO
    from modos.io import parse_attributes

    typer.echo(f"Updating {object_path}.", err=True)
    if force:
        _ = MODO.from_file(
            config_path=config_file,
            object_path=object_path,
            endpoint=ctx.obj["endpoint"],
            s3_kwargs=ctx.obj["s3_kwargs"],
            no_remove=False,
        )
    else:
        element_list = parse_attributes(Path(config_file))
        config_ids = [ele["element"].get("id") for ele in element_list]
        _ = MODO.from_file(
            config_path=config_file,
            object_path=object_path,
            endpoint=ctx.obj["endpoint"],
            s3_kwargs=ctx.obj["s3_kwargs"],
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
                logger.warning(
                    f"Keeping {old_id} in {modo_id}. Consider updating your config_file."
                )
                continue
            _.remove_element(meta_ids[old_id])


# Generate a click group to autogenerate docs via sphinx-click:
# https://github.com/tiangolo/typer/issues/200#issuecomment-795873331
typer_click_object = typer.main.get_command(cli)
