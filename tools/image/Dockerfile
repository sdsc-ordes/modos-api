ARG VERSION_BUILD



##################################################
# Poetry setup
##################################################
FROM python:3.12-slim AS poetry

WORKDIR /app
# Install poetry
ENV PYTHONUNBUFFERED=true
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN python -c 'from urllib.request import urlopen; print(urlopen("https://install.python-poetry.org").read().decode())' | python -

# Copy necessary files only
COPY ./modos/ ./modos
COPY ./pyproject.toml ./pyproject.toml
COPY ./README.md ./README.md
COPY ./poetry.lock ./poetry.lock
RUN apt-get update && \
    apt-get install -y gcc

# Poetry install
RUN poetry install --all-extras --no-interaction --no-ansi -vvv


##################################################
# modos setup
##################################################
FROM python:3.12-slim AS runtime
ARG VERSION_BUILD
ENV PATH="/app/.venv/bin:$PATH"
COPY --from=poetry /app /app

# Set user
RUN useradd -ms /bin/bash modos_user
USER modos_user

# metadata labels
LABEL org.opencontainers.image.source=https://github.com/sdsc-ordes/modos-api
LABEL org.opencontainers.image.description="Serve multi-omics digital objects"
LABEL org.opencontainers.image.licenses=Apache-2.0
LABEL org.opencontainers.image.version=${VERSION_BUILD}

# Test run
RUN modos --help

CMD ["modos"]
