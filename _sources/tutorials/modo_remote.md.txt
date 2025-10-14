# Working with remote objects

Remote storage can be key to share and collaborate on multiomics data. `MODOS` integrates with S3 object storage and <a href="https://academic.oup.com/bioinformatics/article/35/1/119/5040320" target="_blank">htsget</a> to allow remote storage, access and real-time secure streaming of genomic data.
Most of the `MODOS-api`'s functionalities work with remotely stored objects in the same way as with local objects. The user only as to specify the `s3_endpoint` of the remote object store.

## List remotely available MODO's
Listing all available `MODOs` at a specific S3 endpoint (in this tutorial we will use http://localhost as example) will show `MODOs` in all buckets at that endpoint:


```{code-block} python
import modos.remote as remo

# Show all remote modos
remo.list_remote_items("http://localhost")
# ['modos-demo/GIAB', 'modos-demo/ex']
```

## Show metadata of a remote MODO
For all or a specific `MODO` metadata can directly be displayed:

```{code-block} python
import modos.remote as remo

# Get metadata of all MODOs at endpoint "http://localhost"
remo.get_metadata_from_remote("http://localhost")

# Get metadata of MODO with id ex
remo.get_metadata_from_remote("http://localhost", modo_id="ex")
```

## Find a specific MODO and get its S3 path

There are different options to query a specific `MODO` and the __bucket name__ to load it from - fuzzy search or exact string matching:

```{code-block} python
import modos.remote as remo

# Query all MODOs with sequence similar to "ex"
remo.get_s3_path("http://localhost", query="ex")
# [{'http://localhost/s3/modos-demo/ex': {'s3_endpoint': 'http://localhost/s3', 'modo_path': 'modos-demo/ex'}}]

# Query all MODOs exactly matching "ex"
remo.get_s3_path("http://localhost", query="ex", exact_match=True)
# []
```

## Instantiate a remote MODO locally

Remotely stored `MODOs` can be instantiated by specifying their remote endpoint and then worked with as if they were stored locally.

The example below assumes a public s3 bucket endpoint accessible anonymously (without credentials).

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO

# Load MODO from remote storage
modo=MODO(path='s3://modos-demo/ex', endpoint='http://localhost', s3_kwargs={"anon": True})

# All operations can be applied as if locally
modo.metadata
# {'ex': {'@type': 'MODO', 'creation_date': '2024-02-19T00:00:00', 'description': 'Dummy modo for tests.', 'has_assay': ..}}
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
# Interact with remotely stored MODO
modos --anon --endpoint http://localhost show s3://modos-demo/ex
# ex:
#   '@type': MODO
#   creation_date: '2024-02-19T00:00:00'
#   description: Dummy modo for tests.
#   has_assay:
```
:::

::::

:::{warning}
The __bucket name__ and the __endpoint url__ are specified separately. The __bucket name__ is part of the `object_path` and needs to be included in the s3 path, followed by the `MODO`'s name (e.g. `s3://bucket_name/modo_name`), while the __endpoint url__ needs to be specified separately. Only paths that follow the s3 scheme will be considered as remote independent of `--endpoint` being specified or not.
:::

:::{note}
To avoid repetition, the endpoint and anon values can also be read from environment variables.
The syntax then follows the same as for local objects, except that the `object_path` needs to be provided as s3 scheme:

```{code-block} console
export MODOS_ENDPOINT='http://localhost'
export MODOS_ANON=true
modos create s3://bucket/object1
modos show   s3://bucket/object1
modos delete s3://bucket/object1
```
:::

(authenticated_bucket)=
## Use authenticated buckets

Most use-cases require authentication to access the S3 bucket.
This usually requires an access key and secret key.
MODOS can access these keys through the standard [AWS environment variables](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-envvars.html):

```{code-block} console
export AWS_ACCESS_KEY_ID=<id>
export AWS_SECRET_ACCESS_KEY=<secret>
export MODOS_ENDPOINT='http://modos.example.org'
modos show s3://protected-bucket/example
```

However, it is strongly recommended to avoid entering secrets in the terminal and instead store them in encrypted .env files.
Tools like [sops](https://github.com/getsops/sops) make this easy:


```{code-block} console
# create public/secret key pair
age-keygen -o keypair.txt
# create encrypted env file
sops --age <public-key> .enc.env

# Values decrypted in memory and injected in the modos process
sops exec-env .enc.env 'modos show s3://protected-bucket/example'
SOPS_AGE_KEY_FILE=keypair.txt sops exec-env .enc.env \
  'modos show s3://protected-bucket/example'
```

(generate_remote)=
## Generate and modify a MODO at a remote object store

A `MODO` can be generated from scratch or from file in the same way as locally, by specifying the remote endpoint's url or `MODOS_ENDPOINT`:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO
from pathlib import Path

# yaml file with MODO specifications
config_ex = Path("path/to/ex.yaml")

# Create a modo remotely
modo = MODO.from_file(config_ex, "s3://modos-demo/ex", endpoint="http://localhost")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
# Create a modo from file remotely
modos --endpoint "http://localhost" create --from-file "path/to/ex.yaml" s3://modos-demo/ex3
```
:::

::::

:::{note}
Similar to `MODO` creation, any other modifying functionality of the `modos-api`, (e.g.  `modos add`, `modos remove` or `MODO.add_element()`, `MODO.remove_element()`) can be performed on remotely stored objects by specifying the __endpoint__ and object path as s3 scheme + __bucket name__ as path.
:::

## Download and upload a MODO

A `MODO` can directly be __downloaded__ from a remote endpoint.

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO

# Load MODO from remote storage
modo=MODO(path='s3://modos-demo/ex', endpoint='http://localhost')

# Download MODO to local path "data/ex"
modo.download("data/ex")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
# Download a remote modo from "modos-demo/ex" to local path "data/ex"
modos --endpoint http://localhost remote download --target data/ex s3://modos-demo/ex
```
:::

::::

A local `MODO` can be __uploaded__ to a remote endpoint.

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO

# Load MODO from local storage
modo=MODO(path='data/ex')

# Upload MODO to remote path "modos-demo/ex"
modo.upload("s3://modos-demo/ex", s3_endpoint='http://localhost')
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
# Upload a local modo from "data/ex" to remote path "modos-demo/ex"
modos --endpoint http://localhost remote upload --target s3://modos-demo/ex data/ex
```
:::

::::
