Notable changes introduced in modos releases are documented in this file


## [0.3.1] - 2025-05-23

### Bug Fixes
- pin typer AND click versions for compatibility

### Documentation
- add encryption and upload sections (#136)


## [0.3.0] - 2025-05-20

### Bug Fixes

- *(api)* update data path (#118)
- *(deps)* remove misplaced pyfuzon import
- *(server)* api compatibility for /meta and /get (#126)

### Documentation

- *(readme)* fix gha badge url (#132)
- *(tuto)* document modos enrich subcommand- add file format design notes (#111)


### Features

- *(cli)* update prompts for removal of missing config elements (#123)
- *(deploy)* setup refget service (#121)- logger (#130)
- local crypt4gh encryption (#127)



## [0.2.3] - 2024-11-29

### Bug Fixes

- *(deploy)* htsget networking (#102)
- *(htsget)* minio connection

### Documentation

- *(readme)* fix example sparql query
- *(tuto)* fix mztab example

### Features

- *(cli)* consistent path options (#105)
- *(cli, api)* show only target element (#98)- support terminology codes (#106)
- mztab support (#107)



## [0.2.2] - 2024-08-12

### Bug Fixes

- *(rdf)* inject schema:identifier (#99)

### Documentation

- *(tutorial)* update remote and genomics (#97)


## [0.2.1] - 2024-08-08

### Bug Fixes

- *(rdf)* schema.org prefix (#96)


## [0.2.0] - 2024-08-05

### Bug Fixes

- *(api)* add type hints, fix doctests
- *(api)* MODO.metadata extracts own attributes
- *(api)* update changed values in update_element (#83)
- *(cli)* duplicated prompt for id
- *(cli)* drop zarr group creation on modo create
- *(compose)* network syntax
- *(compose)* volume mounts + listening address
- *(compose)* env vars to specify buckets and policies
- *(compose)* disconnect s3 volume from modo-server (accessed via net)
- *(cram)* add slicing logic
- *(cram)* coords -> region
- *(deploy)* disable body size limit in nginx (#42)
- *(deploy)* disable max body size in nginx
- *(docker)* missing dep in client dockerfile
- *(introspection)* support inheritance in get_slots
- *(io)* rm unneeded id_ -> id
- *(minio)* add env variables for auth
- *(minio)* expose console port locally
- *(nginx)* define rewrite rules for s3+htsget
- *(rdf)* handle path->uri conversion for data_path
- *(server)* pin dependencies
- *(server)* safer bucket replacement
- *(server)* safer bucket replacement
- *(server)* make exact_match match exactly
- *(server)* pin htsget version + bump msrv (#49)
- *(server)* reload minio filesystem on server queries (#62)- schema syntax
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

- *(cli)* shorten command descriptions
- *(compose)* mount -> volume for minio
- *(deploy)* add deployment instructions and docs
- *(deploy)* update readme with nginx setup
- *(deploy)* document configuration with .env file
- *(readme)* add usage+development guidelines
- *(readme)* refresh api description
- *(readme)* add credits (#55)
- *(readme)* styling + update examples (#80)
- *(readme)* fix api example
- *(typo)* deploy/README.md
- *(typo)* deploy/README.md- add initial README.md
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

- *(api)* basic metadata extraction
- *(api)* update existing elements
- *(api)* allow passing zarr archive to MODO constructor
- *(cli)* implement create command
- *(cli)* add write commands for metadata+data
- *(cli)* add support for multi-choice prompt
- *(cli)* allow skipping slot prompts
- *(cli)* stream command (#87)
- *(cli)* update modo from yaml file (#89)
- *(cli, api)* remove modo (#76)
- *(cram)* region parsing func
- *(cram)* slice local files
- *(deploy)* add nginx service in compose
- *(deploy)* htsget over s3 (#26)
- *(docker)* version as build arg + metadata label
- *(helpers)* allow enum from model object
- *(introspection)* add getter methods, cache schema views
- *(io)* helper functions for loading instances
- *(makefile)* docker build recipe
- *(meta)* add custom rdf converter
- *(nginx)* placeholder config
- *(s3)* allow virtual-host-style buckets (#75)
- *(server)* extend client dockerfile
- *(server)* list modos and gather metadata[wip]
- *(server)* sort matches by similarity- add draft rdf metadata schema
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
- add helper function to determine the file format. needed for generalized save/stream_genomics methods, and possibly for oter methods/functions as well
- add a function to handle both cram and vcf/bcf BytesIO buffers.
- add a function to handle both cram and vcf/bcf BytesIO buffers.
- Add development setup for Nix shell
- Enable `nix` development
- auto update last_update_date attr (#73)
- htsget client (#78)
- streamline remote options (#90)


<!--generated by git-cliff -->
