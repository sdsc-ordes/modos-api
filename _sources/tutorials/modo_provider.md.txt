# Create and modify a MODO

A `MODO` is a digital object to store, share and access omics data (genomics, transcriptomics, proteomics and metabolomics) and their metadata.
Each `MODO` consists of a unique id, a creation and an update timestamp and some further optional metadata. Elements such as __data entities__, __samples__, __assays__ and __reference genomes__ can be linked and added to a `MODO`. The full data model can be found at <a href="https://sdsc-ordes.github.io/modos-schema/" target="_blank">modos-schema</a>.

(scratch)=
## Generate a MODO from scratch

(Create_scratch)=
### Create the object

To create a new `MODO` you only need to specify the `path` where you want to generate the object. This will automatically generate a new <a href="https://zarr.readthedocs.io/en/stable/api/hierarchy.html" target="_blank">zarr group</a> at the specified `path`. If not specified explicitly the `MODO` id will be set to the `path` name.

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO
modo = MODO(path = "data/ex")
modo
# <modos.api.MODO object at 0x7df3131cb670>
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos create data/ex
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

An element of the type data can be a <a href="https://sdsc-ordes.github.io/modos-schema/DataEntity/" target="_blank">DataEntity</a> or further spefied as an <a href="https://sdsc-ordes.github.io/modos-schema/AlignmentSet/" target="_blank">AlignmentSet</a>, an <a href="https://sdsc-ordes.github.io/modos-schema/Array/" target="_blank">Array</a>, a <a href="https://sdsc-ordes.github.io/modos-schema/VariantSet/" target="_blank">VariantSet</a>.


::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO
import modos_schema.datamodel as model

# Load modo (see above)
modo = MODO(path = "data/ex")

# Generate a data element
data = model.DataEntity(id="genomics1", name= "demo_genomics", description = "A tiny cram file for demos", data_format="CRAM", has_sample= "sample/sample1", data_path = "/internal/path/to/store/cram_file")

# Add element to modo
modo.add_element(element = data, source_file="path/to/cram_file.cram")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos add --source-file path/to/cram_file.cram data/ex data
```
:::

::::

:::{note}
To specify a file that should be associated with this object the `source-file` option can be used.
In addition elements can be linked with each other, e.g. a `VariantSet` to a `ReferenceGenome` or a `DataEntity` to a `Sample` by using the `parent`/`part-of` option.
:::

:::{warning}
Files associated through the `source-file` option will be copied into the `MODO` at the path specified in the `data_path` attribute. For large files this can take some time.
:::

(file)=
## Generate a MODO from (yaml-)file

Alternatively, a MODO and all associated elements can be specified in a `yaml-file`, such as the following `example.yaml`:

```{code-block} yaml
# An example yaml file to generate a MODO.

- element:
    id: ex
    "@type": MODO
    description: "Example modo for tests"
    creation_date: "2024-01-17T00:00:00"
    last_update_date: "2024-01-17T00:00:00"
    has_assay: assay1

- element:
    id: assay1
    "@type": Assay
    name: Assay 1
    description: Example assay for tests
    has_data: demo1
    omics_type: GENOMICS

- element:
    id: demo1
    "@type": DataEntity
    name: Demo 1
    description: Demo CRAM file for tests.
    data_format: CRAM
    data_path: demo1.cram
    has_sample: sample1
    has_reference: reference1
  args:
    source_file: data/ex/demo1.cram

- element:
    id: reference1
    "@type": ReferenceGenome
    name: Reference 1
    data_path: reference1.fa
  args:
    source_file: data/ex/reference1.fa


- element:
    id: sample1
    "@type": Sample
    name: Sample 1
    description: An example sample for tests.
    collector: Foo university
    sex: Male
```
In this yaml file each element is a separate list entry. Within each list entry the `element` section specifies all relevant metadata as well as the `element type` (using `@type: ELEMENT_TYPE` as syntax).
All valid element types, their fields and potential links can be found in the <a href="https://sdsc-ordes.github.io/modos-schema/" target="_blank">modos-schema</a>.
The `args` section provides additional arguments that are valid for adding an element to modo (see [Add elements to the object](add_scratch)), e.g. `args: source_file:` provides the path to the file that should be added into modo.

Using this `example.yaml` a `MODO` and all specified associated elements can be generated in one command:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO
modo = MODO.from_file(config_path= "path/to/example.yaml", object_path = "data/ex")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos create --from-file "path/to/example.yaml" data/ex
```
:::

::::

### Advanced example

