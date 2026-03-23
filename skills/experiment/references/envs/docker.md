# Docker 容器环境

> 参考：[Docker GPU access](https://docs.docker.com/engine/containers/gpu/) | [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

## 前提：NVIDIA Container Toolkit

使用 GPU 前必须在宿主机上安装 NVIDIA Container Toolkit：

```bash
# Ubuntu/Debian 安装
sudo apt-get install -y nvidia-container-toolkit

# 配置 Docker 使用 NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## 运行容器

```bash
# 挂载所有 GPU
docker run -it --rm --gpus all <image> nvidia-smi

# 指定 GPU（按 index）
docker run -it --rm --gpus device=0 <image>

# 指定多块 GPU
docker run -it --rm --gpus '"device=0,2"' <image>

# 按 UUID 指定（先用 nvidia-smi -L 查看）
docker run -it --rm --gpus device=GPU-3a23c669-... <image>
```

## 常用 run 参数

```bash
docker run \
  --gpus all \
  --rm \                              # 退出后自动删除容器
  -it \                               # 交互终端
  -v /host/data:/container/data \     # 挂载数据目录
  -v /host/code:/workspace \          # 挂载代码目录
  -w /workspace \                     # 设置工作目录
  --shm-size=8g \                     # 增大共享内存（多进程 DataLoader 需要）
  <image> python train.py
```

## 后台运行

```bash
# 后台运行，保留日志
docker run -d --gpus all \
  -v /host/data:/data \
  --name <job-name> \
  <image> python train.py

# 查看日志
docker logs -f <job-name>

# 查看运行状态
docker ps
docker inspect <job-name>

# 停止
docker stop <job-name>
docker rm <job-name>
```

## 拷贝结果

```bash
docker cp <container-name>:/workspace/outputs ./outputs
```

## 注意

- 一个容器只能被一个 Docker Engine 使用（NVIDIA 限制）
- `--shm-size` 不足时 PyTorch DataLoader 多进程会报 `Bus error`
- 使用官方 CUDA 镜像（`nvcr.io/nvidia/pytorch` 等）可避免手动配置 CUDA 库
