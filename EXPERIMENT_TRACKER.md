phase: WAITING
updated_at: 2026-03-25T11:30:00+08:00
retry_count: 1
current_claim_id: 1
job_id: 1267164
git_hash: 56557e9
submitted_at: 2026-03-25T11:30:00+08:00
expected_outputs:
  - /online1/sc100123/sc100123/sst2_baseline/runs/qwen3-4b-lora/eval_results.json
  - /online1/sc100123/sc100123/sst2_baseline/logs/1267164.out
  - /online1/sc100123/sc100123/sst2_baseline/logs/1267164.err

claims:
  - id: 1
    desc: Qwen3-4B 在 SST-2 数据集上做情感分类微调，记录 eval_accuracy 和 eval_loss
    status: PENDING
    criteria: 完成完整训练+评测 pipeline，得到 eval_accuracy（数值）和 eval_loss（数值），无报错退出
    result:

next: 检查 job 1267164 状态；若完成则拉取 eval_results.json，进入 ANALYZING
