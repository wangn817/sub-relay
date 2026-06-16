# 订阅中转

这个项目把代理订阅链接转换成 Xray `dokodemo-door` 中转配置，并在 Docker 容器里启动 Xray 做 TCP/UDP 四层转发。

中转规则保持：

```text
中转机端口 = 落地机端口
```

## 适用范围

- 支持常见订阅格式：`vmess://`、`vless://`、`trojan://`、`ss://`、`ssr://`、`shadowsocks://`、`anytls://`、`hysteria2://`、`hy2://`、`tuic://` 等能解析出目标地址和端口的节点。
- 不解密、不改代理协议，只做四层转发。
- 默认同时转发 TCP 和 UDP。
- 适合 hy2 / hysteria2 / QUIC 这类 UDP 场景。
- 如果订阅里多个节点使用同一个落地端口但目标 IP 不同，同一台中转机同一个公网 IP 不能同时转发它们，脚本会报“端口冲突”。

## Docker 部署

直接使用已发布镜像：

```yaml
services:
  sub-relay:
    image: ghcr.io/wangn817/sub-relay:latest
    container_name: sub-relay
    network_mode: host
    environment:
      SUB_URLS: |
        https://example.com/sub/your-subscription
      PROTOCOLS: "tcp,udp"
      REFRESH_SECONDS: "0"
    restart: unless-stopped
```

启动：

```bash
docker compose up -d
```

更新：

```bash
docker compose pull
docker compose up -d
```

## 多订阅

一行一个：

```yaml
SUB_URLS: |
  https://example.com/sub/a
  https://example.com/sub/b
```

或者逗号分隔：

```yaml
SUB_URLS: "https://example.com/sub/a,https://example.com/sub/b"
```

旧配置 `SUB_URL: "..."` 仍然兼容。

## 协议

默认：

```yaml
PROTOCOLS: "tcp,udp"
```

只转发 TCP：

```yaml
PROTOCOLS: "tcp"
```

只转发 UDP：

```yaml
PROTOCOLS: "udp"
```

## 定时刷新

默认启动时拉取一次订阅：

```yaml
REFRESH_SECONDS: "0"
```

每小时刷新一次：

```yaml
REFRESH_SECONDS: "3600"
```

刷新时会重新生成 Xray 配置并重启 Xray 进程。

## 日志

生成的 Xray 配置会关闭访问日志：

```json
"log": {
  "access": "none",
  "loglevel": "warning"
}
```

这样不会持续输出每条连接的 `accepted ...` 记录。Xray 启动时显示的版本信息和 `A unified platform for anti-censorship.` 是启动横幅，不影响服务。

## 不用 Docker

生成 Xray 配置：

```bash
apt-get update
apt-get install -y python3 ca-certificates
chmod +x sub-relay.py
./sub-relay.py "https://example.com/sub/your-subscription" > xray.json
xray -config xray.json
```

## Xray 配置示例

脚本会为每个落地端口生成 `dokodemo-door` 入站，例如：

```json
{
  "inbounds": [
    {
      "tag": "relay-443-node",
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "dokodemo-door",
      "settings": {
        "address": "1.2.3.4",
        "port": 443,
        "network": "tcp,udp"
      }
    }
  ],
  "outbounds": [
    { "tag": "direct", "protocol": "freedom" }
  ]
}
```
