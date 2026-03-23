# 公司内网服务器连接指南

## 前提：接入内网

内网服务器在公网不可达，连接前必须先接入公司网络：

- **已在内网**（办公室有线/Wi-Fi）：直接 SSH
- **远程办公**：先连 VPN，再 SSH
- **有堡垒机**：参考 `references/servers/bastion_host.md`

```bash
ssh <user>@<内网 IP>
```

## HTTP 代理配置

部分内网环境访问外网需要走代理（下载模型、数据集等）：

```bash
export http_proxy=http://<proxy_host>:<port>
export https_proxy=http://<proxy_host>:<port>

# 验证是否能访问外网
curl -I https://huggingface.co
```

工具单独设置代理：
```bash
# pip
pip install <package> --proxy http://<proxy_host>:<port>

# huggingface-cli
HF_ENDPOINT=https://hf-mirror.com huggingface-cli download <model>

# git
git config --global http.proxy http://<proxy_host>:<port>
```

代理不需要时记得取消：
```bash
unset http_proxy https_proxy
```

## 模型 / 数据下载离线方案

外网完全不通时的替代方案：

1. **HuggingFace 镜像**：`export HF_ENDPOINT=https://hf-mirror.com`
2. **本地镜像站**：询问 IT 是否有内部 PyPI / HuggingFace 镜像
3. **手动传输**：在可访问外网的机器上下载后 `scp` 传入

## 注意

- 内网 IP 在公司网络外不可达，确认 VPN 已连接再操作
- 敏感数据（训练数据、模型权重）不得上传到外部服务
- 防火墙可能封锁特定出站端口，下载失败时优先检查代理配置
