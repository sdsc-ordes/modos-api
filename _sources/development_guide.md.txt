# Development guide

The development environment can be set up as follows:

```sh
git clone https://github.com/sdsc-ordes/modos-api && cd modos-api
just setup
```

This will install dependencies and create the python virtual environment using [uv](https://docs.astral.sh/uv/) and setup pre-commit hooks with [pre-commit](https://pre-commit.com/).

The tests can be run with `just test`, it will execute pytest with the doctest module.

## Using Nix Package Manager

If you are using [`nix`](https://nixos.org/download) package manager with [flakes enabled](https://nixos.wiki/wiki/Flakes),
you can enter a development shell with all requirements installed by doing:

```shell
nix develop ./tools/nix#default
```

## Making a release

Releases are deployed to pypi.org through github actions.
To create a new release, create a PR named "chore: bump to X.Y.Z" where X.Y.Z is the new version. In the PR upgrade versions in the repo (sphinx config and pyproject.toml).

Once the PR is merged, a release can be created through the github UI on the merge commit. This will trigger corresponding release builds on PyPI and ghcr.io.
