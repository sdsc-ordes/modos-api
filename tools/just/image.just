set positional-arguments
set dotenv-load
set shell := ["bash", "-cue"]
root_dir := `git rev-parse --show-toplevel`
registry := "ghcr.io/sdsc-ordes"
repository := "modos-api"
ctr := "docker"

tag_cmd := (
  "grep -E '^__version__ += +' " +
  root_dir +
  "/src/modos/__init__.py | sed -E 's/.*= +//' | tr -d '\"'"
)

[private]
default:
  just --unsorted --no-aliases --list image

# Build the modos-api client image.
[no-cd]
build:
  @echo "🐋 Building docker image"
  {{ctr}} build \
    -f ./tools/image/Dockerfile \
    --build-arg=VERSION_BUILD=`{{tag_cmd}}` \
    -t {{registry}}/{{repository}}:`{{tag_cmd}}` .

# Push the modos-api client image.
[no-cd]
push: build
  {{ctr}} push {{registry}}/{{repository}}:`{{tag_cmd}}`
