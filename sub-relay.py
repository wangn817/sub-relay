#!/usr/bin/env python3
import argparse
import base64
import binascii
import json
import re
import sys
import urllib.parse
import urllib.request


SUPPORTED_GENERIC_SCHEMES = {
    "vless",
    "trojan",
    "tuic",
    "hysteria2",
    "hy2",
    "hysteria",
    "http",
    "https",
    "socks",
    "socks5",
    "anytls",
    "shadowsocks",
}

UDP_ONLY_SCHEMES = {"hysteria", "hysteria2", "hy2", "tuic"}
TCP_UDP_SCHEMES = {"ss", "shadowsocks"}
TCP_ONLY_SCHEMES = {"vmess", "vless", "trojan", "anytls", "http", "https", "socks", "socks5", "ssr"}
LOG_LEVELS = {"debug", "info", "warning", "error", "none"}


def b64decode_text(value):
    text = value.strip()
    text = re.sub(r"\s+", "", text)
    if not text:
        return ""
    padding = "=" * ((4 - len(text) % 4) % 4)
    try:
        return base64.urlsafe_b64decode((text + padding).encode()).decode("utf-8", "replace")
    except (binascii.Error, UnicodeDecodeError):
        return ""


def maybe_decode_subscription(raw):
    stripped = raw.strip()
    if "://" in stripped:
        return stripped
    decoded = b64decode_text(stripped)
    if "://" in decoded:
        return decoded
    return stripped


def fetch_subscription(source):
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": "sub-relay/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", "replace")
    with open(source, "r", encoding="utf-8") as f:
        return f.read()


def split_nodes(subscription_text):
    text = maybe_decode_subscription(subscription_text)
    nodes = []
    for line in text.replace("\r", "\n").split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "://" in line:
            nodes.append(line)
    return nodes


def parse_host_port_from_url(node, scheme):
    parsed = urllib.parse.urlsplit(node)
    host = parsed.hostname
    port = parsed.port
    name = urllib.parse.unquote(parsed.fragment or host or "")
    if host and port:
        return {"scheme": scheme, "host": host, "port": int(port), "name": name}
    return None


def parse_vmess(node):
    payload = node[len("vmess://") :]
    decoded = b64decode_text(payload)
    if not decoded:
        return None
    try:
        data = json.loads(decoded)
    except json.JSONDecodeError:
        return None
    host = data.get("add")
    port = data.get("port")
    if host and port:
        return {
            "scheme": "vmess",
            "host": str(host),
            "port": int(port),
            "name": str(data.get("ps") or host),
        }
    return None


def parse_ss(node):
    parsed = urllib.parse.urlsplit(node)
    name = urllib.parse.unquote(parsed.fragment or "")
    if parsed.hostname and parsed.port:
        return {"scheme": "ss", "host": parsed.hostname, "port": int(parsed.port), "name": name or parsed.hostname}

    payload = node[len("ss://") :].split("#", 1)[0].split("?", 1)[0]
    decoded = b64decode_text(payload)
    match = re.search(r"@(\[[^\]]+\]|[^:]+):(\d+)", decoded)
    if match:
        host = match.group(1).strip("[]")
        return {"scheme": "ss", "host": host, "port": int(match.group(2)), "name": name or host}
    return None


def parse_ssr(node):
    payload = node[len("ssr://") :]
    decoded = b64decode_text(payload)
    parts = decoded.split(":")
    if len(parts) >= 6 and parts[1].isdigit():
        return {"scheme": "ssr", "host": parts[0], "port": int(parts[1]), "name": parts[0]}
    return None


def parse_node(node):
    scheme = node.split("://", 1)[0].lower()
    try:
        if scheme == "vmess":
            return parse_vmess(node)
        if scheme == "ss":
            return parse_ss(node)
        if scheme == "ssr":
            return parse_ssr(node)
        if scheme in SUPPORTED_GENERIC_SCHEMES:
            return parse_host_port_from_url(node, scheme)
    except ValueError:
        return None
    return None


def unique_targets(nodes):
    targets = []
    seen = set()
    for node in nodes:
        parsed = parse_node(node)
        if not parsed:
            continue
        key = (parsed["host"], parsed["port"])
        if key not in seen:
            seen.add(key)
            targets.append(parsed)
    return targets


