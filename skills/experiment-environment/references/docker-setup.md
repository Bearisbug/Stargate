# Remote Docker 环境初始化

## 流程

1. 检查 SSH 连通性
2. 拉取/验证镜像
3. 启动容器
4. 验证容器运行 + GPU
5. 写入 env_handle.json

## 步骤

### 1. 检查 SSH

```bash
ssh -o ConnectTimeout=10 <host> "echo ok"
# 失败 → blocked: ssh_unreachable
```

### 1b. gpu_count 自动估算（用户未指定时）

```bash
# 获取服务器实际 GPU 数量和显存
ssh <host> "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"
```

根据返回行数和显存，结合模型规模估算所需卡数（规则见 SKILL.md gpu_count 估算部分）。
估算结果告知用户并写入 env_handle.json，用户可在计划确认时修改。

### 2. 镜像准备

```bash
ssh <host> "docker pull <image>"
# 失败 → 见 experiment-infrastructure/references/image-management.md 的 fallback 流程
```

### 3. 启动容器

```bash
# gpu_count > 0
ssh <host> "docker run -d --gpus all \
  --name <container_name> \
  -v <work_dir>:<work_dir> \
  <image> tail -f /dev/null"

# gpu_count == 0
ssh <host> "docker run -d \
  --name <container_name> \
  -v <work_dir>:<work_dir> \
  <image> tail -f /dev/null"
```

容器已存在时，先检查状态：

```bash
ssh <host> "docker inspect --format='{{.State.Status}}' <container_name>"
# running → 直接复用
# exited  → docker start <container_name>
# 不存在  → 执行上面的 docker run
```

获取 container_id：

```bash
ssh <host> "docker inspect --format='{{.Id}}' <container_name>"
```

### 4. 验证

```bash
# 容器响应
ssh <host> "docker exec <container_id> echo ok"

# GPU（gpu_count > 0）
ssh <host> "docker exec <container_id> nvidia-smi --query-gpu=name --format=csv,noheader"
# 返回行数须 >= gpu_count，否则 blocked: gpu_unavailable
```

### 5. 写入 env_handle.json

```json
{
  "exec_type": "remote-docker",
  "host": "<host>",
  "container_id": "<container_id>",
  "container_name": "<container_name>",
  "work_dir": "<work_dir>",
  "gpu_count": <gpu_count>,
  "status": "ready"
}
```
