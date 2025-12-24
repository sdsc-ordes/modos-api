# Garage S3

Garage S3 is used as the single source of truth to store MODOs (metadata and data together). By default, it is included as part of the compose stack, but it could also be deployed separately (e.g. as a geo-distributed cluster).

Only garage is currently supported as the S3 server, as the kms relies on its API for credential management.

# Configuration

The garage configuration is generated on the fly by templating `garage.toml.template`. You may edit this configuration template to customize the settings.
