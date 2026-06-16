FROM gogost/gost:latest AS gost

FROM alpine:3.20

RUN apk add --no-cache ca-certificates python3

WORKDIR /app
COPY --from=gost /bin/gost /usr/local/bin/gost
COPY sub-relay.py /app/sub-relay.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/sub-relay.py /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
