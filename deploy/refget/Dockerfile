FROM python:3.12-slim-bookworm

EXPOSE 8080

# gettext-base is required for envsubst (config templating)
RUN apt update && apt install -y gettext-base libc6-dev git && apt-get clean

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/

# install refget-cloud from github
RUN uv pip install --system "git+https://github.com/ga4gh/refget-cloud/@c39a65acba9818414789f004cced487562012bf0"

ADD . /app
WORKDIR /app

COPY --chmod=755 docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["refget-server", "--properties-file", "/refget/config.properties"]

### TODO: Enable open-api swagger deployment
