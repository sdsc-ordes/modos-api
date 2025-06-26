# Background

## Multiomics - the (full) picture

Molecular mechanisms are highly regulated at various levels. Different omic layers (genomics, transcriptomics, proteomics, metabolomics) interact and communicate with each other to establish specific phenotypes. Thus, it can be crucial to explore several of these layers together to understand phenotypic pattern and their nuances, e.g. in the manifestation of genetic diseases. Recent advances in sequencing technologies enabled the parallel measurement of multiple omic layers from the same sample. Integrated analysis of these __multiomics__ data can help to unravel the underlying molecular mechanisms of regulation and their interactions.

## Multi Omics Digital Object System(MODOS)

### Features

:::{image} ../img/multiomics.png
   :align: right
   :width: 200
   :height: 200
   :alt: multiomics
:::

The main goal of `MODOS` is to enable collaborative analysis and data sharing of multiomics data. Typically multiomics data are large in size, diverse in their formats and object to secure access. Thus remote storage with regulated access can be key to enable data sharing and integrated analysis.
Because of these requirements the `MODOS-api` provides the following __key features__:

- queryable, linked metadata
- data and metadata synchronisation
- compression
- remote access
- streaming

### Object structure

Internally, `MODOS` builds on the <a href="https://github.com/zarr-developers/zarr-python" target="_blank">zarr</a> file storage format, that allows storage and access of chunked, compressed, N-dimensional __arrays__ alongside their __metadata__ in __hierachical groups__. All metadata can be consolidated and exported separately for querying or listing purposes. Genomics data are not stored as arrays, but can be added to the `zarr` archive in <a href="https://samtools.github.io/hts-specs/CRAMv3.pdf" target="_blank">CRAM</a> format. CRAM is a reference-based compression format for alignment files:

:::{image} ../img/digital-object.png
   :align: center
   :width: 600
   :alt: digital-object
:::

### Remote storage

:::{image} ../img/smoc-server.png
   :align: right
   :width: 270
   :alt: smoc-server
:::

The `MODOS-api` provides a server implementation to facilitate remote storage and access. This server consists of __3 main components__:
- a webserver exposing a REST api to interact with remote objects
- a htsget server to provide streaming access over network to CRAM files
- s3 bucket to allow remote random access

Detailed instructions about how to deploy can be found in the <a href="https://github.com/sdsc-ordes/modos-api/tree/main/deploy" target="_blank">MODOS-api github project -> deploy</a>.
