# Create and modify MODO

A `MODO` is a digital object to store, share and access omics data (genomics, transcriptomics, proteomics and metabolomics) and their metadata.
Each `MODO` consists of a unique id, a creation and an update timestamp and some further optional metadata. Elements such as __data entities__, __samples__, __assays__ and __reference genomes__ can be linked and added to a `MODO`. The full data model can be found at [modo-schema](https://sdsc-ordes.github.io/modo-schema/).

(scratch)=
## Generate a MODO from scratch

(Create_scratch)=
### Create the object

To create a new `MODO` you only need to specify the `path` where you want to generate the object. This will automatically generate a new [zarr group](https://zarr.readthedocs.io/en/stable/api/hierarchy.html) at the specified `path`. If not specified explicitly the `MODO` id will be set to the `path` name.

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modo.api import MODO
modo = MODO(path = "data/ex")
modo
# <modo.api.MODO object at 0x7df3131cb670>
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modo create data/ex
```
:::

::::

:::{note}
If the specified path refers to an existing `MODO`, the existing object will be loaded instead of creating a new object and overwriting the existing object.
Check [update](update) for details on how to update metadata of an existing `MODO`.
:::

:::{warning}
The specified `path` can not point to an existing object other than a `MODO` or the command will fail.
:::

(add_scratch)=
### Add elements to the object

To add omics data entities or further metadata to the object, you can add elements to the `MODO`.
There are 4 different element types, that can be added:
- sample
- assay
- data
- reference

An element of the type data can be a [DataEntity](https://sdsc-ordes.github.io/modo-schema/DataEntity/) or further spefied as an [AlignmentSet](https://sdsc-ordes.github.io/modo-schema/AlignmentSet/), an [Array](https://sdsc-ordes.github.io/modo-schema/Array/), a [VariantSet](https://sdsc-ordes.github.io/modo-schema/VariantSet/)


::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modo.api import MODO
import modo_schema.datamodel as model

# Load modo (see above)
modo = MODO(path = "data/ex")

# Generate a data element
data = model.DataEntity(id="genomics1", name= "demo_genomics", description = "A tiny cram file for demos", data_format="CRAM", data_path = "/internal/path/to/store/cram_file")

# Add element to modo
modo.add_element(element = data, data_file="path/to/cram_file.cram")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modo add --data-file path/to/cram_file.cram data/ex data
```
:::

::::

:::{note}
To specify a file that should be associated with this object the `data-file` option can be used.
In addition elements can be linked with each other, e.g. a `VariantSet` to a `ReferenceGenome` or a `DataEntity` to a `Sample` by using the `parent`/`part-of` option.
:::

:::{warning}
Files associated through the `data-file` option will be copied into the `MODO` at the path specified in the `data_path` attribute. For large files this can take some time.
:::

(file)=
## Generate a MODO from (yaml-)file

Alternatively, a MODO and all associated elements can be specified in a `yaml-file`, such as the following `example.yaml`:

```{code-block} yaml
# An example yaml file to generate a MODO.

- id: ex
  "@type": MODO
  description: "Example modo for tests"
  creation_date: "2024-01-17T00:00:00"
  last_update_date: "2024-01-17T00:00:00"
  has_assay: assay1

- id: assay1
  "@type": Assay
  name: Assay 1
  description: Example assay for tests
  has_sample: sample1
  omics_type: GENOMICS

- id: demo1
  "@type": DataEntity
  name: Demo 1
  description: Demo CRAM file for tests.
  data_format: CRAM
  data_path: data/ex/demo1.cram
  has_reference: reference1

- id: reference1
  "@type": ReferenceGenome
  name: Reference 1
  data_path: data/ex/reference.fa

- id: sample1
  "@type": Sample
  name: Sample 1
  description: An example sample for tests.
  collector: Foo university
  sex: Male
```

All valid element types, their fields and potential links can be found in the [modo-schema](https://sdsc-ordes.github.io/modo-schema/).

Using this `example.yaml` a `MODO` and all specified associated elements can be generated in one command:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modo.io import build_modo_from_file
modo = build_modo_from_file(path = "path/to/example.yaml", object_directory = "data/ex")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modo create --from-file "path/to/example.yaml" data/ex
```
:::

::::


(update)=
## Update or remove a MODO element

All elements of a `MODO` can be added (see [Add elements to the object](add_scratch)) or removed at any timepoint using the `element id`:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
# Remove an associated element
modo.remove_element("/data/genomics1")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modo remove data/ex /data/genomics
```
:::

::::

To update an existing element a new entity of the same type can be provided:

```{code-block} python
import modo_schema.datamodel as model

# Generate the data element from above with a change in name
# Fields that are not changed will be kept
data = model.DataEntity(id="genomics1", name="genomics_example", data_format="CRAM", data_path = "/internal/path/to/store/cram_file")

# Add element to modo
modo.add_element(element = data, data_file="path/to/cram_file.cram")
```