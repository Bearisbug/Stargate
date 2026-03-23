# GPU 可用性验证

> 参考：[nvidia-smi 官方文档](https://docs.nvidia.com/deploy/nvidia-smi/index.html) | [Docker GPU access](https://docs.docker.com/engine/containers/gpu/)

## 各执行环境下的 GPU 启用

### Conda / 直接运行

```bash
# 验证 GPU 可见
nvidia-smi
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"

# 指定 GPU
CUDA_VISIBLE_DEVICES=0 python train.py
```

### Docker

```bash
# 启动时传入 --gpus 参数
docker run --gpus all <image> nvidia-smi

# 验证容器内可见
docker run --gpus all <image> python -c "import torch; print(torch.cuda.is_available())"
```

→ 详见 `references/envs/docker.md`

### Singularity / Apptainer

```bash
# 启动时传入 --nv 参数
apptainer exec --nv <image.sif> nvidia-smi
SINGULARITYENV_CUDA_VISIBLE_DEVICES=0 apptainer exec --nv <image.sif> python train.py
```

→ 详见 `references/envs/singularity.md`

### Slurm

在 job script 中声明 GPU 资源：
```bash
#SBATCH --gres=gpu:1
```
分配后容器 / 进程自动可见对应 GPU，通常不需要手动设置 `CUDA_VISIBLE_DEVICES`。

→ 详见 `references/servers/slurm.md`

---

## GPU 不可用时的分层诊断

```
宿主机层
  └─ nvidia-smi 报错或无输出
        → 驱动未安装或已损坏，联系管理员
        → 检查：lspci | grep -i nvidia

驱动层
  └─ nvidia-smi 正常，但 torch.cuda.is_available() = False
        → CUDA 版本与 PyTorch 不匹配
        → 检查：nvidia-smi（右上角显示 CUDA 版本上限）
                python -c "import torch; print(torch.version.cuda)"

容器层（Docker）
  └─ 容器内 nvidia-smi 报错
        → NVIDIA Container Toolkit 未安装或 Docker daemon 未配置
        → 修复：sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker

容器层（Singularity）
  └─ 容器内 nvidia-smi 报错
        → 未使用 --nv 参数，或宿主机驱动不兼容
        → 修复：加 --nv；检查宿主机 CUDA driver 版本

权限层
  └─ Permission denied 访问 /dev/nvidia*
        → 当前用户不在 video/render 组
        → 修复：sudo usermod -aG video $USER（需重新登录生效）
```

## 快速验证命令

```bash
# 宿主机 GPU 状态
nvidia-smi

# PyTorch GPU 可用性
python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| Devices:', torch.cuda.device_count(), '| Current:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```
