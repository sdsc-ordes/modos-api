# Client-side support for encrypted htsget streams

Date: 2026-06-12
Status: Approved (design)

## Problem

`modos` streams genomic regions from a remote htsget-rs server.
The client (`src/modos/genomics/htsget.py`): fetches a ticket,
concatenates the referenced byte ranges into a single stream,
and feeds the result to stdout (CLI) or a temporary file  and
then to `pysam` (Python API).

htsget-rs can serve crypt4gh-encrypted streams. The client must opt in, send its
public key, and decrypt the assembled stream locally. We already have crypt4gh
encrypt/decrypt for *local* files (`src/modos/genomics/c4gh.py`), but remote
streams cannot currently be decrypted.

## How htsget-rs serves encrypted streams

Documented as experimental feature in htsget-rs:

1. Client sends a `Client-Public-Key: <base64 crypt4gh public key>` request
   header, plus an experimental `encryptionScheme=C4GH` query parameter.
2. Server re-encrypts the crypt4gh header to *that* public key and returns
   byte ranges that, concatenated, form a **valid crypt4gh file** (re-encrypted
   header + edit lists + encrypted data blocks).
3. Client decrypts the assembled stream with the matching **private key**
   using standard crypt4gh decryption, which handles edit lists natively.

References:
- htsget-rs C4GH config: https://github.com/umccr/htsget-rs/blob/main/htsget-config/README.md
- UMCCR walkthrough: https://umccr.org/blog/htsget-rs-crypt4gh/

Caveat: the `encryptionScheme=C4GH` parameter is experimental and "subject to
change" per htsget-rs; this client targets a moving server-side spec.

## Decisions

- **Key input:** a single `--secret-key` (path) plus optional passphrase. The
  client derives the public key from the secret key to send as the header, and
  uses the secret key to decrypt. One input, guaranteed matched pair, mirrors
  the existing `modos c4gh decrypt -s` ergonomics.
- **Surface:** both the CLI `modos stream` command and the Python API
  (`HtsgetConnection` / `MODO.stream_genomics` / `to_pysam`).
- **Output:** decrypt to CRAM/SAM/input format transparently. The user receives
  requested region in plaintext on stdout / as decrypted records of the corresponding
  format; encryption is invisible to them.

## Approach

Decrypt at the `HtsgetConnection.open()` boundary. When a secret key is
configured, `open()` returns a decrypted readable; every downstream consumer
(CLI stdout loop, `to_pysam`, `to_file`) is unchanged and operate on decrypted
data. This keeps a single integration point, reuses the existing crypt4gh
decrypt, and keeps encryption awareness out of every consumer.

The region-bounded encrypted stream is buffered through a temporary
file before decryption. This is consistent with the existing `to_pysam` path,
which already spools to a temp file because `pysam` cannot read byte streams.

Rejected alternatives:
- **Decrypt at each consumer** — duplicates the decrypt call and leaks
  encryption awareness into the CLI and `to_pysam`.
- **Lazy streaming-decrypt `RawIOBase` wrapper** — crypt4gh's Python API has no
  clean incremental reader; reimplementing block/edit-list handling is high risk
  for little gain on bounded region slices.

## Components

### `genomics/c4gh.py`

Add a key-derivation helper:

- `derive_public_key(seckey: bytes) -> bytes`: derive the raw 32-byte
  X25519 public key from the secret-key bytes (via
  `nacl.public.PrivateKey(seckey).public_key`). The `Client-Public-Key` header
  value is its base64 encoding.

Existing `get_secret_key(path, passphrase)` is reused to load the key (it
already supports passphrase prompting and auto-generation).

### `genomics/htsget.py`

- `HtsgetConnection` gains `secret_key: Path | None = None` and
  `passphrase: str | None = None`, with an `_encrypted` property
  (`secret_key is not None`).
- The ticket request adds the `Client-Public-Key` header (base64 of the derived
  public key) when encrypted.
- `build_htsget_url` appends `&encryptionScheme=C4GH` when encrypted.
- `open()`: when encrypted, write the assembled crypt4gh stream to a temporary
  spool and decrypt it with the secret key (reusing crypt4gh `decrypt`),
  returning a readable handle to the plaintext; otherwise return `HtsgetStream`
  as today.
  - Implementation detail to verify: whether crypt4gh can consume the
    non-seekable assembled stream directly, allowing one temp file to be
    dropped. This does not change the design.

### Entry points

Both thread `secret_key` / `passphrase` straight into `HtsgetConnection`:

- CLI `modos stream`: new `--secret-key` / `-s` PATH option (mirrors
  `modos c4gh decrypt -s`) and optional passphrase. The stdout loop is unchanged.
- Python `MODO.stream_genomics(..., secret_key=None, passphrase=None)`.

## Data flow (encrypted path)

```
modos stream -s key.sec ...        MODO.stream_genomics(..., secret_key=...)
            |                                   |
            v                                   v
        HtsgetConnection(secret_key=..., passphrase=...)
            |
            | ticket request: header Client-Public-Key: b64(derive(seckey))
            |                 url   ...&encryptionScheme=C4GH
            v
        ticket (byte ranges -> crypt4gh-encrypted stream)
            |
            v
        open(): assemble blocks -> spool -> crypt4gh.decrypt(seckey) -> plaintext handle
            |
            v
        stdout loop  /  to_pysam (temp file -> pysam records)
```

## Error handling

- A missing or invalid secret key reuses `get_secret_key`'s `ValueError`s.
- If decryption fails (wrong key, or the server returned plaintext despite the
  header), surface a clear error wrapping the crypt4gh failure rather than
  emitting garbage bytes.
- Encryption is strictly opt-in; plaintext streaming paths are unchanged.

## Testing

- **Unit:** `public_key_from_secret` matches crypt4gh's own public key for a
  generated keypair (generate keys, derive, compare).
- **Unit:** the ticket request carries `Client-Public-Key` and
  `encryptionScheme=C4GH` only when a secret key is set, and neither when it is
  not (via `pytest-httpserver`, already a dev dependency).
- **Integration round-trip:** crypt4gh-encrypt a small payload to the client's
  derived public key, serve it as ticket blocks, and assert `open()` yields the
  original plaintext — exercising the full decrypt-at-`open()` path without a
  live htsget-rs server. crypt4gh handles edit lists natively, so standard
  stream decryption coverage is sufficient for the client side.

## Out of scope

- Server-side / deployment configuration of htsget-rs C4GH.
- Encrypting or decrypting remote objects at rest (still local-only).
- Tracking future changes to the experimental `encryptionScheme` negotiation.
