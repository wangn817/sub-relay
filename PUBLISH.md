# 发布 Docker 镜像

发布后，服务器只需要一个 `docker-compose.yml`，不用上传源码，也不用在服务器上构建镜像。

## 方式一：发布到 GitHub Container Registry

当前发布目标：

```text
ghcr.io/wangn817/sub-relay:latest
```

1. 把本目录作为 GitHub 仓库推上去。
2. 确认仓库启用了 Actions。
3. 推送到 `main` 分支后，`.github/workflows/docker-publish.yml` 会自动构建并发布镜像：

```text
ghcr.io/wangn817/sub-relay:latest
```

4. `docker-compose.image.yml` 里的镜像名：

```yaml
image: ghcr.io/wangn817/sub-relay:latest
```

5. 在中转服务器上保存为 `docker-compose.yml`，然后执行：

```bash
docker compose up -d
```

如果 GHCR 包是私有的，需要先登录：

```bash
docker login ghcr.io
```

建议把 GHCR package 设置成 public，这样服务器不需要登录。

## 方式二：手动发布到 Docker Hub

假设 Docker Hub 用户名是 `YOUR_DOCKERHUB_NAME`：

```bash
docker login
docker build -t YOUR_DOCKERHUB_NAME/sub-relay:latest .
docker push YOUR_DOCKERHUB_NAME/sub-relay:latest
```

服务器上的 compose 写：

```yaml
services:
  sub-relay:
    image: YOUR_DOCKERHUB_NAME/sub-relay:latest
    container_name: sub-relay
    network_mode: host
    environment:
      CORE: "xray"
      SUB_URLS: |
        https://example.com/sub/your-subscription
      PROTOCOLS: "tcp,udp"
      REFRESH_SECONDS: "0"
    restart: unless-stopped
```

然后执行：

```bash
docker compose up -d
```
