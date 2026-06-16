FROM alpine:3.20 AS xray
ARG TARGETARCH
RUN apk add --no-cache ca-certificates curl unzip \
    && case "$TARGETARCH" in \
        amd64) XRAY_ARCH="64" ;; \
        arm64) XRAY_ARCH="arm64-v8a" ;; \
        *) echo "unsupported TARGETARCH: $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && curl -fsSL "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-${XRAY_ARCH}.zip" -o /tmp/xray.zip \
    && unzip -j /tmp/xray.zip xray -d /out \
    && chmod +x /out/xray

FROM alpine:3.20

RUN apk add --no-cache ca-certificates python3

WORKDIR /app
COPY --from=xray /out/xray /usr/local/bin/xray
COPY sub-relay.py /app/sub-relay.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/sub-relay.py /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
