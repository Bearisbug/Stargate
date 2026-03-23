# Slurm 集群操作指南

## Job Script 结构

```bash
#!/bin/bash
#SBATCH --job-name=<名称>
#SBATCH -p <partition>
#SBATCH --nodes=1
#SBATCH --gres=gpu:<数量>          # GPU 请求，可加类型：gpu:a100:1
#SBATCH --cpus-per-task=<数量>
#SBATCH --mem=<大小>G
#SBATCH --time=<HH:MM:SS>
#SBATCH --output=/absolute/path/logs/%j.out   # 必须绝对路径
#SBATCH --error=/absolute/path/logs/%j.err    # 必须绝对路径

# 环境初始化
module load <module>
source <conda_init_script>
conda activate <env>

# 任务
cd /absolute/path/work_dir
python train.py
```

**重要限制**：`#SBATCH` 行不展开 shell 变量和 `~`，路径必须写绝对路径。变量只能在 `#SBATCH` 区块结束后使用。

---

## 常用命令

### 提交
```bash
sbatch job.sh                        # 提交，返回 job id
sbatch --dependency=afterok:<id> job.sh  # 依赖另一个 job 完成后运行
```

### 监控
```bash
squeue -u <user>                     # 查看自己的 job
squeue -j <job_id>                   # 查看指定 job
sinfo -p <partition>                 # 查看 partition 状态和空闲节点
```

`squeue` 状态码：

| 状态 | 含义 |
|------|------|
| PD | Pending，等待资源 |
| R  | Running |
| CG | Completing |
| F  | Failed |
| CA | Cancelled |

### 取消
```bash
scancel <job_id>                     # 取消单个 job
scancel -u <user>                    # 取消自己所有 job
```

### 查看详情
```bash
scontrol show job <job_id>           # 完整 job 信息（节点、路径、状态）
```

---

## 提交前检查清单

- [ ] 输出目录已存在（Slurm 不会自动创建）
- [ ] 所有路径为绝对路径
- [ ] `module load` 和 `conda activate` 顺序正确
- [ ] `set -e` 已加（任意步骤失败即终止）
- [ ] 没有同名 job 已在运行

---

## 诊断失败

job 失败时按顺序检查：

```bash
# 1. 看退出状态和节点
scontrol show job <job_id> | grep -E "JobState|ExitCode|NodeList"

# 2. 看 stderr（通常有 Python traceback 或缺库报错）
tail -50 logs/<job_id>.err

# 3. 看 stdout（确认运行到哪一步）
tail -50 logs/<job_id>.out
```

常见原因：

| 现象 | 可能原因 |
|------|---------|
| 48s 内失败 | 缺少动态库（`libcudnn`、`libcuda` 等），检查 `module load` |
| OOM killed | 内存不足，增加 `--mem` 或减小 batch size |
| Timeout | 超过 `--time` 限制，增加时限或拆分任务 |
| 找不到文件 | 路径错误或未 `cd` 到正确目录 |
| 立即 FAILED，无输出 | job script 本身语法错误，本地 `bash -n job.sh` 检查 |
