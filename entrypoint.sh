#!/bin/sh
set -eu

: "${SUB_URLS:=${SUB_URL:-}}"
: "${SUB_URLS:?Set SUB_URLS or SUB_URL to your subscription URL(s)}"
: "${PROTOCOLS:=auto}"
: "${REFRESH_SECONDS:=0}"
: "${LOG_LEVEL:=warning}"
: "${ACCESS_LOG:=none}"
: "${ERROR_LOG:=}"

write_subscriptions() {
  printf '%s\n' "$SUB_URLS" | tr ',' '\n' | sed '/^[[:space:]]*$/d; /^[[:space:]]*#/d' > /tmp/subscriptions.txt
}

write_xray_config() {
  write_subscriptions
  /app/sub-relay.py \
    --subscription-list /tmp/subscriptions.txt \
    --protocols "$PROTOCOLS" \
    --log-level "$LOG_LEVEL" \
    --access-log "$ACCESS_LOG" \
    --error-log "$ERROR_LOG" \
    > /tmp/xray.json
}

run_xray() {
  command -v xray >/dev/null 2>&1 || {
    echo "xray binary is not installed in this image." >&2
    exit 1
  }

  mkdir -p /var/log/sub-relay
  write_xray_config
  xray -config /tmp/xray.json &
  xray_pid="$!"

  if [ "$REFRESH_SECONDS" = "0" ]; then
    wait "$xray_pid"
    exit $?
  fi

  while true; do
    sleep "$REFRESH_SECONDS"
    write_xray_config
    kill "$xray_pid" 2>/dev/null || true
    wait "$xray_pid" 2>/dev/null || true
    xray -config /tmp/xray.json &
    xray_pid="$!"
  done
}

run_xray
