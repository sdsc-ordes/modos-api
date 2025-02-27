# Design notes: Modos x Refget


## Goal
Use a [refget](http://samtools.github.io/hts-specs/refget.html) api in modos to handle reference sequences in an unambigous and standardized way.

## Considerations
1. GA4GH published a [Refget Sequence Collections](https://ga4gh.github.io/refget/seqcol/) specification (v1 approved 2025) to:
    *   allow retrival of sequence collections (usually __reference
 genomes__)
    *   specify __sequence collection hashes__, that are composed from the __sequence hashes__ and __sequence attributes__ (names, length,?)(see [Seqcol standard](#seqcol-standard))
    *   assess compatability of sequence collections 
        *   includes coordinate systems based on sequence attributes
2. A pangenomes standard is planned
3. CRAM uses reference sequence ids (not sequence collections)

### The Refget umbrella
![refget-umbrella](https://ga4gh.github.io/refget/img/refget-umbrella.svg)

### Seqcol standard
![seqcol_abstract_simple](https://ga4gh.github.io/refget/img/seqcol_abstract_simple.svg)

## Existing tools
1. [refget-cloud](https://github.com/ga4gh/refget-cloud): Python-based Refget v1 web service compatible with s3 storage
    - :heavy_check_mark: small and simple tool
    - :heavy_check_mark: part of the official ga4gh github organisation
    - :heavy_minus_sign: not sure how much this is maintained (last commit 5 years ago)
    - :heavy_minus_sign: associated tooling in perl ([ena-processor](https://github.com/andrewyatz/ena-refget-processor))
    - :heavy_minus_sign: minimalistic documentation
2. [refgenie](https://refgenie.org/refgenie): Software suite to manage storage, access, and transfer of reference genome resources. Main usage to download pre-build genomic resources or build "assets" for custom assemblies. Based on 2 main tools: 
    - 2a. [refgenie/refget](https://refgenie.org/refget/): 
    Python client for retrieval and interaction of a refget or seqcol service. Includes convenience functions for digest calculations, caching, local and remote storage, a local refget implementation, ... 
    - 2b. [refgenie/refgenieserver](https://refgenie.org/refgenieserver/):
    API to archive and serve refernce genomes
    - :heavy_check_mark: active maintained, comprehensive docs
    - :heavy_check_mark: flexible to be used with refseq and seqcol, extensive capabilities
    - :heavy_minus_sign: server implementation looks hard to adapt
    - :heavy_minus_sign: code potentially hard to extend/customize


---

## Solutions

### 1. Customized Refget-cloud server

Use [refget-cloud](https://github.com/ga4gh/refget-cloud) to deploy a refget server, that allows upload and retrival of reference sequences as part of modos.

#### Requirements
1. Add and adapt refget-cloud deployment to modos-deployment (inital setup [here](https://github.com/sdsc-ordes/modos-api/tree/feat/deploy_refget))
2. Add functionality to calculate checksums and upload genome sequences/checksum pointer as done by the [refget-loader](https://github.com/ga4gh/refget-loader/tree/master)(convenience functions in [refgenie/refget](https://refgenie.org/refget/) could potentially be useful as well)
3. Adapt refget-cloud to refget v2 (minor changes)
4. Integration with modos-api:
    *    upload/download ReferenceSequences
    *    find/list references
    *    ?
    *    reference lift-over (probably later?)

#### Pro
- :heavy_check_mark: slim dependencies (refget-cloud is rather simple)
- :heavy_check_mark: refget protocol should be sufficient for cram - no/small overhead

#### Con
- :heavy_minus_sign: refget-cloud seems not maintained/minimalistic docs


### 2. Customize refgenieserver
Deploy [refgenie/refgenieserver](https://refgenie.org/refgenieserver/) as part of modos deployments to make use of the refgenie suite.

#### Requirements
1. Adapt refgenieserver to use cloudbased data (there is a remote option for refgenie/refget, so it should be possible?)
2. Deploy refgenieserver
3. Use refgenie/refget to allow up/download, comparison of genomes (coordinate system), caching?
4. Integrate with modos-api

#### Pro
- :heavy_check_mark: active maintenance + group working on tooling
- :heavy_check_mark: it should be straight forward to extend for seqcol standard, if that is useful in future

#### Con
- :heavy_minus_sign: heavy-dependance on refgenie
- :heavy_minus_sign: code-adaptation seem cumbersome

