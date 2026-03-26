# 实验报告

**实验 ID**：20260325_140849_AutoDL_____root_region_42_seetacloud_c
**生成时间**：2026-03-25
**状态**：DONE

---

## 实验目标

在 AutoDL 服务器（root@region-42.seetacloud.com:54297）上使用 PyTorch 训练一个两层 MLP，对随机生成的二分类数据进行分类，跑 100 steps，记录 train_loss 和 accuracy。

---

## Claims 汇总

| Claim | 描述 | 状态 |
|-------|------|------|
| Claim 1 | 两层 MLP 在随机生成的二分类数据上能正常训练 100 steps，train_loss 持续下降，accuracy 高于随机水平 | ANSWERED ✅ |

---

## Claim 1 详情

### 成功标准

- 100 steps 完成无报错
- 最终 train_loss < 初始 loss
- 最终 accuracy > 55%
- 全程每 step 均记录 train_loss 和 accuracy

### 实验结果

| 指标 | 值 |
|------|-----|
| 训练步数 | 100 |
| 初始 loss | 0.6771 |
| 最终 loss | 0.2378 |
| Loss 降幅 | 64.9% |
| 最终 accuracy | 95.31% |
| 记录完整性 | 100/100 步 |
| GPU | NVIDIA H20（CUDA） |
| 运行时间 | 0.29 秒 |

### 标准评估

| 标准 | 通过 |
|------|------|
| 100 steps 完成无报错 | ✅ |
| final_loss < initial_loss | ✅ |
| final_accuracy > 55% | ✅ |
| 全程每 step 均记录 | ✅ |
| **pass_all** | **✅** |

**结论**：Claim 1 完全成立。两层 MLP 在随机二分类数据上训练收敛良好，loss 降幅 64.9%，accuracy 达 95.31%，远超预期阈值。

---

## 运行记录

| 字段 | 值 |
|------|----|
| Run ID | nohup_2677 |
| Job ID | nohup/2677 |
| Git Hash | 5be917475f1d5bb391213db3377b1be0cc6654df |
| 服务器 | root@region-42.seetacloud.com:54297 |
| 提交时间 | 2026-03-25T14:45:00Z |
| 分析时间 | 2026-03-25T15:00:00Z |

---

## 关键发现

1. **环境验证通过**：AutoDL H20 GPU 环境正常，PyTorch CUDA 可用，0.29 秒内完成 100 steps 训练，无任何报错。

2. **模型收敛迅速**：两层 MLP 在随机生成的线性可分二分类数据上表现出色，loss 在 100 steps 内从 0.6771 降至 0.2378，accuracy 从随机水平提升至 95.31%。

3. **可复现性**：实验结果通过 Git 追踪（hash: 5be9174），可复现。

---

## 结论

实验目标已全部达成。AutoDL 服务器 GPU 环境已验证可用，两层 MLP baseline 建立完成，为后续更复杂实验提供了稳定的基础。

---

*报告由 Stargate 实验层自动生成*
