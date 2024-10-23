
# Working with genomics data

Genomic data can reach large volumes and is typically stored in domain-specific file formats such as <a href="https://samtools.github.io/hts-specs/CRAMv3.pdf" target="_blank">CRAM</a>, <a href="https://samtools.github.io/hts-specs/SAMv1.pdf" target="_blank">BAM</a> or <a href="https://samtools.github.io/hts-specs/VCFv4.5.pdf" target="_blank">VCF</a>. In `MODOs` genomics files are linked to a metadata element and directly stored within the object. To access region-specific information without downloading the entire file the remote storage is linked to a <a href="https://academic.oup.com/bioinformatics/article/35/1/119/5040320" target="_blank">htsget</a> server that allows secure streaming over the network.

## Data streaming
`MODOs` supports streaming of data from <a href="https://samtools.github.io/hts-specs/CRAMv3.pdf" target="_blank">CRAM</a>, <a href="https://samtools.github.io/hts-specs/SAMv1.pdf" target="_blank">BAM</a>, <a href="https://samtools.github.io/hts-specs/VCFv4.5.pdf" target="_blank">VCF</a> and <a href="https://samtools.github.io/hts-specs/BCFv2_qref.pdf" target="_blank">BCF</a> files to access specific genomic regions. In `MODOs`


::::{tab-set}

:::{tab-item} python
:sync: python
```{code-block} python
from modos.api import MODO

# Load MODO from remote storage
modo=MODO(path= 's3://modos-demo/ex', endpoint = 'http://localhost')

# Stream a specific region
modo.stream_genomics(file_path = "demo1.cram", region = "BA000007.3")
```
:::

:::{tab-item} cli
:sync: cli
```{code-block} console
# Stream chromosome BA000007.3 from modos-demo/ex/demo1.cram
modos --endpoint http://localhost stream --region BA000007.3 s3://modos-demo/ex/demo1.cram
```
:::

::::

:::{warning}
We highly recommend using the `MODOs` CLI for streaming. The output can directly be passed to tools like <a href="https://www.htslib.org/" target="_blank">samtools</a>. Streaming using the `MODOs` python api will return a <a href="https://pysam.readthedocs.io/en/stable/" target="_blank">pysam</a> object. `pysam` does not allow reading from byte-streams and thus the streamed region will be written into an temporary file before parsing to `pysam`. For large files/regions this can cause issues.
:::
