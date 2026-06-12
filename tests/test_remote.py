"""Tests for remote authentication handling."""

import jwt
import pytest
import requests

from modos import remote
from modos.remote import BearerAuth, JWT

# Far-future expiry so the token is never considered expired.
_FUTURE_EXP = 4102444800  # 2100-01-01 UTC


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Redirect the JWT cache to a temporary directory."""
    monkeypatch.setattr(remote, "get_cache_dir", lambda: tmp_path)
    return tmp_path


def test_bearer_auth_picks_up_token_cached_after_construction(cache_dir):
    """A session built before login must still send a token cached later."""
    auth = BearerAuth()  # constructed while logged out

    token = jwt.encode({"exp": _FUTURE_EXP}, "secret" * 8)
    JWT(token).to_cache()  # simulate a later login

    req = requests.Request("GET", "http://modos.example.org").prepare()
    auth(req)

    assert req.headers.get("Authorization") == f"Bearer {token}"
