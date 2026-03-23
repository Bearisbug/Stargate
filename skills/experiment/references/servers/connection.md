# 持久化连接管理

> 参考：[tmux Getting Started](https://github.com/tmux/tmux/wiki/Getting-Started)

## 为什么需要 tmux

SSH 连接中断会终止所有前台进程。tmux 让进程在服务器端独立运行，断线后可重新 attach 恢复。

## 本地：SSH 保活配置

在 `~/.ssh/config` 中加入：

```
Host *
  ServerAliveInterval 60
  ServerAliveCountMax 3
```

## 远端：tmux 会话管理

```bash
# 创建命名会话
tmux new -s <session-name>

# 分离（不中断进程）
Ctrl+B, D

# 断线后重连，恢复会话
tmux attach -t <session-name>

# 查看所有会话
tmux ls

# 删除会话
tmux kill-session -t <session-name>
```

**常用快捷键**：

| 按键 | 功能 |
|------|------|
| `Ctrl+B, D` | 分离当前 session |
| `Ctrl+B, s` | 列出并切换 session |
| `Ctrl+B, $` | 重命名当前 session |
| `Ctrl+B, c` | 新建 window |
| `Ctrl+B, n/p` | 切换下/上一个 window |

## 约定

- 每个实验使用固定会话名（如项目名），重连时优先 `attach`，不重复创建
- Slurm job 由调度系统管理，提交后不依赖 tmux 存活，可直接断开连接
- tmux 在 Slurm 环境下主要用于提交前的交互和查看日志