```{code-block} yaml
# A more advanced example with multiple assays, samples and files.

- element:
    id: f2a991_full_mouse
    "@type": MODO
    description: "Example complex modo describing multiple assays on fictional mouse f2a991."
    creation_date: "2024-01-17T00:00:00"
    last_update_date: "2024-01-17T00:00:00"
    has_assay:
      - 001_rnaseq
      - 001_wgs

- element:
    id: 001_rnaseq
    "@type": Assay
    name: Tissue specific RNA-seq.
    description: Example RNA-seq assay with multiple samples.
    sample_processing:
      - http://www.ebi.ac.uk/efo/EFO_0001461
      - http://www.ebi.ac.uk/efo/EFO_0008567
      - http://www.ebi.ac.uk/efo/EFO_0009653
    has_data:
      - 001_brain_rna_aligned
      - 001_liver_rna_aligned
    omics_type: TRANSCRIPTOMICS

- element:
    id: 001_wgs
    "@type": Assay
    name: Mouse WGS
    description: Example whole genome sequencing assay with one sample.
    sample_processing:
      - http://www.ebi.ac.uk/efo/EFO_0001461
      - http://www.ebi.ac.uk/efo/EFO_0010172
      - http://www.ebi.ac.uk/efo/EFO_0008631
    has_data: 001_wgs_aligned
    omics_type: GENOMICS

- element:
    id: 001_wgs_aligned
    "@type": DataEntity
    name: Mouse WGS.
    description: Mouse WGS alignment, Illumina sequencing.
    data_format: CRAM
    data_path: 001_wgs_aligned.cram
    has_reference: mm39
    has_sample: 001_tail_dna
  args:
    source_file: data/tail.cram

- element:
    id: 001_brain_rna_aligned
    "@type": DataEntity
    name: Mouse brain RNAseq.
    description: Mouse brain RNAseq alignment, Illumina sequencing.
    data_format: CRAM
    data_path: 001_brain_rna_aligned.cram
    has_reference: mm39
    has_sample: 001_brain_rna
  args:
    source_file: data/brain.cram

- element:
    id: 001_liver_rna_aligned
    "@type": DataEntity
    name: Mouse liver RNAseq.
    description: Mouse liver RNAseq alignment, Illumina sequencing.
    data_format: CRAM
    data_path: 001_liver_rna_aligned.cram
    has_reference: mm39
    has_sample: 001_liver_rna
  args:
    source_file: data/liver.cram

- element:
    id: mm39
    "@type": ReferenceGenome
    name: Genome assembly mm39
    description: Genome assembly mm39 of M. musculus strain C57BL/6J.
    data_path: mm39.fa
    version: mm39
    source_uri: https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_000001635.27
    taxon_id: http://purl.obolibrary.org/obo/NCBITaxon_39442
  args:
    source_file: data/reference1.fa

- element:
    id: 001_liver_rna
    "@type": Sample
    name: Liver RNA library
    description: RNA library from liver of mouse f2a991.
    collector: Foo university
    taxon_id: http://purl.obolibrary.org/obo/NCBITaxon_39442
    source_material: http://purl.obolibrary.org/obo/UBERON_0002107
    sex: Male

- element:
    id: 001_brain_rna
    "@type": Sample
    name: Brain ventricles RNA library
    description: RNA library from brain ventricles of mouse f2a991.
    collector: Foo university
    taxon_id: http://purl.obolibrary.org/obo/NCBITaxon_39442
    source_material: http://purl.obolibrary.org/obo/UBERON_0004086
    sex: Male

- element:
    id: 001_tail_dna
    "@type": Sample
    name: Tail snip DNA library
    description: WGS library from tail snip of mouse f2a991.
    collector: Foo university
    taxon_id: http://purl.obolibrary.org/obo/NCBITaxon_39442
    source_material: http://purl.obolibrary.org/obo/UBERON_0002415
    sex: Male
```

```{code-block} console
$ modos create -f advanced.yaml advanced
$ modos show advanced --zarr

INFO | Using local storage for advanced
/
 ├── assay
 │   ├── 001_rnaseq
 │   └── 001_wgs
 ├── data
 │   ├── 001_brain_rna_aligned
 │   ├── 001_liver_rna_aligned
 │   └── 001_wgs_aligned
 ├── reference
 │   └── mm39
 ├── sample
 │   ├── 001_brain_rna
 │   ├── 001_liver_rna
 │   └── 001_tail_dna
 └── sequence
```

(update)=
## Update or remove a MODO element

All elements of a `MODO` can be added (see [Add elements to the object](add_scratch)) or removed at any timepoint using the `element id`:

::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
# Remove an associated element
modo.remove_element("data/genomics1")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
modos remove data/ex data/genomics
```
:::

::::

To update an existing element a new entity of the same type can be provided:

```{code-block} python
import modos_schema.datamodel as model

# Generate the data element from above with a change in name
# Fields that are not changed will be kept
data = model.DataEntity(id="genomics1", name="genomics_example", data_format="CRAM", data_path = "/internal/path/to/store/cram_file")

# Update element to modo
modo.update_element(element_id = "data/genomics1", new = data)
```
