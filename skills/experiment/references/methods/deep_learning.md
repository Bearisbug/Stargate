# 传统深度学习工具规范

## 默认工具

**按任务选框架**：

| 任务 | 默认工具 |
|------|---------|
| 图像分类 | PyTorch + timm |
| 目标检测 | Ultralytics（YOLO 系列）/ MMDetection |
| 语义/实例分割 | MMSegmentation / Detectron2 |
| 时序/表格 | PyTorch + sklearn |
| 图神经网络 | PyTorch Geometric / DGL |
| 自定义网络结构 | 纯 PyTorch |

## 替代条件

| 替代工具 | 何时使用 | 必须说明原因 |
|---------|---------|------------|
| JAX / Flax | 需要函数式变换（vmap、jit）或 TPU | ✅ |
| TensorFlow / Keras | 已有 TF 预训练权重，转换成本过高 | ✅ |
| scikit-learn | 小数据、传统 ML 基线对比 | ✅ |

## 禁止用法

- **不能从零手写常见网络结构**（ResNet、ViT 等）：用 timm 直接加载，避免实现 bug
- **不能在训练中途更改 batch size 而不调整学习率**：学习率需随 batch size 线性缩放
- **不能跳过 random seed 固定**：结果不可复现，无法对比实验
