---
name: experiment-errors
description: 实验执行中的错误处理：环境错误、命令失败、结果异常。在实验遇到报错、blocked 或意外情况时使用。
---

# 实验错误处理

## 错误分类

| 类型 | 标记 | 可否自动修复 |
|------|------|:-----------:|
| env_handle.json 不存在 | `blocked: no_env_handle` | ❌ |
| 镜像不可用 | `blocked: image_unavailable` | ❌ |
| OOM | 重试（减半 batch_size） | ✅ 一次 |
| 缺少依赖 | 重试（安装依赖） | ✅ 一次 |
| 验收命令失败 | `failed` | ❌ |
| 其他命令报错 | `blocked: exec_error` | ❌ |
| 容器/连接中断 | 重启/重连一次 | ✅ 一次 |
| 计算节点无网络（数据/依赖下载失败） | 自动修复（见下方） | ✅ 一次 |

## 自动修复规则

只尝试一次，失败立即 blocked，不循环。

**OOM：**
```bash
# 将 --batch-size N 替换为 --batch-size N/2，重新执行
```

**缺少依赖：**
```bash
# docker
docker exec <container_id> pip install <package>
# ssh / local
pip install <package>
```

**容器中断：**
```bash
docker restart <container_id>   # 成功则重跑当前 run
```

**计算节点无网络（URLError / ConnectionRefused 下载数据集或依赖）：**

HPC 集群计算节点通常无公网访问，`download=True` 或 `pip install` 在 job 内必然失败。自动修复流程：

1. 检查登录节点是否有网络：`ssh <login_node> "curl -s --connect-timeout 5 https://pypi.org -o /dev/null -w '%{http_code}'"`
2. 登录节点有网 → 在登录节点内（容器外或容器内）提前下载，再重跑 job
3. 登录节点也无网 → 检查本地（Claude Code 所在机器）是否有网，有则本地下载后 scp 上传
4. 均无网 → `blocked: no_internet`，提示用户手动准备数据

数据集下载后，将训练脚本中的 `download=True` 改为 `download=False` 再提交。

## blocked vs failed

- `failed`：run 跑完了，但结果不达标（metric 没过 threshold）
- `blocked`：无法继续执行，需要人工介入

blocked 时输出明确的原因和解决方案，不要静默停止。
