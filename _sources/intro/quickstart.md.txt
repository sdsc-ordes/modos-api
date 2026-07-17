# Quickstart

MODO can be used as command-line tool or python module.

First install modos using pip or use docker to run modos within a container:

::::{tab-set}

:::{tab-item} pip
:sync: pip
```{code-block} console
pip install git+https://github.com/sdsc-ordes/modos-api.git@main
```
:::

:::{tab-item} docker
:sync: docker
```{code-block} console
docker pull ghcr.io/sdsc-ordes/modos-api:latest
```
:::

::::

Next, you can use the modo-cli to build a new multiomics digital object (__modo__) with the id `ex`:

:::{note}
You will be prompted to complete further modo metadata information.
This command will generate the modo object in the current working directory. Use a relative path, if you want to store your object at a specific location, e.g. `modos create data/ex`
:::

::::{tab-set}

:::{tab-item} pip
:sync: pip
```{code-block} console
modos create ex
```
:::

:::{tab-item} docker
:sync: docker
```{code-block} console
docker run -itv "${PWD}:/modo" ghcr.io/sdsc-ordes/modos-api:latest modos create modo/ex
```
:::

::::

To check further commands e.g. to add omics elements or interact use:

::::{tab-set}

:::{tab-item} pip
:sync: pip
```{code-block} console
modos --help
```
:::

:::{tab-item} docker
:sync: docker
```{code-block} console
docker run ghcr.io/sdsc-ordes/modos-api:latest --help
```
:::

::::
