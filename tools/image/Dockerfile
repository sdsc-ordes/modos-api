FROM python:3.12-slim
ARG VERSION_BUILD

# metadata
LABEL org.opencontainers.image.title="MODOS API"
LABEL org.opencontainers.image.source=https://github.com/sdsc-ordes/modos-api
LABEL org.opencontainers.image.description="Manage multi-omics digital objects"
LABEL org.opencontainers.image.licenses=Apache-2.0
LABEL org.opencontainers.image.version=${VERSION_BUILD}

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/

# modos setup
WORKDIR /app
ADD CHANGELOG.md LICENSE README.md pyproject.toml uv.lock /app
ADD src ./src
RUN uv sync --frozen

# Set user
RUN useradd -ms /bin/bash modos_user
USER modos_user


# Test run
RUN uv run modos --help

ENTRYPOINT ["uv", "run", "modos"]
