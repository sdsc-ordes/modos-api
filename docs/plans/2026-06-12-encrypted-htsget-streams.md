# Encrypted htsget streams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `modos` stream and decrypt crypt4gh-encrypted genomic regions from an htsget-rs server, given the user's secret key.

**Architecture:** Decryption happens at the `HtsgetConnection.open()` boundary. When a secret key is configured, the ticket request carries a `Client-Public-Key` header (derived from the secret key) plus an `encryptionScheme=C4GH` query parameter, and `open()` returns a plaintext file handle. Every downstream consumer (CLI stdout loop, `to_pysam`, `to_file`) is unchanged and transparently receives plaintext. The CLI `modos remote stream` command and the Python `MODO.stream_genomics` method thread the key straight through.

**Tech Stack:** Python 3.12+, crypt4gh (`crypt4gh.lib.decrypt`), PyNaCl (`nacl.public.PrivateKey`), requests, pysam, typer, pytest + pytest-httpserver, uv.

Reference spec: `docs/specs/2026-06-12-encrypted-htsget-streams-design.md`

---

## File Structure

- **Modify** `src/modos/genomics/c4gh.py` — add `derive_public_key(seckey: bytes) -> bytes`.
- **Modify** `src/modos/genomics/htsget.py` — encryption negotiation on the ticket request and decryption in `open()`.
- **Modify** `src/modos/api.py` — `stream_genomics` gains `secret_key`/`passphrase`, threaded to `HtsgetConnection`.
- **Modify** `src/modos/cli/remote.py` — `stream` command gains `--secret-key`/`--passphrase`.
- **Create** `tests/test_c4gh.py` — unit test for `derive_public_key`.
- **Create** `tests/test_htsget.py` — negotiation + decryption round-trip tests.
- **Modify** `tests/test_api_local.py` — composition test for `stream_genomics` wiring.
- **Modify** `tests/test_cli_remote.py` — composition test for CLI `stream` wiring.
- **Modify** `docs/tutorials/genomics_streaming.md` — document encrypted streaming.

Validation commands (run from the git root):
- Test a file: `uv run pytest tests/test_htsget.py -v`
- Format: `uv run ruff format <files>`
- Lint: `uv run ruff check <files>`

Commits are blocked by a pre-commit hook that needs the venv on PATH. Commit with:
`PATH="$PWD/.venv/bin:$PATH" git commit -m "..."`

---

### Task 1: Derive public key from secret key

**Files:**
- Modify: `src/modos/genomics/c4gh.py`
- Test: `tests/test_c4gh.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_c4gh.py`:

```python
"""Tests for crypt4gh helpers."""

from crypt4gh.keys import get_private_key, get_public_key

from modos.genomics.c4gh import derive_public_key


def test_derive_public_key_matches_keypair(c4gh_keypair):
    """The derived public key equals the keypair's own public key."""
    seckey = get_private_key(str(c4gh_keypair["private_key"]), lambda: None)
    expected = get_public_key(str(c4gh_keypair["public_key"]))

    assert derive_public_key(seckey) == expected
```

