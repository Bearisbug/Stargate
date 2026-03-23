# 学校 / 实验室服务器连接指南

> 参考：[nvidia-smi 官方文档](https://docs.nvidia.com/deploy/nvidia-smi/index.html)

## 连接

```bash
ssh <user>@<host>
# 非默认端口
ssh -p <port> <user>@<host>
```

## GPU 状态查看

```bash
# 查看所有 GPU 状态（显存占用、温度、功耗）
nvidia-smi

# 每秒刷新
nvidia-smi -l 1

# 查看正在使用 GPU 的进程
nvidia-smi pmon

# 自定义格式查询
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv
```

## 多人共用时的 GPU 协调

实验室服务器通常无调度系统，需手动协调：

```bash
# 查看当前 GPU 占用
nvidia-smi

# 查看哪些进程在用 GPU（按 GPU 编号）
nvidia-smi pmon -d 1

# 指定使用某块空闲 GPU
CUDA_VISIBLE_DEVICES=0 python train.py

# 指定多卡
CUDA_VISIBLE_DEVICES=0,1 python train.py
```

**约定**：使用前先 `nvidia-smi` 确认空闲，不抢占他人正在使用的 GPU。

## 运行训练任务

用 tmux 保持进程，防止 SSH 断线后任务中止：

```bash
tmux new -s <session-name>
CUDA_VISIBLE_DEVICES=<id> python train.py
# Ctrl+B, D 分离后可断开 SSH
```

→ tmux 详细用法见 `references/servers/connection.md`

## 存储约定

- 数据集放共享目录（询问管理员路径）
- 个人实验放 `/home/<user>/` 或指定目录
- 避免在根目录或系统盘存放大文件，先用 `df -h` 确认磁盘空间
