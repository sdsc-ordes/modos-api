"""Tests for crypt4gh helpers."""

from crypt4gh.keys import get_private_key, get_public_key

from modos.genomics.c4gh import derive_public_key


def test_derive_public_key_matches_keypair(c4gh_keypair):
    """The derived public key equals the keypair's own public key."""
    seckey = get_private_key(str(c4gh_keypair["private_key"]), lambda: None)
    expected = get_public_key(str(c4gh_keypair["public_key"]))

    assert derive_public_key(seckey) == expected
