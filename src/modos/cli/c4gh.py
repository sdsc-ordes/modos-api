from pathlib import Path
from typing import Optional
from typing_extensions import Annotated
import typer

from modos.cli.common import OBJECT_PATH_ARG

c4gh = typer.Typer(add_completion=False)


@c4gh.command()
def decrypt(
    object_path: OBJECT_PATH_ARG,
    secret_key: Annotated[
        Path,
        typer.Option(
            "--secret-key",
            "-s",
            help="Secret key of the recipient to decrypt files in the MODO.",
        ),
    ],
    passphrase: Annotated[
        Optional[Path],
        typer.Option(
            "--passphrase",
            "-pw",
            help="Path to file with passphrase to unlock secret key.",
        ),
    ] = None,
):
    """Decrypt a local MODO."""
    from modos.api import MODO

    modo = MODO(object_path)
    modo.decrypt(
        secret_key, passphrase=open(passphrase).read() if passphrase else None
    )


@c4gh.command()
def encrypt(
    object_path: OBJECT_PATH_ARG,
    public_key: Annotated[
        list[str],
        typer.Option(
            "--public-key",
            "-p",
            help="Public key(s) of the recipent(s) to decrypt files in the MODO.",
        ),
    ],
    secret_key: Annotated[
        Optional[str],
        typer.Option(
            "--secret-key",
            "-s",
            help="Secret key of the sender to encrypt files in the MODO.",
        ),
    ] = None,
    passphrase: Annotated[
        Optional[Path],
        typer.Option(
            "--passphrase",
            "-pw",
            help="Path to file with passphrase to unlock secret key.",
        ),
    ] = None,
):
    """Encrypt a local MODO."""
    from modos.api import MODO

    modo = MODO(object_path)
    modo.encrypt(
        public_key,
        secret_key,
        passphrase=open(passphrase).read() if passphrase else None,
    )
