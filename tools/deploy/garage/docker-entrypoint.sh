#!/bin/sh
set -e

# only use entrypoint if running garage
if [ "$1" = "garage" ] ; then

  # Templating
  if [ -e "/etc/garage.toml" ]; then
    echo "Using existing config.toml"

  elif [ -e "/etc/garage.toml.template" ]; then
    echo "Generating garage.toml from garage.toml.template"
    envsubst < /etc/garage.toml.template > /etc/garage.toml
    cat /etc/garage.toml
    echo "$@"

  else
    echo "No garage.toml or garage.toml.template found. Exiting."
    exit 1

  fi
fi

exec "$@"
