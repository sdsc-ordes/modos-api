FROM python:3.12-slim AS builder

USER root

WORKDIR /build

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/sdsc-ordes/refget-cloud.git --branch master .

ENV PYTHONUSERBASE=/install

RUN pip install --prefix=/install .


FROM python:3.12-slim

# gettext-base is required for envsubst (config templating)
RUN apt update && apt install -y gettext-base libc6-dev && rm -rf /var/lib/apt/lists/*

ENV PYTHONUSERBASE=/install
ENV PATH="/install/bin:$PATH"
ENV PYTHONPATH="/install/lib/python3.12/site-packages"

COPY --from=builder /install /install
COPY --chmod=755 docker-entrypoint.sh /

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["refget-server", "--properties-file", "/refget/config.properties"]

### TODO: Enable open-api swagger deployment
