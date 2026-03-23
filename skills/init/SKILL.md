---
name: init
description: 项目初始化入口。所有层（实验层、调研层、论文层）首次使用前运行，写入 project.json，配置 Langfuse tracing。
---

# 项目初始化

## 入口

**检查 `project.json` 是否已存在。**

- 已存在且字段完整 → 展示当前配置，询问是否需要更新某个字段，不重新收集
- 已存在但字段缺失 → 只补缺失字段
- 不存在 → 完整收集，见下方

---

## Step 1：收集基础信息

依次询问以下字段，已有默认值的可直接确认跳过：

| 字段 | 说明 | 是否必填 |
|------|------|:------:|
| `project_name` | 项目名，用于报告标题和 tracing session | ✅ |
| `servers.default` | 主服务器地址，`user@host` 格式；本地实验填 `local` | ✅ |
| `work_dir` | 远端实验根目录，绝对路径 | ✅ |
| `model_base_dir` | 预训练模型根路径 | — |
| `data_base_dir` | 数据集根路径 | — |

可选字段不填时写 `null`，后续用到时再补，不打断当前初始化。

---

## Step 2：实验层配置（实验层使用时收集）

若用户计划使用实验层（`experiment` skill），额外询问：

| 字段 | 说明 |
|------|------|
| GPU 平台类型 | Slurm / AutoDL / 云主机 / 实验室服务器 / 本地，用于 ENVIRONMENT 阶段预判 |
| 预计使用的执行环境 | Conda / Docker / Singularity |
| 是否离线环境 | 影响模型/数据拉取策略 |

这些信息写入 `project.json` 的 `experiment` 字段，供 `experiment` skill 的 ENVIRONMENT 阶段参考，避免重复询问。

---

## Step 3：Langfuse tracing（可选）

询问是否启用 tracing：

- **不需要** → `langfuse.enabled: false`，跳过
- **使用 Langfuse Cloud** → 引导用户到 cloud.langfuse.com 注册，获取 public key 和 secret key
- **自部署** → 询问 host 地址和 key

配置完成后运行验证：

```bash
python tools/trace.py init
```

输出 `[ok] Langfuse connected` 则写入 `project.json`，置 `langfuse.enabled: true`。
连接失败则保留配置但置 `enabled: false`，提示用户检查 key 和网络。

---

## Step 4：写入 project.json

```json
{
  "project_name": "<填写>",
  "servers": {
    "default": "user@host"
  },
  "work_dir": "/workspace",
  "model_base_dir": null,
  "data_base_dir": null,
  "experiment": {
    "platform": "<slurm | autodl | cloud | lab | local>",
    "runtime": "<conda | docker | singularity>",
    "offline": false
  },
  "langfuse": {
    "enabled": false,
    "host": "https://cloud.langfuse.com",
    "public_key": "",
    "secret_key": ""
  }
}
```

写入后告知用户初始化完成，可以开始使用对应层的 skill。

---

## 后续自动更新时机

| 时机 | 更新内容 |
|------|---------|
| ENVIRONMENT 阶段完成 | 补全 `servers.default` 的探测结果（GPU 型号、分区等）|
| 镜像拉取成功 | 更新 `image_registry` 为实际地址 |
| Langfuse 首次连接成功 | 将 `langfuse.enabled` 置为 `true` |
