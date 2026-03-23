# 长时间任务监控

适用于：Slurm job、远程训练、预计超过 context 窗口时长的任务。

## 轮询策略

提交任务后记录任务 ID，定期检查状态：

```bash
# Slurm
squeue -j <job_id>          # 检查是否还在队列
tail -f <job_id>.out        # 查看输出

# screen / tmux（远程）
screen -ls                  # 列出会话
screen -r <session>         # 接入查看

# 本地后台
ps aux | grep <script_name>
```

轮询间隔：统一 5 分钟。

## 完成判断

任务结束后检查：
- exit code（Slurm：`sacct -j <job_id> --format=ExitCode`）
- 预期输出文件是否存在
- 然后走正常的 artifact 收集和验证流程
