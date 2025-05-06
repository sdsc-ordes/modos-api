"""crypt4gh implementation

Crypt4gh allows envelop encryption of genomic files. See [1]_ for more details.

Here we use the crypt4gh python [2]_ implementation to allow de/encryption of genomic files within modos.

References
----------

.. [1] https://samtools.github.io/hts-specs/crypt4gh.pdf
.. [2] https://github.com/EGA-archive/crypt4gh
"""

from typing import List, Optional, Set, Tuple
import os
from pathlib import Path

from crypt4gh.keys import get_public_key, get_private_key
from crypt4gh.lib import decrypt, encrypt
from functools import partial
from getpass import getpass
from nacl.public import PrivateKey


def get_secret_key(
    seckey_path: Optional[os.PathLike] = None,
    generate: bool = True,
    passphrase: Optional[str] = None,
) -> bytes:
    # auto generate a secret key
    if generate and seckey_path is None:
        sk = PrivateKey.generate()
        return bytes(sk)

    # get user secre tkey
    seckey_path = os.path.expanduser(seckey_path)
    if not os.path.exists(seckey_path):
        raise ValueError("Secret key not found")

    # in case it is passphrase protected
    if passphrase:
        cb = lambda: passphrase
    else:
        cb = partial(getpass, prompt=f"Passphrase for {seckey_path}: ")

    return get_private_key(seckey_path, cb)


def get_keys(
    recipient_pubkeys: List[os.PathLike] | os.PathLike, seckey: bytes
) -> Set[Tuple[int, bytes, bytes]]:
    if not isinstance(recipient_pubkeys, List):
        recipient_pubkeys = [recipient_pubkeys]
    # get recepient public key(s) and generate "key tuple":
    # keys = (method, privkey, recipient_pubkey=None)
    recipient_list = []
    for pubkey in recipient_pubkeys:
        pubkey_path = os.path.expanduser(pubkey)
        if not os.path.exists(pubkey_path):
            raise ValueError(f"Recipient public key not found: {pubkey}")
        recipient_list.append((0, seckey, get_public_key(pubkey_path)))

    return set(recipient_list)


def encrypt_file(
    recipient_pubkeys: List[os.PathLike] | os.PathLike,
    infile: Path | str,
    outfile: Path | str,
    seckey_path: Optional[os.PathLike] = None,
    passphrase: Optional[str] = None,
):
    seckey = get_secret_key(seckey_path, passphrase=passphrase)
    keys = get_keys(recipient_pubkeys, seckey)
    with open(infile, "rb") as input, open(outfile, "wb") as output:
        encrypt(keys=keys, infile=input, outfile=output)


def decrypt_file(
    seckey_path: os.PathLike,
    infile: Path | str,
    outfile: Path | str,
    sender_pubkey: Optional[os.PathLike] = None,
    passphrase: Optional[str] = None,
):
    seckey = get_secret_key(seckey_path, generate=False, passphrase=passphrase)
    keys = [
        (0, seckey, None)
    ]  # keys = list of (method, privkey, recipient_pubkey=None)
    if sender_pubkey:
        sender_pubkey = os.path.expanduser(sender_pubkey)

    with open(infile, "rb") as input, open(outfile, "wb") as output:
        decrypt(
            keys=keys,
            infile=input,
            outfile=output,
            sender_pubkey=sender_pubkey,
        )
