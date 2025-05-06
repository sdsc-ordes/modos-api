#!/bin/sh
set -e

if [ "${S3_ADDRESSING_STYLE}" = "virtual" ]; then
  export PATH_STYLE=false
else
  export PATH_STYLE=true
fi

# only use entrypoint if running htsget-actix
if [ "$1" = "htsget-actix" ] ; then

  # Templating
  if [ -e "/htsget/config.toml" ]; then
    echo "Using existing config.toml"

  elif [ -e "/htsget/config.toml.template" ]; then
    echo "Generating config.toml from config.toml.template"
    envsubst < /htsget/config.toml.template > /htsget/config.toml
    cat /htsget/config.toml
    echo "$@"

  else
    echo "No config.toml or config.toml.template found. Exiting."
    exit 1

  fi
fi

exec "$@"
