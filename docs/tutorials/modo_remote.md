# Working with remote objects

Remote storage can be key to share and collaborate on multiomics data. `MODO` integrates with S3 object storage and <a href="https://academic.oup.com/bioinformatics/article/35/1/119/5040320" target="_blank">htsget</a> to allow remote storage, access and real-time secure streaming of genomic data.
Most of the `MODO-api`'s functionalities work with remotely stored objects in the same way as with local objects. The user only as to specify the `s3_endpoint` of the remote object store.

## List remotely available MODO's
Listing all available `MODOs` at a specific S3 endpoint (in this tutorial we will use http://localhost as example) will show `MODOs` in all buckets at that endpoint:


```{code-block} python
import modo.remote as remo

# Show all remote modos
remo.list_remote_items("http://localhost")
# ['modo-demo/GIAB', 'modo-demo/ex']
```

## Show metadata of a remote MODO
For all or a specific `MODO` metadata can directly be displayed:

```{code-block} python
import modo.remote as remo

# Get metadata of all modos at endpoint "http://localhost"
remo.get_metadata_from_remote("http://localhost")

# Get metadata of modo with id ex
remo.get_metadata_from_remote("http://localhost", modo_id = "ex")
```

## Find a specific MODO ad get it's S3 path
There are different options to query a specific `MODO` and the __bucket name__ to load it from - fuzzy search or exact string matching:

```{code-block} python
import modo.remote as remo

# Query all MODOs with sequence similar to "ex"
remo.get_s3_path("http://localhost", query="ex")
# [{'http://localhost/s3/modo-demo/ex': {'s3_endpoint': 'http://localhost/s3', 'modo_path': 'modo-demo/ex'}}]

# Query all MODOs exactly matching "ex"
remo.get_s3_path("http://localhost", query="ex", exact_match = True)
# []
```

## Intiantiate a remote MODO locally

Remotely stored `MODOs` can be intiantiated by specifiying their remote endpoint and then and worked with as if they were stored locally.

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modo.api import MODO

# Load MODO from remote storage
modo=MODO(path= 'modo-demo/ex', s3_endpoint = 'http://localhost/s3')

# All operations can be applied as if locally
modo.metadata
# {'ex': {'@type': 'MODO', 'creation_date': '2024-02-19T00:00:00', 'description': 'Dummy modo for tests.', 'has_assay': ..}}
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
# Interact with remotly stored MODO
modo show -s3 "http://localhost/s3" modo-demo/ex
# ex:
#   '@type': MODO
#   creation_date: '2024-02-19T00:00:00'
#   description: Dummy modo for tests.
#   has_assay:
```
:::

::::

:::{note}
The __bucket name__ and the __S3 endpoint url__ are specified separatly. The __bucket name__ is prepended to the `MODO`'s name in the same way as a local path, while the __S3 endpoint url__ needs to be specified specifically.
:::

(generate_remote)=
## Generate and modify a MODO at a remote object store

A `MODO` can be generated from scratch or from file in the same way as locally, by specifying the remote endpoint's url:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modo.api import MODO
from pathlib import Path

# yaml file with MODO specifications
config_ex = Path("path/to/ex.yaml")

# Create a modo remotely
modo = build_modo_from_file(config_ex, "modo-demo/ex", s3_endpoint= "http://localhost/s3")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
# Create a modo from file remotely
modo create -s3 "http://localhost/s3" ----from-file "path/to/ex.yaml" modo-demo/ex3
```
:::

::::

:::{note}
Similar to `MODO` creation, any other modifying functionality of the `MODO-api`, (e.g.  `modo add`, `modo remove` or `modo.add_element()`, `modo.remove_element()`)can be performed on remotely stored objects by specifying the __S3 endpoint__ and __bucket name__ as path.
:::