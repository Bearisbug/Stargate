# env_config.json 字段说明

用户提供的输入文件。`experiment-environment` skill 会自动探测并补全大部分字段，
不需要的字段可以省略。

## 通用字段

| 字段 | 必填 | 自动探测 | 说明 |
|------|:----:|:-------:|------|
| `exec_type` | — | ✅ SSH 探测 | 可省略；探测逻辑见 SKILL.md |
| `work_dir` | ✅ | — | 实验工作目录（远端绝对路径） |
| `gpu_count` | — | ✅ 自动估算 | 省略时自动估算并告知用户 |

## 按 exec_type 的额外字段

### remote-docker

```json
{
  "exec_type": "remote-docker",
  "host": "user@gpu-server",
  "image": "base-pytorch-cu121",
  "work_dir": "/workspace",
  "gpu_count": 4,
  "container_name": "stargate-exp"
}
```

| 字段 | 必填 | 自动 | 说明 |
|------|:----:|:----:|------|
| `host` | ✅ | — | SSH 目标，格式 `user@host` |
| `image` | — | ✅ 按任务选 | Docker 镜像标签，见镜像清单 |
| `container_name` | — | — | 默认 `stargate-exp` |

### remote-singularity / slurm-singularity

```json
{
  "exec_type": "slurm-singularity",
  "host": "user@hpc-login",
  "sif_path": "/scratch/images/base-pytorch-cu121.sif",
  "work_dir": "/scratch/project",
  "gpu_count": 4,
  "partition": "gpu",
  "time_limit": "24:00:00"
}
```

| 字段 | 必填 | 自动 | 说明 |
|------|:----:|:----:|------|
| `host` | ✅ | — | SSH 目标 |
| `sif_path` | — | ✅ 搜索可用镜像 | 远端 .sif 绝对路径；省略时自动搜索 |
| `partition` | ✅（slurm） | — | Slurm 分区名 |
| `time_limit` | — | — | 单 job 最长时间，默认 `24:00:00` |
| `slurm_log_dir` | — | — | 日志目录，默认 `<work_dir>/logs` |

**自动探测、不需要用户填写的字段**（写入 env_handle.json，不在 env_config.json 中）：

| 字段 | 说明 |
|------|------|
| `runtime` | singularity/apptainer 完整路径，初始化时探测 |
| `bind_paths` | 根据 work_dir 是否在容器内可见自动决定 |
| `sbatch_cwd` | sbatch 的允许提交路径，报错时探测 |

### ssh

```json
{
  "exec_type": "ssh",
  "host": "user@gpu-server",
  "work_dir": "/home/user/project",
  "gpu_count": 2
}
```

### local

```json
{
  "exec_type": "local",
  "work_dir": "/home/user/project",
  "gpu_count": 1
}
```

## 最小输入示例

只提供必须由用户决定的信息，其余全部自动探测：

```json
{
  "host": "user@192.168.1.10",
  "work_dir": "/scratch/my-exp"
}
```

skill 会自动探测 exec_type、选镜像/sif、估算 gpu_count、确定 bind_paths 等。
