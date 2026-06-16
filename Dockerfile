FROM gogost/gost:latest AS gost
FROM ghcr.io/xtls/xray-core:latest AS xray
RUN cp "$(command -v xray)" /xray

FROM alpine:3.20

RUN apk add --no-cache ca-certificates python3

WORKDIR /app
COPY --from=gost /bin/gost /usr/local/bin/gost
COPY --from=xray /xray /usr/local/bin/xray
COPY sub-relay.py /app/sub-relay.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/sub-relay.py /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
