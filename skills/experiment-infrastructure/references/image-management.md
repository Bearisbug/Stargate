# 镜像管理

## 拉取流程

```bash
docker pull <image_tag>
```

失败时按顺序尝试：
1. `docker images <image_tag>` → 本地有则直接用，tracker 备注 `used_local_image: true`
2. `~/.stargate/images/<tag>.tar` 存在 → `docker load -i <path>.tar`
3. 均无 → 标记 `blocked: image_unavailable`

提示用户：
```
在有网环境执行：docker save <image_tag> > ~/.stargate/images/<image_tag>.tar
```

## 基础镜像清单

| 标签 | 内容 |
|------|------|
| `base-pytorch-cu121` | Python 3.11 + PyTorch 2.2 + CUDA 12.1 |
| `base-pytorch-cu118` | Python 3.10 + PyTorch 2.0 + CUDA 11.8 |
| `base-jax-cu121` | Python 3.11 + JAX 0.4 + CUDA 12.1 |
| `base-cpu` | Python 3.11，无 GPU |
