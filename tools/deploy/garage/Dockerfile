FROM alpine:edge

RUN apk add --no-cache bash curl garage gettext

COPY docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["garage", "-c", "/etc/garage.toml", "server"]
