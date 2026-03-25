phase: EXECUTING
updated_at: 2026-03-25T14:20:00Z
retry_count: 0
current_claim_id: 1

claims:
  - id: 1
    desc: 两层 MLP 在随机生成的二分类数据上能正常训练 100 steps，train_loss 持续下降，accuracy 高于随机水平
    status: PENDING
    criteria: 100 steps 完成无报错；最终 train_loss < 初始 loss；最终 accuracy > 55%；全程每 step 均记录 train_loss 和 accuracy

next: 设计实验代码（两层 MLP 二分类），写入 /root/ 目录，准备在 AutoDL tmux 中执行
