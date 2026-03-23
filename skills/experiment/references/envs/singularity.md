# Singularity / Apptainer 容器环境

> 参考：[Apptainer GPU Support](https://apptainer.org/user-docs/3.8/gpu.html)

HPC 集群常用 Apptainer（原 Singularity）替代 Docker，因为它不需要 root 权限。

## 获取镜像

```bash
# 从 Docker Hub 拉取，转换为 SIF 格式
apptainer pull docker://pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# 从本地 Docker 镜像构建
apptainer build my_image.sif docker-daemon://my_image:latest

# 从已有 SIF 文件
# 直接使用，无需额外步骤
```

## 运行容器（GPU）

使用 `--nv` 启用 NVIDIA GPU 支持：

```bash
# 执行命令
apptainer exec --nv my_image.sif python train.py

# 交互 shell
apptainer shell --nv my_image.sif

# 直接 run（使用镜像默认入口）
apptainer run --nv my_image.sif
```

`--nv` 的作用：
1. 将宿主机 `/dev/nvidiaX` 设备映射进容器
2. 将宿主机 CUDA 库绑定进容器
3. 自动设置 `LD_LIBRARY_PATH`

## 控制使用哪块 GPU

```bash
# 只使用第 0 块 GPU
SINGULARITYENV_CUDA_VISIBLE_DEVICES=0 apptainer run --nv my_image.sif python train.py

# 使用第 0 和第 2 块
SINGULARITYENV_CUDA_VISIBLE_DEVICES=0,2 apptainer run --nv my_image.sif python train.py
```

## 挂载目录

```bash
apptainer exec --nv \
  --bind /host/data:/data \
  --bind /host/code:/workspace \
  my_image.sif python /workspace/train.py
```

默认情况下，`$HOME`、`/tmp`、`/proc`、`/sys`、`/dev` 会自动挂载。

## 与 Slurm 结合

在 job script 中：

```bash
#!/bin/bash
#SBATCH --gres=gpu:1
...
module load apptainer   # 或 singularity，集群不同命令不同
apptainer exec --nv /path/to/my_image.sif python train.py
```

## 注意

- 容器内应用须与宿主机 CUDA driver 版本兼容（容器 CUDA 版本 ≤ 宿主 driver 支持的最高版本）
- 遇到 `CUDA_ERROR_UNKNOWN` 时，先在宿主机上运行一个 CUDA 程序初始化 driver stack
- SIF 文件是单个只读文件，适合分发和存档
