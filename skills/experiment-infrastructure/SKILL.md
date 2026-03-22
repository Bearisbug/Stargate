---
name: experiment-infrastructure
description: 管理实验执行环境：读取 env_handle.json，按执行类型在本地或远端容器内执行命令，收集 artifacts。在执行实验命令或配置环境时使用。
---

# 实验基础设施

## env_handle.json

读取执行环境配置，字段因 exec_type 而异：

```json
{
  "exec_type": "remote-docker | remote-singularity | slurm-singularity | ssh | local",
  "host": "user@gpu-server",
  "work_dir": "/workspace",
  "gpu_count": 4,
  "status": "ready"
}
```

各 exec_type 的额外字段和执行方式见下表，详见对应 reference：

| exec_type | 场景 | 参考 |
|-----------|------|------|
| `remote-docker` | 本地 Claude Code + 云端 Docker 容器 | [references/docker.md](references/docker.md) |
| `remote-singularity` | 本地 Claude Code + 远端 Singularity/Apptainer | [references/singularity.md](references/singularity.md) |
| `slurm-singularity` | HPC 集群，Slurm 调度 + Singularity | [references/singularity.md](references/singularity.md) |
| `ssh` | SSH 到远端直接执行，无容器 | — |
| `local` | 本地直接执行，无容器 | — |

## GPU 检查

`gpu_count > 0` 时：
```bash
# remote-docker
ssh <host> "docker exec <container_id> nvidia-smi"
# remote-singularity / ssh
ssh <host> "nvidia-smi"
# local
nvidia-smi
```

`gpu_count == 0` 跳过。

## 镜像管理

→ 见 [references/image-management.md](references/image-management.md)
