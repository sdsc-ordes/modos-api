# Handling data arrays with MODOS

Any count-like data, e.g protein abundances, RNA counts, metabolomic measurements, etc. can be stored as arrays in the `MODO`.
The underlying <a href="https://github.com/zarr-developers/zarr-python" target="_blank">zarr</a> supports array creation as well as an interface to NumPy arrays.


## Load data

(pandas)=
### Using panda DataFrames

Count-like data can usually be loaded into <a href="https://pandas.pydata.org/docs/reference/frame.html" target="_blank">pandas DataFrame</a>.
To keep column names (__observations__) and row names (__variables__) both need to be stored in a separate numpy array first:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
import pandas as pd
import numpy as np

# Example of RNA-seq count data

rna_count = pd.read_csv('/path/to/rna/counts.csv', index_col="gene")
rna_count
# rna_count
#             time1  time2  time3    ...
# gene
# Xkr4        1891   2410   2159     ...
# Rp1         2      2      0        ...
# ...         ...    ...    ...      ...
# TrnP        334    202    218      ...

obs = rna_count.columns.to_numpy()
var = rna_count.index.to_numpy()
rna_array = rna_count.to_numpy()

obs
# array(['time1', 'time2', 'time3', ...], dtype=object)

var
# array(['Xkr4', 'Rp1', ..., 'TrnP'], dtype=object)

rna_array
# array([[1891, 2410, 2159, ...],
#        [   2,    2,    0, ...],
#        ...,
#        [ 334,  202,  218, ...]])

```
::::

:::{warning}
`to_numpy()` automatically removes row and column names from pandas DataFrames.
It is important to store them separately, if they contain important information.
:::

:::{note}
Skip this section, if you already have your data in a NumPy array.
:::

## Add array element to a MODO

Next, an element with the metadata describing the array can be added to the `MODO`:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO
import modos_schema.datamodel as model

# load modo - example at "data/ex"
modo= MODO("data/ex")

# Generate an Array element
array_element = model.Array(id="rna1", name= "RNA raw counts", description = "RNA counts from multiple timepoints", has_sample="sample/sample1", data_format = "Zarr", data_path="data/ex/data/rna1")

# Add element to modo
modo.add_element(element = array_element)

# Check the modo structure
modo.list_arrays()
#/
# ├── assay
# ├── data
# │   └── rna1
# ├── reference
# └── sample
#     └── sample1

```
:::
::::

:::{note}
Skip this step, if you want to add the count data to an already existing element in the `MODO`.
A helper function to facilitate adding the metadata element and numpy array in one step will also be added in future releases.
:::

## Add array to a MODO
Finally all arrays can be added to the modo element:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python

modo.archive["data/rna1"].create_dataset("data", data=rna_array)
modo.archive["data/rna1"].create_dataset("obs", data=obs)
modo.archive["data/rna1"].create_dataset("var", data=var, object_codec=numcodecs.JSON())

# update zarr metadata
zarr.consolidate_metadata(modo.store)

# check the new structure
modo.list_arrays()
#/
# ├── assay
# ├── data
# │   └── rna1
# │       └── data (1473,3) float64
# │       └── obs (3,) object
# │       └── var (1473,) object
# ├── reference
# └── sample
#     └── sample1

```
:::

::::

(access)=
## Access Array data

### Load array as pandas DataFrame
To access array data and analyse them the separated arrays can be loaded into a pandas dataframe:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
import pandas as pd

rna_array = modo.archive["data/rna1/data"][:]
obs = modo.archive["data/rna1/obs"][:]
var = modo.archive["data/rna1/var"][:]

rna_counts = pd.DataFrame(rna_array, index=var, columns=obs)
```
:::
::::
