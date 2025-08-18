FROM rust:1.75.0 AS builder

WORKDIR /build

RUN cargo install cargo-strip

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/sdsc-ordes/fuzon.git --branch v0.4.0 .

RUN cd fuzon-http && cargo build --release && cargo strip

FROM debian:stable-slim

# gettext-base is required for envsubst (config templating)
RUN apt update && apt install --no-install-recommends -y curl gettext-base libc6-dev && rm -rf /var/lib/apt/lists/*

COPY --from=builder /etc/ssl/certs/ /etc/ssl/certs/
COPY --from=builder /build/target/release/fuzon-http /usr/local/bin/fuzon-http
COPY docker-entrypoint.sh /

# Download terminologies into the image
RUN mkdir /data && chmod -R 744 /data
RUN curl -L "https://purl.obolibrary.org/obo/cl.owl" -o /data/cl.owl && \
    curl -L "https://purl.obolibrary.org/obo/uberon.owl" -o /data/uberon.owl && \
    curl -L "https://purl.obolibrary.org/obo/ncbitaxon/subsets/taxslim.owl" -o /data/taxslim.owl

EXPOSE 9090

# Set user and permissions
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser
USER appuser
USER root
RUN mkdir /fuzon && chown -R appuser:appgroup /fuzon /data
USER appuser

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["fuzon-http", "--config", "/fuzon/config.json"]
