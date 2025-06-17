FROM rust:1.75.0 AS builder

WORKDIR /build

RUN cargo install cargo-strip

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/sdsc-ordes/fuzon.git --branch v0.4.0 .

RUN cd fuzon-http && cargo build --release && cargo strip

FROM debian:stable-slim

# gettext-base is required for envsubst (config templating)
RUN apt update && apt install -y gettext-base libc6-dev && rm -rf /var/lib/apt/lists/*

COPY --from=builder /etc/ssl/certs/ /etc/ssl/certs/
COPY --from=builder /build/target/release/fuzon-http /usr/local/bin/fuzon-http
COPY docker-entrypoint.sh /

EXPOSE 9090

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["fuzon-http", "--config", "/fuzon/config.json"]
