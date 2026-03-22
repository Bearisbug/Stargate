---
name: experiment-environment
description: 初始化实验执行环境：从对话或 env_config.json 中获取环境信息，连接远端服务器，启动/验证容器，写入 env_handle.json。在跑实验前需要准备好环境时使用。
---

# 实验环境初始化

## 获取环境信息

优先读取当前目录的 `env_config.json`；不存在时，从对话上下文中提取：

| 字段 | 提取方式 |
|------|---------|
| `exec_type` | 见下方**探测流程**；用户措辞仅作参考 |
| `host` | 用户提供的 IP 或域名，格式补全为 `user@host`（用户名未提供时询问） |
| `image` | 用户提到框架/任务 → 按下表选择；用户指定时直接用 |
| `work_dir` | 用户提供；未提供时使用 `/workspace` |
| `gpu_count` | 用户指定时直接用；未指定时按下方**自动估算**流程决定 |

### exec_type 探测流程

有 `host` 时，SSH 进去探测，**不靠用户措辞推断**：

```bash
ssh <host> "command -v sbatch sinfo 2>/dev/null | head -1;
            command -v docker 2>/dev/null;
            command -v singularity apptainer 2>/dev/null | head -1"
```

| 探测结果 | exec_type |
|---------|-----------|
| 有 `sbatch` / `sinfo` | `slurm-singularity` |
| 无 Slurm，有 `docker` | `remote-docker` |
| 无 Slurm，无 Docker，有 `singularity`/`apptainer` | `remote-singularity` |
| 均无 | `ssh` |

`host` 不存在（本地任务）→ `local`。

**镜像自动选择：**

| 用户描述 | 选择镜像 |
|---------|---------|
| PyTorch / 训练 / SFT / RFT / DL | `base-pytorch-cu121` |
| JAX / Flax | `base-jax-cu121` |
| 旧环境 / CUDA 11 | `base-pytorch-cu118` |
| 无 GPU / 数据处理 | `base-cpu` |

### gpu_count 自动估算

用户未指定时，执行以下流程（**不打断用户询问**）：

**1. 获取单卡显存**
```bash
ssh <host> "sinfo -p <partition> -o '%G %N' --noheader | head -1"
# 得到 GPU 型号，再查单卡显存：
ssh <host> "srun -p <partition> --gres=gpu:1 --pty nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1"
# 若 srun 交互受限，从已知型号估算：H20=96GB, A100=80GB, V100=32GB, RTX3090=24GB
```

**2. 估算模型显存需求**

有 `config.json` 时读参数量，否则按名称估算：

```bash
ssh <host> "python3 -c \"
import json, math
cfg = json.load(open('<model_path>/config.json'))
# 参数量 ≈ hidden*layers*... 或直接取 num_parameters 字段
params = cfg.get('num_parameters') or \
    cfg.get('hidden_size',0) * cfg.get('num_hidden_layers',0) * 12
gb = params * 2 / 1e9   # bfloat16: 2 bytes/param
print(f'{gb:.1f}')
\""
```

按模型名推断的兜底估算：

| 模型规模 | bf16 显存 | 训练（含梯度+优化器） |
|---------|----------|-------------------|
| 7B      | ~14 GB   | ~60 GB            |
| 13B     | ~26 GB   | ~110 GB           |
| 70B     | ~140 GB  | ~560 GB           |

**3. 决定 gpu_count**

```
推理：ceil(模型显存 / 单卡显存 * 1.2)   # 20% 余量
训练：ceil(训练显存 / 单卡显存 * 1.1)   # 建议整卡，尽量不跨机
```

结果告知用户（"预计需要 N 卡，原因：…"），**自动写入 env_handle.json 并继续**，用户可在计划确认时修改。

信息不足时**只询问缺失的必填字段**，不打断用户填写完整表单。

提取完成后写入 `env_config.json`（供后续复用），再执行初始化流程。

## 初始化流程

1. 按 exec_type 建立连接并准备容器 → 见对应 reference
2. 验证 GPU（gpu_count > 0 时）
3. 写入 `env_handle.json`（status: `ready`）

| exec_type | 参考 |
|-----------|------|
| `remote-docker` | [references/docker-setup.md](references/docker-setup.md) |
| `remote-singularity` | [references/singularity-setup.md](references/singularity-setup.md) |
| `slurm-singularity` | [references/singularity-setup.md](references/singularity-setup.md) |
| `ssh` / `local` | 仅验证连通性，无需容器操作 |

## 输出：env_handle.json

status 只有两个值：`ready` 或 `blocked: <reason>`。
blocked 时不写 env_handle.json，直接输出原因和解决方案。

## 遇到问题

- SSH 无法连接 → `blocked: ssh_unreachable`
- 镜像不可用 → 见 [experiment-infrastructure/references/image-management.md](../experiment-infrastructure/references/image-management.md)
- GPU 不可用但 gpu_count > 0 → `blocked: gpu_unavailable`
