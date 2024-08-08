# Development guide

The development environment can be set up as follows:

```sh
git clone https://github.com/sdsc-ordes/modos-api && cd modos-api
make install
```

This will install dependencies and create the python virtual environment using [poetry](https://python-poetry.org/) and setup pre-commit hooks with [pre-commit](https://pre-commit.com/).

The tests can be run with `make test`, it will execute pytest with the doctest module.

## Using Nix Package Manager

If you are using [`nix`](https://nixos.org/download) package manager with [flakes enabled](https://nixos.wiki/wiki/Flakes),
you can enter a development shell with all requirements installed by doing:

```shell
nix develop ./nix#default
```