def target_protocols(target, selected_protocols):
    if selected_protocols != ["auto"]:
        return selected_protocols
    scheme = target["scheme"]
    if scheme in UDP_ONLY_SCHEMES:
        return ["udp"]
    if scheme in TCP_UDP_SCHEMES:
        return ["tcp", "udp"]
    if scheme in TCP_ONLY_SCHEMES:
        return ["tcp"]
    return ["tcp", "udp"]


def targets_by_port(targets, selected_protocols):
    by_port = {}
    conflicts = []
    for target in targets:
        port = target["port"]
        current = by_port.get(port)
        target["protocols"] = target_protocols(target, selected_protocols)
        if current and (current["host"] != target["host"] or current["protocols"] != target["protocols"]):
            conflicts.append((port, current["host"], ",".join(current["protocols"]), target["host"], ",".join(target["protocols"])))
        else:
            by_port[port] = target

    if conflicts:
        print("端口冲突：同一个中转端口不能同时转发到多个不同目标或协议组合。", file=sys.stderr)
        for port, first_host, first_protocols, second_host, second_protocols in conflicts:
            print(f"  {port}: {first_host} ({first_protocols}) / {second_host} ({second_protocols})", file=sys.stderr)
        sys.exit(2)
    return by_port


def normalize_log_path(value):
    if value == "stdout":
        return "/dev/stdout"
    if value == "stderr":
        return "/dev/stderr"
    return value


def emit_xray_config(targets, selected_protocols, log_level, access_log, error_log):
    by_port = targets_by_port(targets, selected_protocols)
    inbounds = []
    for target in by_port.values():
        name_part = re.sub(r"[^a-zA-Z0-9_.-]+", "-", target["name"] or target["host"]).strip("-")[:40]
        network = ",".join(target["protocols"])
        inbounds.append(
            {
                "tag": f"relay-{target['port']}-{name_part or 'node'}",
                "listen": "0.0.0.0",
                "port": target["port"],
                "protocol": "dokodemo-door",
                "settings": {
                    "address": target["host"],
                    "port": target["port"],
                    "network": network,
                },
            }
        )
    log_config = {"access": normalize_log_path(access_log), "loglevel": log_level}
    if error_log:
        log_config["error"] = normalize_log_path(error_log)

    config = {
        "log": log_config,
        "inbounds": inbounds,
        "outbounds": [{"tag": "direct", "protocol": "freedom"}],
    }
    print(json.dumps(config, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Convert proxy subscription nodes to Xray relay config.")
    parser.add_argument("subscriptions", nargs="*", help="Subscription URL(s) or local subscription file(s)")
    parser.add_argument("--subscription-list", help="File containing subscription URL(s), one per line")
    parser.add_argument("--protocols", default="auto", help="auto or comma-separated protocols: tcp,udp")
    parser.add_argument("--log-level", default="warning", help="Xray log level: debug,info,warning,error,none")
    parser.add_argument("--access-log", default="none", help="Xray access log: none, stdout, stderr, or file path")
    parser.add_argument("--error-log", default="", help="Xray error log: stdout, stderr, file path, or empty for default")
    args = parser.parse_args()

    subscriptions = list(args.subscriptions)
    if args.subscription_list:
        with open(args.subscription_list, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    subscriptions.append(line)
    if not subscriptions:
        print("No subscription URL or file provided.", file=sys.stderr)
        sys.exit(1)

    nodes = []
    for subscription in subscriptions:
        raw = fetch_subscription(subscription)
        nodes.extend(split_nodes(raw))
    targets = unique_targets(nodes)
    if not targets:
        print("No supported nodes found in subscription.", file=sys.stderr)
        sys.exit(1)
    protocols = [p.strip().lower() for p in args.protocols.split(",") if p.strip()]
    invalid = sorted(set(protocols) - {"auto", "tcp", "udp"})
    if "auto" in protocols and len(protocols) > 1:
        invalid = ["auto with tcp/udp"]
    if invalid:
        print(f"Invalid protocol(s): {', '.join(invalid)}", file=sys.stderr)
        sys.exit(1)
    log_level = args.log_level.strip().lower()
    if log_level not in LOG_LEVELS:
        print(f"Invalid log level: {args.log_level}", file=sys.stderr)
        sys.exit(1)
    emit_xray_config(targets, protocols, log_level, args.access_log.strip(), args.error_log.strip())


if __name__ == "__main__":
    main()