(The `c4gh_keypair` fixture already exists in `tests/conftest.py` and generates an unencrypted keypair.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_c4gh.py -v`
Expected: FAIL with `ImportError: cannot import name 'derive_public_key'`.

- [ ] **Step 3: Write minimal implementation**

In `src/modos/genomics/c4gh.py`, add after the existing imports/`get_secret_key` (the module already has `from nacl.public import PrivateKey`):

```python
def derive_public_key(seckey: bytes) -> bytes:
    """Derive the raw 32-byte X25519 public key from secret key bytes.

    Used to advertise the client public key to an htsget server via the
    Client-Public-Key header without requiring a separate public key file.
    """
    return bytes(PrivateKey(seckey).public_key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_c4gh.py -v`
Expected: PASS

- [ ] **Step 5: Format, lint, commit**

```bash
uv run ruff format src/modos/genomics/c4gh.py tests/test_c4gh.py
uv run ruff check src/modos/genomics/c4gh.py tests/test_c4gh.py
PATH="$PWD/.venv/bin:$PATH" git add src/modos/genomics/c4gh.py tests/test_c4gh.py
PATH="$PWD/.venv/bin:$PATH" git commit -m "feat(c4gh): derive public key from secret key"
```

---

### Task 2: Add encryption negotiation to the htsget URL

**Files:**
- Modify: `src/modos/genomics/htsget.py` (`build_htsget_url`, `HtsgetConnection` fields + `url` property)
- Test: `tests/test_htsget.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_htsget.py`:

```python
"""Tests for the htsget client."""

from pathlib import Path

from modos.genomics.htsget import HtsgetConnection, build_htsget_url
from modos.genomics.region import Region


def test_build_url_adds_encryption_scheme_when_encrypted():
    url = build_htsget_url(
        "http://localhost:8000",
        Path("file.cram"),
        Region("chr1", 0, 1000),
        encrypted=True,
    )
    assert url.endswith("&encryptionScheme=C4GH")


def test_build_url_omits_encryption_scheme_by_default():
    url = build_htsget_url(
        "http://localhost:8000", Path("file.cram"), None
    )
    assert "encryptionScheme" not in url


def test_connection_url_reflects_secret_key(tmp_path):
    encrypted = HtsgetConnection(
        host="http://localhost:8000",
        path=Path("file.cram"),
        region=None,
        secret_key=tmp_path / "key.sec",
    )
    plain = HtsgetConnection(
        host="http://localhost:8000", path=Path("file.cram"), region=None
    )
    assert "encryptionScheme=C4GH" in encrypted.url
    assert "encryptionScheme" not in plain.url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_htsget.py -v`
Expected: FAIL — `build_htsget_url() got an unexpected keyword argument 'encrypted'` and `HtsgetConnection` has no `secret_key` field.

- [ ] **Step 3: Write minimal implementation**

In `src/modos/genomics/htsget.py`, change `build_htsget_url` to accept `encrypted` (note the new parameter and the appended query):

```python
@validate_call
def build_htsget_url(
    host: HttpUrl,
    path: Path,
    region: Region | None,
    encrypted: bool = False,
) -> str:
    """Build an htsget URL from a host, path, and region.

    Examples
    --------
    >>> build_htsget_url(
    ...   "http://localhost:8000",
    ...   Path("file.bam"),
    ...   Region("chr1", 0, 1000)
    ... )
    'http://localhost:8000/reads/file?format=BAM&referenceName=chr1&start=0&end=1000'
    """
    format = GenomicFileSuffix.from_path(path)
    endpoint = format.to_htsget_endpoint()

    # remove .gz suffix if present
    stem = path.with_suffix("") if path.name.endswith("gz") else path
    stem = stem.with_suffix("")

    netloc = host if str(host).endswith("/") else f"{host}/"
    url = f"{netloc}{endpoint}/{stem}?format={format.name}"
    if region:
        url += f"&{region.to_htsget_query()}"
    if encrypted:
        url += "&encryptionScheme=C4GH"
    return url
```

Add the new fields and `_encrypted` property to `HtsgetConnection` (immediately after the `region: Region | None` field declaration):

```python
    host: HttpUrl
    path: Path
    region: Region | None
    secret_key: Path | None = None
    passphrase: str | None = None

    @property
    def _encrypted(self) -> bool:
        return self.secret_key is not None
```

Update the `url` property to pass the flag:

```python
    @property
    def url(self) -> str:
        """URL to fetch the ticket."""
        return build_htsget_url(
            self.host, Path(self.path), self.region, encrypted=self._encrypted
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_htsget.py -v`
Expected: PASS (3 tests). Also run the htsget doctests to confirm the unchanged example still holds:
Run: `uv run pytest --doctest-modules src/modos/genomics/htsget.py -v`
Expected: PASS

- [ ] **Step 5: Format, lint, commit**

```bash
uv run ruff format src/modos/genomics/htsget.py tests/test_htsget.py
uv run ruff check src/modos/genomics/htsget.py tests/test_htsget.py
PATH="$PWD/.venv/bin:$PATH" git add src/modos/genomics/htsget.py tests/test_htsget.py
PATH="$PWD/.venv/bin:$PATH" git commit -m "feat(htsget): negotiate C4GH encryption scheme in url"
```

---

### Task 3: Send the Client-Public-Key header on the ticket request

**Files:**
- Modify: `src/modos/genomics/htsget.py` (imports, `_seckey`, `_client_public_key`, `ticket`)
- Test: `tests/test_htsget.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_htsget.py` (add `import base64` and `from modos import remote` to the existing imports at the top of the file):

```python
def test_ticket_sends_client_public_key(httpserver, c4gh_keypair, monkeypatch, tmp_path):
    """The ticket request carries the derived client public key when encrypted."""
    # Avoid touching the real token cache (keep auth out of the way).
    monkeypatch.setattr(remote, "get_cache_dir", lambda: tmp_path)
    httpserver.expect_request("/reads/file").respond_with_json(
        {"htsget": {"urls": []}}
    )

    con = HtsgetConnection(
        host=httpserver.url_for("/"),
        path=Path("file.cram"),
        region=None,
        secret_key=c4gh_keypair["private_key"],
    )
    _ = con.ticket

    request, _ = httpserver.log[0]
    assert "Client-Public-Key" in request.headers
    sent = base64.b64decode(request.headers["Client-Public-Key"])
    from crypt4gh.keys import get_public_key

    assert sent == get_public_key(str(c4gh_keypair["public_key"]))


def test_ticket_omits_client_public_key_when_plaintext(
    httpserver, monkeypatch, tmp_path
):
    """No client key header is sent for a plaintext connection."""
    monkeypatch.setattr(remote, "get_cache_dir", lambda: tmp_path)
    httpserver.expect_request("/reads/file").respond_with_json(
        {"htsget": {"urls": []}}
    )

    con = HtsgetConnection(
        host=httpserver.url_for("/"), path=Path("file.cram"), region=None
    )
    _ = con.ticket

    request, _ = httpserver.log[0]
    assert "Client-Public-Key" not in request.headers
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_htsget.py::test_ticket_sends_client_public_key -v`
Expected: FAIL — the request has no `Client-Public-Key` header (header not yet sent).

- [ ] **Step 3: Write minimal implementation**

In `src/modos/genomics/htsget.py`, add to the imports near the other `modos.genomics` imports (`base64` and `cached_property` are already imported):

```python
from modos.genomics.c4gh import derive_public_key, get_secret_key
```

Add a cached secret key and a header helper to `HtsgetConnection` (place next to the other properties):

```python
    @cached_property
    def _seckey(self) -> bytes:
        return get_secret_key(self.secret_key, self.passphrase)

    def _client_public_key(self) -> str:
        """Base64-encoded public key for the Client-Public-Key header."""
        return base64.b64encode(derive_public_key(self._seckey)).decode()
```

Update the `ticket` cached property to attach the header when encrypted:

```python
    @cached_property
    def ticket(self) -> dict[str, Any]:
        """Ticket containing the URLs to fetch the data."""
        headers = {}
        if self._encrypted:
            headers["Client-Public-Key"] = self._client_public_key()
        return get_session().get(self.url, headers=headers).json()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_htsget.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Format, lint, commit**

```bash
uv run ruff format src/modos/genomics/htsget.py tests/test_htsget.py
uv run ruff check src/modos/genomics/htsget.py tests/test_htsget.py
PATH="$PWD/.venv/bin:$PATH" git add src/modos/genomics/htsget.py tests/test_htsget.py
PATH="$PWD/.venv/bin:$PATH" git commit -m "feat(htsget): send Client-Public-Key header for encrypted streams"
```

---

### Task 4: Decrypt the assembled stream in `open()`

**Files:**
- Modify: `src/modos/genomics/htsget.py` (imports, `open`, `_decrypt`)
- Test: `tests/test_htsget.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_htsget.py` (the `encrypt_file` helper already exists in `modos.genomics.c4gh`):

```python
def test_open_decrypts_encrypted_stream(c4gh_keypair, tmp_path):
    """open() returns plaintext when a secret key is configured."""
    from modos.genomics.c4gh import encrypt_file

    payload = b"##fileformat=VCFv4.3\nchr1\t1\t.\tA\tT\t.\t.\t.\n" * 50
    plain_path = tmp_path / "payload.vcf"
    plain_path.write_bytes(payload)
    enc_path = tmp_path / "payload.vcf.c4gh"
    encrypt_file(c4gh_keypair["public_key"], plain_path, enc_path)

    block = base64.b64encode(enc_path.read_bytes()).decode()
    con = HtsgetConnection(
        host="http://localhost:8000",
        path=Path("payload.vcf"),
        region=None,
        secret_key=c4gh_keypair["private_key"],
    )
    # Inject the ticket directly to avoid an HTTP round-trip (cached_property).
    con.__dict__["ticket"] = {
        "htsget": {"urls": [{"url": f"data:;base64,{block}"}]}
    }

    with con.open() as handle:
        assert handle.read() == payload


def test_open_wraps_decryption_failure(c4gh_keypair, tmp_path):
    """A stream that is not valid crypt4gh raises a clear error."""
    import pytest

    block = base64.b64encode(b"not encrypted data").decode()
    con = HtsgetConnection(
        host="http://localhost:8000",
        path=Path("payload.vcf"),
        region=None,
        secret_key=c4gh_keypair["private_key"],
    )
    con.__dict__["ticket"] = {
        "htsget": {"urls": [{"url": f"data:;base64,{block}"}]}
    }

    with pytest.raises(ValueError, match="decrypt"):
        con.open()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_htsget.py::test_open_decrypts_encrypted_stream -v`
Expected: FAIL — `open()` returns the raw encrypted `HtsgetStream`, so `handle.read()` returns ciphertext, not `payload`.

- [ ] **Step 3: Write minimal implementation**

In `src/modos/genomics/htsget.py`, add to the imports (near `import pysam`):

```python
from crypt4gh.lib import decrypt
```

Replace the existing `open` method with a version that decrypts when encrypted, and add the `_decrypt` helper. Note the return annotation widens from `io.RawIOBase` to `io.IOBase` (a temp file is a `BufferedRandom`, both share `io.IOBase`):

```python
    def open(self) -> io.IOBase:
        """Open a connection to the stream data (decrypted if a key is set)."""
        try:
            stream = HtsgetStream(self.ticket["htsget"]["urls"])
        except KeyError:
            raise KeyError(f"No htsget urls found in ticket: {self.ticket}")
        if not self._encrypted:
            return stream
        return self._decrypt(stream)

    def _decrypt(self, stream: io.RawIOBase) -> io.IOBase:
        """Decrypt a crypt4gh stream into a readable plaintext temp file."""
        encrypted = tempfile.TemporaryFile("w+b")
        for chunk in stream:
            encrypted.write(chunk)
        encrypted.seek(0)
        plaintext = tempfile.TemporaryFile("w+b")
        try:
            decrypt(
                keys=[(0, self._seckey, None)],
                infile=encrypted,
                outfile=plaintext,
            )
        except Exception as err:
            plaintext.close()
            raise ValueError(
                "Failed to decrypt htsget stream. Ensure the secret key "
                "matches the public key registered with the server."
            ) from err
        finally:
            encrypted.close()
        plaintext.seek(0)
        return plaintext
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_htsget.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Format, lint, commit**

```bash
uv run ruff format src/modos/genomics/htsget.py tests/test_htsget.py
uv run ruff check src/modos/genomics/htsget.py tests/test_htsget.py
PATH="$PWD/.venv/bin:$PATH" git add src/modos/genomics/htsget.py tests/test_htsget.py
PATH="$PWD/.venv/bin:$PATH" git commit -m "feat(htsget): decrypt encrypted streams at open() boundary"
```

---

### Task 5: Thread the key through `MODO.stream_genomics`

**Files:**
- Modify: `src/modos/api.py` (`stream_genomics` signature + `HtsgetConnection` call, around lines 473-507)
- Test: `tests/test_api_local.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_api_local.py`:

```python
def test_stream_genomics_threads_secret_key(monkeypatch, tmp_path):
    """stream_genomics forwards secret_key/passphrase to HtsgetConnection."""
    import modos.api as api_mod

    modo = MODO(tmp_path)
    captured = {}

    class FakeConnection:
        def __init__(
            self, host, path, region=None, secret_key=None, passphrase=None
        ):
            captured["secret_key"] = secret_key
            captured["passphrase"] = passphrase

        def to_pysam(self, reference_filename=None):
            return iter([])

    class FakeEndpoint:
        s3 = {"s3": "http://s3"}
        htsget = "http://htsget"

    monkeypatch.setattr(api_mod, "HtsgetConnection", FakeConnection)
    monkeypatch.setattr(MODO, "list_files", lambda self: [Path("demo1.cram")])
    monkeypatch.setattr(modo, "endpoint", FakeEndpoint())

    key = tmp_path / "key.sec"
    list(
        modo.stream_genomics(
            "demo1.cram", secret_key=key, passphrase="secret"
        )
    )

    assert captured["secret_key"] == key
    assert captured["passphrase"] == "secret"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api_local.py::test_stream_genomics_threads_secret_key -v`
Expected: FAIL — `stream_genomics() got an unexpected keyword argument 'secret_key'`.

- [ ] **Step 3: Write minimal implementation**

In `src/modos/api.py`, update the `stream_genomics` signature (add the two parameters after `reference_filename`):

```python
    def stream_genomics(
        self,
        file_path: str,
        region: str | None = None,
        reference_filename: str | None = None,
        secret_key: Path | None = None,
        passphrase: str | None = None,
    ) -> Iterator[AlignedSegment | VariantRecord]:
```

And update the `HtsgetConnection(...)` construction (around line 502) to forward them:

```python
            con = HtsgetConnection(
                self.endpoint.htsget,
                Path(*self.path.parts[1:]) / file_path,
                region=_region,
                secret_key=secret_key,
                passphrase=passphrase,
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_api_local.py::test_stream_genomics_threads_secret_key -v`
Expected: PASS

- [ ] **Step 5: Format, lint, commit**

```bash
uv run ruff format src/modos/api.py tests/test_api_local.py
uv run ruff check src/modos/api.py tests/test_api_local.py
PATH="$PWD/.venv/bin:$PATH" git add src/modos/api.py tests/test_api_local.py
PATH="$PWD/.venv/bin:$PATH" git commit -m "feat(api): pass secret key through stream_genomics"
```

---

### Task 6: Add `--secret-key` to the CLI `stream` command

**Files:**
- Modify: `src/modos/cli/remote.py` (`stream` command, imports)
- Test: `tests/test_cli_remote.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli_remote.py` (check the top of the file for an existing `CliRunner`/`cli` import; if absent, add `from typer.testing import CliRunner` and `from modos.cli.main import cli`, and `runner = CliRunner()`):

```python
def test_cli_stream_threads_secret_key(monkeypatch, tmp_path):
    """`modos remote stream --secret-key` forwards the key to HtsgetConnection."""
    import io

    import modos.genomics.htsget as htsget_mod
    import modos.remote as remote_mod

    captured = {}

    class FakeConnection:
        def __init__(
            self, host, path, region=None, secret_key=None, passphrase=None
        ):
            captured["secret_key"] = secret_key

        def open(self):
            return io.BytesIO(b"")

    class FakeEndpoint:
        def __init__(self, *args, **kwargs):
            pass

        def __bool__(self):
            return True

        htsget = "http://htsget"

    monkeypatch.setattr(htsget_mod, "HtsgetConnection", FakeConnection)
    monkeypatch.setattr(remote_mod, "EndpointManager", FakeEndpoint)

    key = tmp_path / "key.sec"
    key.write_text("")
    result = runner.invoke(
        cli,
        [
            "--endpoint",
            "http://example.org",
            "remote",
            "stream",
            "--secret-key",
            str(key),
            "s3://bucket/ex",
            "demo1.cram",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["secret_key"] == key
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_remote.py::test_cli_stream_threads_secret_key -v`
Expected: FAIL — `stream` has no `--secret-key` option (typer reports "No such option").

- [ ] **Step 3: Write minimal implementation**

In `src/modos/cli/remote.py`, add the imports at the top if missing:

```python
from typing import Optional
```

Add the two options to the `stream` command signature (after the existing `region` option, before the closing `):`):

```python
    secret_key: Annotated[
        Optional[Path],
        typer.Option(
            "--secret-key",
            "-s",
            help="Secret key to decrypt an encrypted stream. Its public "
            "key is sent to the htsget server.",
        ),
    ] = None,
    passphrase: Annotated[
        Optional[Path],
        typer.Option(
            "--passphrase",
            "-pw",
            help="Path to file with passphrase to unlock the secret key.",
        ),
    ] = None,
```

Update the `HtsgetConnection(...)` construction inside `stream` to forward the key (mirror the `c4gh decrypt` passphrase-file reading):

```python
    con = HtsgetConnection(
        endpoint.htsget,
        source,
        _region,
        secret_key=secret_key,
        passphrase=open(passphrase).read() if passphrase else None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_remote.py::test_cli_stream_threads_secret_key -v`
Expected: PASS

- [ ] **Step 5: Format, lint, commit**

```bash
uv run ruff format src/modos/cli/remote.py tests/test_cli_remote.py
uv run ruff check src/modos/cli/remote.py tests/test_cli_remote.py
PATH="$PWD/.venv/bin:$PATH" git add src/modos/cli/remote.py tests/test_cli_remote.py
PATH="$PWD/.venv/bin:$PATH" git commit -m "feat(cli): add --secret-key to stream command"
```

---

### Task 7: Document encrypted streaming

**Files:**
- Modify: `docs/tutorials/genomics_streaming.md`

- [ ] **Step 1: Add a documentation subsection**

In `docs/tutorials/genomics_streaming.md`, after the `## Data streaming` tab-set (before `## Data encryption and decryption`), add:

````markdown
### Streaming encrypted data

When the htsget server stores crypt4gh-encrypted data, pass your secret key to
decrypt the stream on the fly. The matching public key is derived and sent to
the server automatically; the decrypted region is returned transparently.

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO

modo = MODO(path='s3://modos-demo/ex', endpoint='http://localhost')
modo.stream_genomics(
    file_path="demo1.cram",
    region="BA000007.3",
    secret_key="path/to/recipient.sec",
)
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos --endpoint http://localhost remote stream \
  --region BA000007.3 \
  --secret-key path/to/recipient.sec \
  s3://modos-demo/ex demo1.cram
```
:::

::::
````

- [ ] **Step 2: Verify docs build**

Run: `uv run sphinx-build -q docs/ docs/_build`
Expected: completes without new ERRORs referencing `genomics_streaming.md`.

- [ ] **Step 3: Commit**

```bash
PATH="$PWD/.venv/bin:$PATH" git add docs/tutorials/genomics_streaming.md
PATH="$PWD/.venv/bin:$PATH" git commit -m "docs: document encrypted htsget streaming"
```

---

### Task 8: Full validation

- [ ] **Step 1: Run the whole suite**

Run: `uv run pytest -q`
Expected: all tests pass (existing 50 + new), the 13 remote-marked tests still skipped.

- [ ] **Step 2: Run all pre-commit hooks**

Run: `uv run pre-commit run -a`
Expected: all hooks pass.

---

## Self-Review

**Spec coverage:**
- Key input (secret key only, derive pubkey) → Task 1 (`derive_public_key`) + Task 3 (`_client_public_key`).
- `Client-Public-Key` header + `encryptionScheme=C4GH` → Task 2 (URL) + Task 3 (header).
- Decrypt at `open()` boundary, transparent plaintext → Task 4.
- Surface = CLI + Python API → Task 6 (CLI) + Task 5 (API).
- Error handling (clear error on decryption failure; opt-in leaves plaintext paths unchanged) → Task 4 (`test_open_wraps_decryption_failure`); plaintext paths covered by the existing doctest + `test_*_omits/by_default` tests.
- Testing (unit pubkey, unit header negotiation via pytest-httpserver, integration round-trip) → Tasks 1, 2, 3, 4.
- Docs (CLAUDE.md requires updating docs for new functionality) → Task 7.

**Naming consistency:** The spec's Components section names the helper `derive_public_key`; the Testing section's stale `public_key_from_secret` is superseded — this plan uses `derive_public_key` everywhere.

**Placeholder scan:** No TBD/TODO; every code step shows complete code.

**Type consistency:** `HtsgetConnection.secret_key: Path | None`; `passphrase: str | None`. `derive_public_key(bytes) -> bytes`. `_seckey -> bytes`. `_client_public_key() -> str`. `open() -> io.IOBase` (widened from `io.RawIOBase` to accommodate the decrypted temp file). `stream_genomics(..., secret_key: Path | None, passphrase: str | None)`. CLI passes `secret_key` as `Path` and a passphrase string read from file, matching `HtsgetConnection`'s field types.
