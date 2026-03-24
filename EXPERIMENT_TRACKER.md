phase: EXECUTING
updated_at: 2026-03-25T01:30:00+08:00
retry_count: 0
current_claim_id: 1

claims:
  - id: 1
    desc: Qwen3-4B 在 SST-2 数据集上做情感分类微调，记录 eval_accuracy 和 eval_loss
    status: PENDING
    criteria: 完成完整训练+评测 pipeline，得到 eval_accuracy（数值）和 eval_loss（数值），无报错退出
    result:

next: 创建环境：连接 sc100123@174.0.250.88，验证 Slurm + conda 环境，写 env_handle.json
