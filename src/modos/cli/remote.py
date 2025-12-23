import sys
from pathlib import Path
from typing_extensions import Annotated
from loguru import logger
import typer

from modos.remote import JWT, get_cache_dir
from modos.cli.common import OBJECT_PATH_ARG

remote = typer.Typer(add_completion=False)


@remote.command()
def login(
    ctx: typer.Context,
    client_id: Annotated[
        str | None,
        typer.Option(
            "--client-id",
            "-c",
            help="Specify OAuth Client ID explicitely.",
            envvar="MODOS_OAUTH_CLIENT_ID",
        ),
    ] = None,
    auth_url: Annotated[
        str | None,
        typer.Option(
            "--auth-url",
            "-a",
            help="Specify OAuth Authorization URL explicitely.",
            envvar="MODOS_OAUTH_AUTH_URL",
        ),
    ] = None,
):
    """Oauth device flow to login into a remote endpoint.

    Once the flow is completed, the JWT token is cached locally for future requests.
    The JWT is then used to request temporary S3 credentials from the remote endpoint.
    """
    from pyocli import start_device_code_flow, finish_device_code_flow
    import requests

    from modos.remote import EndpointManager

    endpoint = EndpointManager(ctx.obj["endpoint"])

    if endpoint is None:
        raise ValueError("Must provide an endpoint using modos --endpoint")

    # Try to get auth parameters from command line options
    if client_id and auth_url:
        pass
    elif endpoint.auth is None:
        raise ValueError(
            "The provided endpoint does not support authentication. Login not required."
        )
    else:
        auth_url = str(endpoint.auth["url"])
        client_id = str(endpoint.auth["client_id"])

    # Oauth device flow
    data = start_device_code_flow(
        auth_url,
        client_id,
        scopes=["profile", "offline_access", "permissions"],
    )

    print(f"To authenticate, visit {data.verify_url_full()}.")
    token = finish_device_code_flow(data)

    JWT(token.access_token).to_cache()  # TODO: Handle refresh token

    # Request temporary S3 credentials to test login
    resp = requests.get(
        url=f"{endpoint.kms}/create",
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    resp.raise_for_status()

    spec = resp.json()["spec"]
    access_key_id = resp.json()["access_key_id"]
    secret_access_key = resp.json()["secret_access_key"]
    with open(get_cache_dir() / "s3.env", "w") as f:
        _ = f.write(f"AWS_ACCESS_KEY_ID={access_key_id}\n")
        _ = f.write(f"AWS_SECRET_ACCESS_KEY={secret_access_key}\n")
    perm = ",".join([k for k, v in spec["permissions"].items() if v])
    logger.info("You are logged in")
    logger.info(f"S3 credentials valid until: {spec['expiration']}.")
    logger.info(f"{perm} access on s3://{spec['bucket']}.")


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
    object_path: OBJECT_PATH_ARG,
    file_path: Annotated[
        str,
        typer.Argument(
            ...,
            help="The path of the file to stream, within the modo. Use modos show --files to check it.",
        ),
    ],
    region: Annotated[
        str | None,
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
    source = Path(
        *Path(object_path.removeprefix("s3://")).parts[1:], file_path
    )
    endpoint = EndpointManager(ctx.obj["endpoint"])

    if not endpoint:
        raise ValueError("Streaming requires a remote endpoint.")

    if not endpoint.htsget:
        raise ValueError("No htsget service found.")

    con = HtsgetConnection(endpoint.htsget, source, _region)
    with con.open() as f:
        for chunk in f:
            sys.stdout.buffer.write(chunk)
