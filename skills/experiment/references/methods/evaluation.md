# 评估（Evaluation）工具规范

## 默认工具

**按评估类型选工具**：

| 评估类型 | 默认工具 |
|---------|---------|
| 标准 LLM benchmark | lm-evaluation-harness |
| 国内常用 benchmark | OpenCompass |
| LLM-as-judge | 用 vLLM 托管评估模型，自定义脚本调用 |
| 领域专有指标 | 自定义脚本（参考 `references/code.md` 规范） |

## 替代条件

| 替代工具 | 何时使用 | 必须说明原因 |
|---------|---------|------------|
| HELM | 需要多维度综合评估报告 | ✅ |
| Evalplus | 代码生成评估（HumanEval+、MBPP+） | ✅ |
| 人工评估 | 自动指标与人类判断相关性低的任务 | ✅ |

## 禁止用法

- **不能用训练集或其子集做评估**：数据泄露会使结果无意义
- **不能在不固定 generation 参数的情况下对比不同模型**：temperature、top_p 必须一致
- **不能只报单一指标**：至少报主指标 + 置信区间或标准差
- **不能跳过评估脚本的 reproducibility 验证**：相同模型跑两次结果应一致
