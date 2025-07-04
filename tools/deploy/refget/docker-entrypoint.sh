#!/bin/sh
set -e

# only use entrypoint if running refget-server
if [ "$1" = "uv" ] ; then

  # Templating
  if [ -e "/refget/config.properties" ]; then
    echo "Using existing config.properties"

  elif [ -e "/refget/config.properties.template" ]; then
    echo "Generating config.properties from config.properties.template"
    envsubst < /refget/config.properties.template > /refget/config.properties
    cat /refget/config.properties
    echo "$@"

  else
    echo "No config.properties or config.properties.template found. Exiting."
    exit 1

  fi
fi

exec "$@"
