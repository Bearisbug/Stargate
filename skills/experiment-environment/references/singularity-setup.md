# Singularity / Apptainer 环境初始化

适用于 `remote-singularity` 和 `slurm-singularity`。

Singularity 无守护进程，无需启动容器，初始化只需验证连通性、镜像和 GPU。

## 流程

1. 检查 SSH 连通性
2. 验证 .sif 文件存在
3. 验证 singularity/apptainer 可用
4. 验证 GPU（如需）
5. 写入 env_handle.json

## 步骤

### 1. 检查 SSH

```bash
ssh -o ConnectTimeout=10 <host> "echo ok"
# 失败 → blocked: ssh_unreachable
```

### 2. 定位 .sif 文件

用户指定了 .sif 路径时，取 `realpath` 验证：

```bash
ssh <host> "realpath <sif_path> && test -f <sif_path> && echo ok || echo missing"
```

用户未指定时，在常见位置搜索可用镜像：

```bash
ssh <host> "find ~ /scratch /online1/<user> -name '*.sif' -o -name '*.simg' 2>/dev/null | head -20"
```

找到多个时，优先选含 `pytorch`/`torch`/`cuda` 的镜像；让用户从列表中确认或指定。

缺失时尝试构建（需有网环境）：

```bash
ssh <host> "singularity build <sif_path> docker://<image_tag>"
# 失败 → blocked: image_unavailable，提示用户手动构建后重试
```

### 3. 选择 singularity/apptainer 命令

集群上常存在多个版本或多个 binary，**必须选出一个可用的**：

```bash
# 收集所有候选 binary（含常见安装路径）
ssh <host> "find /opt /usr/local /online1 /software /apps -name singularity -o -name apptainer 2>/dev/null | head -20; command -v singularity; command -v apptainer"
```

**选择优先级：**
1. 有 setuid bit（`-rwsr-xr-x`）的 `singularity` → 最优先，不依赖 user namespace
2. 普通 `singularity` / `apptainer` → 次选
3. 均无 → `blocked: singularity_unavailable`

```bash
# 检查 setuid bit
ssh <host> "ls -la <binary_path>"
# -rwsr-xr-x 表示有 setuid → 选用
```

**验证可用性（用实际 .sif 测试一条命令）：**
```bash
ssh <host> "<runtime> exec <sif_path> echo ok 2>&1"
# 出现 'user namespace disabled' → 此 binary 不可用，换下一个候选
# 出现 'ok' → 可用，记录到 env_handle.json runtime 字段
```

记录到 env_handle.json 的 `runtime` 字段（存完整绝对路径）。

### 4. 验证 GPU（gpu_count > 0）

```bash
ssh <host> "nvidia-smi --query-gpu=name --format=csv,noheader"
# 返回行数须 >= gpu_count，否则 blocked: gpu_unavailable
```

### 5. 写入 env_handle.json

**remote-singularity：**

```json
{
  "exec_type": "remote-singularity",
  "host": "<host>",
  "sif_path": "<sif_path>",
  "bind_paths": "<bind_paths>",
  "work_dir": "<work_dir>",
  "gpu_count": <gpu_count>,
  "runtime": "singularity",
  "status": "ready"
}
```

**slurm-singularity（追加 Slurm 字段）：**

```json
{
  "exec_type": "slurm-singularity",
  "host": "<host>",
  "sif_path": "<sif_path>",
  "bind_paths": "<bind_paths>",
  "work_dir": "<work_dir>",
  "gpu_count": <gpu_count>,
  "runtime": "singularity",
  "partition": "<partition>",
  "time_limit": "<time_limit>",
  "slurm_log_dir": "<slurm_log_dir>",
  "status": "ready"
}
```

## bind_paths 确定方法

**不要盲目 bind work_dir**——Singularity 会自动挂载 `$HOME`，重复 bind 同一路径可能干扰。

```bash
# 1. 取 work_dir 的真实路径（解析 symlink）
ssh <host> "realpath <work_dir>"

# 2. 在容器内探测真实路径是否可见
ssh <host> "<runtime> exec <sif_path> bash -c 'ls <real_work_dir> 2>/dev/null && echo visible || echo missing'"

# 3. 如果 missing，找到需要 bind 的顶层目录（通常是真实路径的最顶层挂载点）
ssh <host> "df <real_work_dir> | tail -1 | awk '{print \$NF}'"
# 把该挂载点加入 bind_paths，例如 /online1:/online1
```

**规则：**
- 路径已自动可见 → `bind_paths` 留空
- 路径不可见 → bind 真实路径所在的顶层目录（不是 symlink）
- `runtime` 字段由初始化阶段检测写入，execution skill 执行时直接读取，无需重新检测

## Slurm 提交路径限制

部分集群限制 `sbatch` 只能在特定目录（如 `~/online1/`）下提交：

```bash
# sbatch 报错 "作业只能提交到..." 时，在报错提示的允许路径下执行
ssh <host> "cd <allowed_dir> && sbatch <script>"
```

初始化时记录允许路径到 env_handle.json `sbatch_cwd` 字段（如已知），执行 skill 提交时使用。
