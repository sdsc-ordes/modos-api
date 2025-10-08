import sys
from typing import Optional
from pathlib import Path
from typing_extensions import Annotated
from loguru import logger
import typer

from modos.remote import JWT
from modos.cli.common import OBJECT_PATH_ARG

remote = typer.Typer(add_completion=False)


@remote.command()
def login(
    ctx: typer.Context,
    client_id: Annotated[
        str,
        typer.Option(
            "--client-id",
            "-c",
            help="OAuth Client ID to use for authentication.",
            envvar="MODOS_OAUTH_CLIENT_ID",
        ),
    ],
    auth_url: Annotated[
        str,
        typer.Option(
            "--auth-url",
            "-a",
            help="OAuth Authorization URL to use for authentication.",
            envvar="MODOS_OAUTH_AUTH_URL",
        ),
    ],
):
    """Oauth device flow to login into a remote endpoint."""
    from pyocli import start_device_code_flow, finish_device_code_flow

    data = start_device_code_flow(auth_url, client_id, [])
    print(f"To authenticate, visit {data.verify_url_full()}.")
    token = finish_device_code_flow(data)

    JWT(token.access_token).to_cache()  # TODO: Handle refresh token

    logger.info("You are logged in")


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
