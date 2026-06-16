#!/bin/sh
set -eu

: "${SUB_URLS:=${SUB_URL:-}}"
: "${SUB_URLS:?Set SUB_URLS or SUB_URL to your subscription URL(s)}"
: "${BACKEND:=gost}"
: "${PROTOCOLS:=tcp,udp}"
: "${CHAIN:=SUB_RELAY}"
: "${REFRESH_SECONDS:=0}"

write_subscriptions() {
  printf '%s\n' "$SUB_URLS" | tr ',' '\n' | sed '/^[[:space:]]*$/d; /^[[:space:]]*#/d' > /tmp/subscriptions.txt
}

apply_iptables_rules() {
  write_subscriptions
  /app/sub-relay.py --backend iptables --subscription-list /tmp/subscriptions.txt --protocols "$PROTOCOLS" --chain "$CHAIN" > /tmp/apply-sub-relay.sh
  sh /tmp/apply-sub-relay.sh
}

write_gost_config() {
  write_subscriptions
  /app/sub-relay.py --backend gost --subscription-list /tmp/subscriptions.txt --protocols "$PROTOCOLS" > /tmp/gost.json
}

run_gost() {
  command -v gost >/dev/null 2>&1 || {
    echo "gost backend selected, but gost binary is not installed in this image." >&2
    exit 1
  }
  write_gost_config
  gost -C /tmp/gost.json &
  gost_pid="$!"

  if [ "$REFRESH_SECONDS" = "0" ]; then
    wait "$gost_pid"
    exit $?
  fi

  while true; do
    sleep "$REFRESH_SECONDS"
    write_gost_config
    kill "$gost_pid" 2>/dev/null || true
    wait "$gost_pid" 2>/dev/null || true
    gost -C /tmp/gost.json &
    gost_pid="$!"
  done
}

case "$BACKEND" in
  iptables)
    apply_iptables_rules
    if [ "$REFRESH_SECONDS" = "0" ]; then
      tail -f /dev/null
    fi
    while true; do
      sleep "$REFRESH_SECONDS"
      apply_iptables_rules
    done
    ;;
  gost)
    run_gost
    ;;
  *)
    echo "Unsupported BACKEND: $BACKEND. Use iptables or gost." >&2
    exit 1
    ;;
esac
