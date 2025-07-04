FROM python:3.12-slim-bookworm

EXPOSE 8080

# gettext-base is required for envsubst (config templating)
RUN apt update && apt install --no-install-recommends -y gettext-base libc6-dev git && apt-get clean

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/

COPY docker-entrypoint.sh /

# Set user and permissions
RUN chmod 755 /docker-entrypoint.sh
RUN addgroup appgroup && adduser appuser --ingroup appgroup
USER appuser
WORKDIR /app
COPY . /app
USER root
RUN mkdir /refget
RUN chown -R appuser:appgroup /app /refget
USER appuser

# install refget-cloud from github
RUN uv venv -p 3.12 --allow-existing
RUN uv pip install "git+https://github.com/ga4gh/refget-cloud/@c39a65acba9818414789f004cced487562012bf0"

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["uv", "run", "refget-server", "--properties-file", "/refget/config.properties"]

### TODO: Enable open-api swagger deployment
