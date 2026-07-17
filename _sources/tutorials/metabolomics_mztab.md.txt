
# Working with metabolomics results

MODOS supports [mzTab 2.0-M](https://hupo-psi.github.io/mzTab/2_0-metabolomics-release/mzTab_format_specification_2_0-M_release.html#adding-optional-columns) files to represent mass spectrometry results from metabolomics.

These files can be added to an existing MODO and some metadata can be extracted automatically.

## Including a file

mztab files can be embedded like any other file into the digital object:


::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO
import modos_schema.datamodel as model

# Load modo (see above)
modo = MODO(path = "data/ex")

# Generate a data element
data = model.DataEntity(id="metabo_MS1", name= "Metabo MS1", description = "Some mass spectrometry results", data_format="mzTab", data_path = "metabo_ms1.mztab")

# Add element to modo
modo.add_element(element = data, source_file="path/to/source.mztab")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos add --source-file path/to/source.mztab data/ex data
```
:::

::::

## Extracting metadata

Once the mzTab file is included, some of its metadata can be extracted to enrich the MODOS metadata:


::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO

# Load modo (see above)
modo = MODO(path = "data/ex")
modo.enrich_metadata()

```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos enrich data/ex
```
:::

::::


This will check all files in the modos for metadata to be extracted. After running it, samples described in the mzTab files should be visible in the MODOS metadata, and can be viewed e.g. by running modos show --zarr.


## Opening mzTab files

[pyteomics](https://pyteomics.readthedocs.io/en/latest/) ofter an intuitive API to work with mzTab files, however it only works with local files.
If the MODO is local, the mzTab can be opened directly with pyteomics.
Otherwise, it must be downloaded first:

```{code-block} python
from modos.api import MODO
from pyteomics.mztab import MzTab

# if the modo is local
mz = MzTab('data/ex/metabo_ms1.mztab')

# if remote

modo = MODO('s3://example/modo')
with open("local.mztab", "w") as mz_handle:
  for line in modo.storage.open("metabo_ms1.mztab"):
      mz_handle.write(line)

mz = MzTab("local.mztab")
```
