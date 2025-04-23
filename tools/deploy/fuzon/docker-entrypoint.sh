#!/bin/sh
set -e

# only use entrypoint if running fuzon-http
if [ "$1" = "fuzon-http" ] ; then

  # Templating
  if [ -e "/fuzon/config.json" ]; then
    echo "Using existing config.json"

  elif [ -e "/fuzon/config.json.template" ]; then
    echo "Generating config.json from config.json.template"
    envsubst < /fuzon/config.json.template > /fuzon/config.json
    cat /fuzon/config.json
    echo "$@"

  else
    echo "No config.json or config.json.template found. Exiting."
    exit 1

  fi
fi

exec "$@"
