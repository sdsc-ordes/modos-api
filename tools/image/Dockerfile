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

# include source files
WORKDIR /app
COPY CHANGELOG.md LICENSE README.md pyproject.toml uv.lock /app
COPY src ./src

# Set user and permissions
RUN useradd -ms /bin/bash modos_user
RUN chown -R modos_user:modos_user /app
RUN chmod -R 755 /app
USER modos_user

# modos setup
RUN uv venv -p 3.12
RUN uv sync --frozen

# Test run
RUN uv run modos --help

ENTRYPOINT ["uv", "run"]
CMD ["modos"]
