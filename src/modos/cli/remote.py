import sys
from typing import Optional
from pathlib import Path
from typing_extensions import Annotated
import typer

from modos.cli.common import OBJECT_PATH_ARG

remote = typer.Typer(add_completion=False)


@remote.command()
def download(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    target_path: Annotated[
        Path,
        typer.Option(
            "--target",
            "-t",
            help="Path where to download the digital object.",
            exists=False,
            dir_okay=True,
        ),
    ],
):
    """Download a modo from a remote endpoint."""
    from modos.api import MODO

    modo = MODO(
        object_path,
        endpoint=ctx.obj["endpoint"],
        s3_kwargs=ctx.obj["s3_kwargs"],
    )
    modo.download(target_path)


@remote.command()
def upload(
    ctx: typer.Context,
    object_path: OBJECT_PATH_ARG,
    target_path: Annotated[
        str,
        typer.Option(
            "--target",
            "-t",
            help="S3 path where to upload the digital object (format: s3://bucket/name).",
        ),
    ],
):
    """Upload a local modo to a remote endpoint."""
    from modos.api import MODO
    from modos.remote import EndpointManager

    modo = MODO(object_path)
    endpoint = EndpointManager(ctx.obj["endpoint"])
    modo.upload(target_path, endpoint.s3, s3_kwargs=ctx.obj["s3_kwargs"])


@remote.command()
def list(
    ctx: typer.Context,
):
    """List remote modos on the endpoint."""
    from modos.remote import list_remote_items

    if ctx.obj["endpoint"] is None:
        raise ValueError("Must provide an endpoint using modos --endpoint")

    for item in list_remote_items(ctx.obj["endpoint"]):
        print(item)


@remote.command()
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
    from modos.genomics.htsget import HtsgetConnection
    from modos.genomics.region import Region
    from modos.remote import EndpointManager

    _region = Region.from_ucsc(region) if region else None

    # NOTE: bucket is not included in htsget paths
    source = Path(*Path(file_path.removeprefix("s3://")).parts[1:])
    endpoint = EndpointManager(ctx.obj["endpoint"])

    if not endpoint:
        raise ValueError("Streaming requires a remote endpoint.")

    if not endpoint.htsget:
        raise ValueError("No htsget service found.")

    con = HtsgetConnection(endpoint.htsget, source, _region)
    with con.open() as f:
        for chunk in f:
            sys.stdout.buffer.write(chunk)
