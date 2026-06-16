#!/bin/sh
set -eu

: "${SUB_URLS:=${SUB_URL:-}}"
: "${SUB_URLS:?Set SUB_URLS or SUB_URL to your subscription URL(s)}"
: "${CORE:=xray}"
: "${PROTOCOLS:=tcp,udp}"
: "${REFRESH_SECONDS:=0}"

write_subscriptions() {
  printf '%s\n' "$SUB_URLS" | tr ',' '\n' | sed '/^[[:space:]]*$/d; /^[[:space:]]*#/d' > /tmp/subscriptions.txt
}

write_core_config() {
  write_subscriptions
  /app/sub-relay.py --core "$CORE" --subscription-list /tmp/subscriptions.txt --protocols "$PROTOCOLS" > "/tmp/${CORE}.json"
}

run_core() {
  case "$CORE" in
    xray)
      command -v xray >/dev/null 2>&1 || {
        echo "xray core selected, but xray binary is not installed in this image." >&2
        exit 1
      }
      core_cmd="xray -config /tmp/xray.json"
      ;;
    gost)
      command -v gost >/dev/null 2>&1 || {
        echo "gost core selected, but gost binary is not installed in this image." >&2
        exit 1
      }
      core_cmd="gost -C /tmp/gost.json"
      ;;
    *)
      echo "Unsupported CORE: $CORE. Use xray or gost." >&2
      exit 1
      ;;
  esac

  write_core_config
  sh -c "$core_cmd" &
  core_pid="$!"

  if [ "$REFRESH_SECONDS" = "0" ]; then
    wait "$core_pid"
    exit $?
  fi

  while true; do
    sleep "$REFRESH_SECONDS"
    write_core_config
    kill "$core_pid" 2>/dev/null || true
    wait "$core_pid" 2>/dev/null || true
    sh -c "$core_cmd" &
    core_pid="$!"
  done
}

case "$CORE" in
  xray|gost)
    run_core
    ;;
  *)
    echo "Unsupported CORE: $CORE. Use xray or gost." >&2
    exit 1
    ;;
esac
