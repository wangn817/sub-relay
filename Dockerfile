FROM gogost/gost:latest AS gost

FROM debian:12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends iptables python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=gost /bin/gost /usr/local/bin/gost
COPY sub-relay.py /app/sub-relay.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/sub-relay.py /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
