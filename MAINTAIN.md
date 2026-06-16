# 维护和发布

项目仓库：

```text
https://github.com/wangn817/sub-relay
```

镜像地址：

```text
ghcr.io/wangn817/sub-relay:latest
```

## 日常更新流程

进入项目目录：

```bash
cd sub-relay
```

查看改动：

```bash
git status
```

提交改动：

```bash
git add .
git commit -m "Update relay"
```

推送到 GitHub：

```bash
git push
```

推送到 `main` 分支后，GitHub Actions 会自动构建并推送 Docker 镜像：

```text
ghcr.io/wangn817/sub-relay:latest
```

## 服务器更新容器

服务器上的 `docker-compose.yml` 使用：

```yaml
services:
  sub-relay:
    image: ghcr.io/wangn817/sub-relay:latest
    container_name: sub-relay
    network_mode: host
    environment:
      CORE: "xray"
      SUB_URLS: |
        你的订阅链接
      PROTOCOLS: "tcp,udp"
      REFRESH_SECONDS: "0"
    restart: unless-stopped
```

更新镜像并重启：

```bash
docker compose pull
docker compose up -d
```

查看日志：

```bash
docker logs -f sub-relay
```

## 发布版本标签

如果要发布一个固定版本，例如 `v1.0.0`：

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions 会额外发布：

```text
ghcr.io/wangn817/sub-relay:v1.0.0
```

服务器可以把 compose 里的镜像从 `latest` 改成固定版本：

```yaml
image: ghcr.io/wangn817/sub-relay:v1.0.0
```
