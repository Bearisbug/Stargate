# env_handle.json 格式规范

ENVIRONMENT 阶段完成后写入，供后续所有阶段读取。记录环境能力，不记录业务逻辑。

## 完整格式

```json
{
  "status": "ready",
  "exec_type": "<slurm | docker | tmux | kubernetes>",
  "host": "<user@host>",
  "work_dir": "<远端绝对路径>",

  "slurm": {
    "partition": "<partition 名称>",
    "gpu_type": "<GPU 型号，如 H20 / A100>",
    "gpu_vram_gb": <显存 GB>,
    "gpu_count": <每 job 申请的卡数>,
    "gres": "<完整 gres 字符串，如 gpu:tesla:1>"
  },

  "docker": {
    "image": "<registry/image:tag>",
    "runtime": "nvidia",
    "shm_size": "<如 8g>"
  },

  "runtime": {
    "type": "<conda | pip | container>",
    "env_path": "<conda 环境绝对路径（可选）>",
    "activate_cmd": "<激活环境的完整命令>",
    "packages_verified": ["<已验证可用的关键包>"]
  },

  "offline": false,

  "notes": "<备注，如模块加载命令、已知限制等>"
}
```

## 字段说明

| 字段 | 必填 | 说明 |
|------|:----:|------|
| `status` | ✅ | 固定为 `"ready"`，表示环境已就绪 |
| `exec_type` | ✅ | 决定 EXECUTING 阶段使用哪种提交方式 |
| `host` | ✅ | `user@host` 格式，本地机器填 `"local"` |
| `work_dir` | ✅ | 远端工作目录，**必须绝对路径** |
| `slurm` | 条件 | `exec_type == "slurm"` 时必填 |
| `docker` | 条件 | `exec_type == "docker"` 时必填 |
| `runtime` | ✅ | 环境激活方式，job script 直接使用 `activate_cmd` |
| `offline` | — | 外网不可达时置 `true`，DESIGN 阶段切换到本地路径 |
| `notes` | — | 自由文本，记录特殊配置（如需要 `module load` 的命令）|

## 写入时机

- **ENVIRONMENT 阶段完成**：首次写入
- **环境有变化**（更换 conda 环境、迁移服务器等）：重新运行 ENVIRONMENT 阶段，覆盖写入
- 其他阶段**只读**，不修改此文件
