Notable changes introduced in modos releases are documented in this file

## [0.3.5] - 2025-11-17

### Bug Fixes
- _(deploy)_ switch from minio to garage as S3 storage service (#183)

### Features

- *(cli)* oauth device code flow support (#183)

## [0.3.4] - 2025-10-14

### Bug Fixes

- *(api)* do not consolidate on read operations (#173)
- *(api)* auto-attach assays to MODO (#176)
- *(server)* explicit error message on missing bucket (#165)- vcf streaming to pysam (#180)


### Documentation

- *(tutorials)* fix obsolete api parameters (#168)
- *(tutorials)* add advanced yaml example (#172)

### Features

- *(cli)* codes for sample processing (#178)
- *(cli)* pass s3 credentials via env (#179)
- *(fuzon)* cli fallback without autocomplete (#164)- schema upgrade (#177)

## [0.3.3] - 2025-08-22

### Bug Fixes

- _(deploy)_ drop depends_on.required for compat with older compose (#156)
- _(deploy)_ nonroot container users (#157)
- _(deploy)_ addgroup -> groupadd for debian-based images

### Features

- _(deploy)_ caddy with https support (#160)- compatibility with air-gapped
  deployments (#154)

## [0.3.2] - 2025-06-16

### Bug Fixes

- _(cli)_ syntax when reading passphrase from file (#140)
- _(storage)_ transfer metadata (#148)

## [0.3.1] - 2025-05-23

### Bug Fixes

- _(api)_ sequential encryption (#138)
- pin typer AND click versions for compatibility

### Documentation

- add encryption and upload sections (#136)

## [0.3.0] - 2025-05-20

### Bug Fixes

- _(api)_ update data path (#118)
- _(deps)_ remove misplaced pyfuzon import
- _(server)_ api compatibility for /meta and /get (#126)

### Documentation

- _(readme)_ fix gha badge url (#132)
- _(tuto)_ document modos enrich subcommand- add file format design notes (#111)

### Features

- _(cli)_ update prompts for removal of missing config elements (#123)
- _(deploy)_ setup refget service (#121)- logger (#130)
- local crypt4gh encryption (#127)

## [0.2.3] - 2024-11-29

### Bug Fixes

- _(deploy)_ htsget networking (#102)
- _(htsget)_ minio connection

### Documentation

- _(readme)_ fix example sparql query
- _(tuto)_ fix mztab example

### Features

- _(cli)_ consistent path options (#105)
- _(cli, api)_ show only target element (#98)- support terminology codes (#106)
- mztab support (#107)

## [0.2.2] - 2024-08-12

### Bug Fixes

- _(rdf)_ inject schema:identifier (#99)

### Documentation

- _(tutorial)_ update remote and genomics (#97)

## [0.2.1] - 2024-08-08

### Bug Fixes

- _(rdf)_ schema.org prefix (#96)

## [0.2.0] - 2024-08-05

### Bug Fixes

- _(api)_ add type hints, fix doctests
- _(api)_ MODO.metadata extracts own attributes
- _(api)_ update changed values in update_element (#83)
- _(cli)_ duplicated prompt for id
- _(cli)_ drop zarr group creation on modo create
- _(compose)_ network syntax
- _(compose)_ volume mounts + listening address
- _(compose)_ env vars to specify buckets and policies
- _(compose)_ disconnect s3 volume from modo-server (accessed via net)
- _(cram)_ add slicing logic
- _(cram)_ coords -> region
- _(deploy)_ disable body size limit in nginx (#42)
- _(deploy)_ disable max body size in nginx
- _(docker)_ missing dep in client dockerfile
- _(introspection)_ support inheritance in get_slots
- _(io)_ rm unneeded id_ -> id
- _(minio)_ add env variables for auth
- _(minio)_ expose console port locally
- _(nginx)_ define rewrite rules for s3+htsget
- _(rdf)_ handle path->uri conversion for data_path
- _(server)_ pin dependencies
- _(server)_ safer bucket replacement
- _(server)_ safer bucket replacement
- _(server)_ make exact_match match exactly
- _(server)_ pin htsget version + bump msrv (#49)
- _(server)_ reload minio filesystem on server queries (#62)- schema syntax
- drop unused query
- visit nodes recursively when extracting metadata
- path handling on modo creation
- cli display of modo show
- rm unused linkml-owl helper+undeclared linkml dep
- add missing --data-file option
- set filename using metadata when copying into digital object
- validate types of has_part relationship in MODO.add
- handle root path when adding data
- allow flexible number of elements in yaml
- change path in example config.yaml
- use schema model to build modo from yaml
- directly cast schema models
- add check for list
- propagate function name change
- minor fix in example yaml id
- add check for existing before adding element to modo
- missing typing import
- create unique sequence ids from extracted metadata
- standardize metadata extraction
- extract reference from list
- remote metadata streaming
- add group level to extract_metadata in line with the new structure
- adapt tests to zarr path as id
- prevent failing for non existing keys in whitelist
- define existing paths in test yaml
- use relative path to enrich metadata
- rename whitelist, simplify conditions
- set full id for has_part attributes when build from yaml
- adapt has_part ids to full id when build from yaml
- consistent naming
- include metadata from all modos
- wildcard use in fstring
- adapt env var name
- name mismatch in slice_remote_cram
- mutable args (#52)
- auto upload cram index (#64)
- Add `direnv` tooling and ignore
- Add `pyright` lsp
- format bug in feature-request.yml
- consistent ids (#70)
- client-side region-filter on htsget streams (#71)

### Documentation

- _(cli)_ shorten command descriptions
- _(compose)_ mount -> volume for minio
- _(deploy)_ add deployment instructions and docs
- _(deploy)_ update readme with nginx setup
- _(deploy)_ document configuration with .env file
- _(readme)_ add usage+development guidelines
- _(readme)_ refresh api description
- _(readme)_ add credits (#55)
- _(readme)_ styling + update examples (#80)
- _(readme)_ fix api example
- _(typo)_ deploy/README.md
- _(typo)_ deploy/README.md- add initial README.md
- add implementation details to README.md
- add status to readme
- add license
- add NOTE in get_slot_range about class-independence
- mention class-independence in get_slot_range docstring
- docstring for MODO.update_element
- sphinx website with API reference (#32)
- Add some documentation for using `nix`
- format markdown documents (#66)

### Features

- _(api)_ basic metadata extraction
- _(api)_ update existing elements
- _(api)_ allow passing zarr archive to MODO constructor
- _(cli)_ implement create command
- _(cli)_ add write commands for metadata+data
- _(cli)_ add support for multi-choice prompt
- _(cli)_ allow skipping slot prompts
- _(cli)_ stream command (#87)
- _(cli)_ update modo from yaml file (#89)
- _(cli, api)_ remove modo (#76)
- _(cram)_ region parsing func
- _(cram)_ slice local files
- _(deploy)_ add nginx service in compose
- _(deploy)_ htsget over s3 (#26)
- _(docker)_ version as build arg + metadata label
- _(helpers)_ allow enum from model object
- _(introspection)_ add getter methods, cache schema views
- _(io)_ helper functions for loading instances
- _(makefile)_ docker build recipe
- _(meta)_ add custom rdf converter
- _(nginx)_ placeholder config
- _(s3)_ allow virtual-host-style buckets (#75)
- _(server)_ extend client dockerfile
- _(server)_ list modos and gather metadata[wip]
- _(server)_ sort matches by similarity- add draft rdf metadata schema
- add taxid in schema
- add pkg skeleton
- add helper functions to inspect schema
- add zarr mgmt funcs to modo.storage
- list samples in archive via API
- add remove command
- allow adding reference genomes
- relevant metadata from cram file
- first version to build full obj from yaml
- extend cli create
- server deployment (#12)
- update build_modo_from_file for new structure
- use zarr path as id, check for unique
- fail early for duplicated id in build_modo_from_file
- repeat prompt for invalid inputs (non unique ids)
- copy files into modo when building from yaml
- request server endpoints
- Add get?query to modo server
- enable instantiation of remote modo
- add a function to handle both cram and vcf/bcf BytesIO buffers.
- add helper function to determine the file format. needed for generalized
  save/stream_genomics methods, and possibly for oter methods/functions as well
- add a function to handle both cram and vcf/bcf BytesIO buffers.
- add a function to handle both cram and vcf/bcf BytesIO buffers.
- Add development setup for Nix shell
- Enable `nix` development
- auto update last_update_date attr (#73)
- htsget client (#78)
- streamline remote options (#90)

<!--generated by git-cliff -->
