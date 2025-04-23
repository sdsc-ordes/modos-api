REGISTRY="ghcr.io/sdsc-ordes"
IMAGE_NAME="modos-api"
LOCAL_IP := $(shell ip route get 1 | sed -n 's/^.*src \([0-9.]*\) .*$$/\1/p')
VERSION :=$(shell grep -E '^__version__ += +' src/modos/__init__.py | sed -E 's/.*= +//' | tr -d '"')

.PHONY: install
install: ## Install with the poetry and add pre-commit hooks
	@echo "🚀 Installing packages with uv"
	@uv venv -p 3.12
	@uv sync --all-extras --group={'dev','test','docs'}
	@uv run pre-commit install

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking Poetry lock file consistency with 'pyproject.toml': Running poetry lock --check"
	@uv lock --check
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a

.PHONY: docs
doc: ## Build sphinx documentation website locally
	@echo "📖 Building documentation"
	@cd docs
	@uv sync --frozen --group docs --all-extras
	@uv run sphinx-build docs/ docs/_build

.PHONY: docker-build
docker-build: ## Build the modos-api client Docker image
	@echo "🐋 Building docker image"
	@docker build \
		--build-arg="VERSION_BUILD=$(VERSION)" \
		-t $(REGISTRY)/$(IMAGE_NAME):$(VERSION) .

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run pytest

.PHONY: deploy
deploy: ## Deploy services using docker compose
	@echo "$(LOCAL_IP)";exit 0
	@echo "🐋 Deploying server with docker compose"
	cd deploy; S3_PUBLIC_URL="http://$(LOCAL_IP):9000" docker compose up --build --force-recreate


.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
