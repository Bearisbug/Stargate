# Singularity / Apptainer 执行

适用于 `remote-singularity` 和 `slurm-singularity`。

## env_handle.json 字段

由 `experiment-environment` skill 初始化后写入，执行层只读不写。

**remote-singularity：**

```json
{
  "exec_type": "remote-singularity",
  "host": "user@hpc-login",
  "sif_path": "/scratch/images/base-pytorch-cu121.sif",
  "bind_paths": "/scratch,/data",
  "work_dir": "/scratch/project",
  "gpu_count": 4,
  "runtime": "/usr/local/bin/singularity",
  "status": "ready"
}
```

**slurm-singularity（追加字段）：**

```json
{
  "exec_type": "slurm-singularity",
  "host": "user@hpc-login",
  "sif_path": "/scratch/images/base-pytorch-cu121.sif",
  "bind_paths": "/scratch,/data",
  "work_dir": "/scratch/project",
  "gpu_count": 4,
  "runtime": "/usr/local/bin/singularity",
  "partition": "gpu",
  "time_limit": "24:00:00",
  "slurm_log_dir": "/scratch/project/logs",
  "sbatch_cwd": "/online1/user",
  "status": "ready"
}
```

| 字段 | 来源 | 说明 |
|------|------|------|
| `runtime` | 自动探测 | singularity/apptainer 的完整绝对路径 |
| `bind_paths` | 自动探测或用户指定 | 为空时执行命令省略 `--bind` |
| `sbatch_cwd` | 自动探测（仅 slurm） | sbatch 的允许提交路径；为空时用 `work_dir` |

## 执行命令

`runtime` 和 `bind_paths` 从 env_handle.json 读取；`bind_paths` 为空时省略 `--bind`。

命令中用**绝对路径**，不依赖容器内 cwd。

### remote-singularity（直接 SSH + singularity exec）

```bash
# bind_paths 非空
ssh <host> "<runtime> exec --nv --bind <bind_paths> <sif_path> python3 <work_dir>/script.py <args>"
# bind_paths 为空
ssh <host> "<runtime> exec --nv <sif_path> python3 <work_dir>/script.py <args>"
```

无 GPU 时去掉 `--nv`。

### slurm-singularity（写 job script 再 sbatch）

优先用 job script 文件而非 `--wrap`，便于调试和重跑：

```bash
# 生成 job script
cat > <work_dir>/run_<run_id>.sh << 'EOF'
#!/bin/bash
#SBATCH --job-name=<name>
#SBATCH --partition=<partition>
#SBATCH --gres=gpu:<gpu_count>
#SBATCH --cpus-per-task=<cpus>
#SBATCH --mem=<mem>
#SBATCH --time=<time_limit>
#SBATCH --output=<slurm_log_dir>/run_<run_id>_%j.out
#SBATCH --error=<slurm_log_dir>/run_<run_id>_%j.err

<runtime> exec --nv [--bind <bind_paths>] <sif_path> \
    python3 <work_dir>/train.py <args>
EOF

# 从 sbatch_cwd（env_handle.json）指定的路径提交
ssh <host> "cd <sbatch_cwd> && sbatch <work_dir>/run_<run_id>.sh"
```

返回 job_id，记录到 rounds/<run_id>.json，再按 monitor.md 轮询。

## Artifact 收集

容器内路径直接映射到宿主机（通过 --bind），无需 docker cp：

```bash
rsync -az <host>:<artifact_path>/ <local_output_dir>/
```

## 镜像管理

.sif 文件由 Environment 模块提前放置到 `sif_path`，执行模块检查文件是否存在：

```bash
ssh <host> "test -f <sif_path>" || echo "blocked: image_unavailable"
```

无法拉取时提示用户在有网环境构建：

```bash
singularity build <sif_path> docker://<image_tag>
```
