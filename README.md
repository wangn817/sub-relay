# Debian 订阅中转

这个方案把订阅链接转成中转服务配置。默认使用 gost，iptables 作为可选后端。

- `gost`：默认后端，用 gost 监听端口并转发，日志和运行状态更直观，不直接改宿主机防火墙规则。
- `iptables`：纯 DNAT 转发，最轻，不跑常驻代理进程。

两种后端都会保持：中转机监听端口 = 落地机端口。

## 适用范围

- 支持常见订阅格式：`vmess://`、`vless://`、`trojan://`、`ss://`、`ssr://`、`shadowsocks://`、`anytls://`、`hysteria2://`、`hy2://`、`tuic://` 等能解析出目标地址和端口的节点。
- 本方案不解密、不改代理协议，只做四层端口转发。
- 如果订阅里多个节点使用同一个落地端口但目标 IP 不同，同一台中转机同一个公网 IP 不能同时转发它们。脚本会报“端口冲突”。

## Docker 部署

在中转服务器安装 Docker 后，把本目录上传到服务器，然后执行：

```bash
docker compose up -d --build
```

如果已经发布成镜像，服务器只需要使用 `docker-compose.image.yml` 这种写法，把 `image:` 改成你的镜像地址后执行：

```bash
docker compose up -d
```

发布镜像的方法见 `PUBLISH.md`。

默认订阅链接在 `docker-compose.yml` 里。支持多个订阅链接，一行一个：

```yaml
BACKEND: "gost"
SUB_URLS: |
  https://example.com/sub/your-subscription
  http://example.com/sub/another
```

也可以用逗号分隔：

```yaml
SUB_URLS: "http://a.example/sub,https://b.example/sub"
```

旧配置 `SUB_URL: "..."` 仍然兼容。

选择后端，默认是：

```yaml
BACKEND: "gost"
```

也可以切回 iptables：

```yaml
BACKEND: "iptables"
```

如果需要定时刷新订阅，把 `REFRESH_SECONDS` 改成秒数，例如每小时刷新：

```yaml
REFRESH_SECONDS: "3600"
```

使用 `gost` 后端时，也建议保留 `network_mode: host`，这样 gost 可以直接监听中转机端口。`gost` 后端不需要 `NET_ADMIN`，但保留也不影响运行；如果你只用 gost，可以删掉 `cap_add`。

使用 `iptables` 后端时，容器必须使用：

- `network_mode: host`
- `cap_add: NET_ADMIN, NET_RAW`

否则容器里的 iptables 规则不会作用到中转机网络命名空间。

## 不用 Docker，直接在 Debian 执行

生成 gost 配置：

```bash
apt-get update
apt-get install -y python3 ca-certificates
chmod +x sub-relay.py
./sub-relay.py --backend gost \
  "https://example.com/sub/your-subscription" \
  > gost.json
gost -C gost.json
```

生成并应用 iptables 规则：

```bash
apt-get update
apt-get install -y iptables python3 ca-certificates
chmod +x sub-relay.py
./sub-relay.py --backend iptables \
  "https://example.com/sub/your-subscription" \
  "http://example.com/sub/another" \
  > apply-sub-relay.sh
sh apply-sub-relay.sh
```

## gost 后端逻辑

脚本会为每个落地端口生成一个 TCP 服务和一个 UDP 服务，例如：

```json
{
  "services": [
    {
      "name": "tcp-443-node",
      "addr": ":443",
      "handler": { "type": "tcp" },
      "listener": { "type": "tcp" },
      "forwarder": {
        "nodes": [
          { "name": "1.2.3.4:443", "addr": "1.2.3.4:443" }
        ]
      }
    }
  ]
}
```

也就是：gost 监听中转机 `:443`，再转发到落地机 `1.2.3.4:443`。

`gost` 后端更适合想看日志、少碰系统防火墙、后续扩展健康检查或更多转发策略的场景。

## iptables 后端逻辑

脚本会创建一个 nat 表链，默认叫 `SUB_RELAY`：

```bash
iptables -t nat -N SUB_RELAY
iptables -t nat -A PREROUTING -j SUB_RELAY
iptables -t nat -A POSTROUTING -j MASQUERADE
```

每个节点生成类似规则：

```bash
iptables -t nat -A SUB_RELAY -p tcp --dport 443 -j DNAT --to-destination 1.2.3.4:443
iptables -t nat -A SUB_RELAY -p udp --dport 443 -j DNAT --to-destination 1.2.3.4:443
```

也就是：访问中转机 `中转IP:443` 会被转到落地机 `1.2.3.4:443`。

## iptables 查看和清理

查看：

```bash
iptables -t nat -S SUB_RELAY
iptables -t nat -S PREROUTING
iptables -t nat -S POSTROUTING
```

清理：

```bash
iptables -t nat -D PREROUTING -j SUB_RELAY 2>/dev/null || true
iptables -t nat -F SUB_RELAY 2>/dev/null || true
iptables -t nat -X SUB_RELAY 2>/dev/null || true
```

如果你确认这台机器只用这一套转发，可以额外手工删除 `POSTROUTING -j MASQUERADE`；脚本没有自动删它，避免影响其他转发。
