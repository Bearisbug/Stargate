phase: EXECUTING
updated_at: 2026-03-25T14:30:00Z
retry_count: 0
current_claim_id: 1

claims:
  - id: 1
    desc: 在 AutoDL 服务器上用 PyTorch 训练两层 MLP 对随机生成的二分类数据做分类，跑 100 steps，train_loss 持续下降，最终 accuracy > 50%
    status: PENDING
    criteria: 训练 100 步无报错完成；每 step 均有 train_loss 和 accuracy 记录；最终 accuracy > 50%
    result:

next: 上传 train_mlp.py 到 /root/，在 tmux 中执行 100 steps 训练，收集结果 JSON
