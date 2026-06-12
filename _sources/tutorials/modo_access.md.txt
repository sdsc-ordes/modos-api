# Explore a MODO and access its data

There are multiple ways to use a `MODO` and interact with it's elements.

(explore)=
## Explore a MODO and it's elements

`MODO` metadata can be easily accessed via CLI or using the python api:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO

# Create modo object (see Create and modify MODO)
modo = MODO(path = "data/ex")

# Show metadata as dictionary
modo.show_contents()
# {'ex': {'@type': 'MODO', 'creation_date': '2024-02-19T00:00:00', 'description': ..}
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos show "data/ex"
```
:::

::::

The objects structure can be visualized by displaying the internal hierarchy:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
modo.list_arrays()
#/
# ├── assay
# │   └── assay1
# ├── data
# │   └── demo1
# ├── reference
# │   └── reference1
# └── sample
#     └── sample1
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos show --zarr "data/ex"
#/
# ├── assay
# │   └── assay1
# ├── data
# │   └── demo1
# ├── reference
# │   └── reference1
# └── sample
#     └── sample1
```
:::

::::

:::{note}
`MODOS` internally uses <a href="https://zarr.readthedocs.io/en/stable/api/hierarchy.html" target="_blank">zarr's hierarchy groups</a>. Each sub-directory represents a new hierarchy group. Any array-like data can directly be stored within these hierarchy groups, while other file formats are stored separately.
:::

All files part of a `MODO` can be listed:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
modo.list_files()
# [PosixPath('data/ex/reference1.fa'), PosixPath('data/ex/demo1.cram')]
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos show --files "data/ex"
# data/ex/reference1.fa
# data/ex/demo1.cram
```
:::

::::

(publish)=
## Publish a MODO as linked data

A semantic artifact can be created from the digital object and published as linked data.
In this process JSON metadata are converted to RDF and all relative paths are converted to URI's.

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
modo.knowledge_graph(uri_prefix="http://demo-data")
# <Graph identifier=N1aa0d4f1f3d9428b9c01e703096c5c96 (<class 'rdflib.graph.Graph'>)>
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos publish --base-uri "http://demo-data" "data/ex"
# @prefix EDAM: <http://edamontology.org/> .
# @prefix NCIT: <http://purl.obolibrary.org/obo/NCIT_> .
# @prefix modos: <https://w3id.org/sdsc-ordes/modos-schema/> .
# @prefix schema: <http://schema.org/> .
# @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
#
# <http://demo-data/assay/assay1> a modos:Assay ;
#     schema:description "Dummy assay for tests." ;
#     schema:name "Assay 1" ;
#     modos:has_data <http://demo-data/demo1> ;
#     modos:omics_type NCIT:C84343 .
#
#     ...
```
:::

::::

## Enrich metadata
Some formats, such as CRAM, store relevant metadata, e.g. their reference sequences, in their header. These information can be automatically extracted and included into a `MODO`.


::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
# Enrich modo
modo.enrich_metadata()

# Check the added elements
modo.list_arrays()
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos enrich
modos show --zarr
```
:::

::::
