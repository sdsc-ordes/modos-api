FROM rust:1.75.0 AS builder

WORKDIR /build

RUN cargo install cargo-strip

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/umccr/htsget-rs.git --branch htsget-actix-v0.6.1 .


RUN cargo build --features s3-storage --release && cargo strip

FROM debian:stable-slim

# gettext-base is required for envsubst (config templating)
RUN apt update && apt install --no-install-recommends -y gettext-base libc6-dev && rm -rf /var/lib/apt/lists/*

COPY --from=builder /etc/ssl/certs/ /etc/ssl/certs/
COPY --from=builder /build/target/release/htsget-actix /usr/local/bin/htsget-actix
COPY docker-entrypoint.sh /

# Set user and permissions
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser
USER appuser
USER root
RUN mkdir /htsget && chown -R appuser:appgroup /htsget
USER appuser

ENV HTSGET_TICKET_SERVER_ADDR 0.0.0.0:8080
ENV HTSGET_DATA_SERVER_ADDR 0.0.0.0:8081

EXPOSE 8080
EXPOSE 8081


ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["htsget-actix", "--config", "/htsget/config.toml"]
