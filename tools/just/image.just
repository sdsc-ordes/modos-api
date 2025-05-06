set positional-arguments
set dotenv-load
set shell := ["bash", "-cue"]
root_dir := `git rev-parse --show-toplevel`
registry := "ghcr.io/sdsc-ordes"
repository := "modos-api"
tag := `just get-version`
ctr := "docker"

[private]
default:
  just --unsorted --no-aliases --list image

# Build the modos-api client image.
build:
  @echo "🐋 Building docker image"
  cd {{root_dir}} && \
    {{ctr}} build \
      -f ./tools/image/Dockerfile \
      --build-arg="VERSION_BUILD={{tag}}" \
      -t {{registry}}/{{repository}}:{{tag}} .

# Push the modos-api client image.
push: build
  cd {{root_dir}} && \
    {{ctr}} push {{registry}}/{{repository}}:{{tag}}
