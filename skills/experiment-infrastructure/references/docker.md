# Remote Docker 执行

## env_handle.json 字段

```json
{
  "exec_type": "remote-docker",
  "host": "user@gpu-server",
  "container_id": "abc123def456",
  "work_dir": "/workspace",
  "gpu_count": 4,
  "status": "ready"
}
```

## 执行命令

```bash
ssh <host> "docker exec <container_id> bash -c '<command>'"
```

多行命令：

```bash
ssh <host> "docker exec <container_id> bash -c 'cd <work_dir> && <command>'"
```

## Artifact 收集

优先使用 `docker cp`，再 rsync：

```bash
# docker cp → 本地
ssh <host> "docker cp <container_id>:<remote_path> /tmp/artifacts/"
rsync -az <host>:/tmp/artifacts/ <local_output_dir>/

# 或直接 rsync（需容器内路径挂载到宿主机）
rsync -az <host>:<work_dir>/outputs/ <local_output_dir>/
```

## 容器生命周期

Environment 模块负责启动容器并写入 `container_id`，执行模块不负责启停。

容器中断时（`docker exec` 报错）：

```bash
ssh <host> "docker restart <container_id>"
# 成功后重跑当前 run；失败则 blocked: exec_error
```
