# 向量检索与 RAG 工具规范

## 默认工具

**按场景选工具**：

| 场景 | 默认工具 |
|------|---------|
| 实验/原型阶段向量检索 | FAISS |
| RAG pipeline 构建 | LlamaIndex |
| 生产级向量数据库 | Milvus / Qdrant |
| Embedding 模型 | BGE 系列（中文）/ E5 系列（英文）|

## 替代条件

| 替代工具 | 何时使用 | 必须说明原因 |
|---------|---------|------------|
| Chroma | 本地轻量原型，不需要持久化生产部署 | ✅ |
| LangChain | 已有 LangChain 生态集成，迁移成本高 | ✅ |
| BM25（sparse） | 关键词检索效果优于 dense，或 hybrid 检索 | ✅ |

## 禁止用法

- **不能在没有 retrieval 质量评估的情况下只评估生成质量**：RAG 失败多数在检索环节
- **不能用 LangChain 做实验性 RAG**：抽象层过多，debug 困难，实验用 LlamaIndex 或自定义
- **不能跳过 chunk size / overlap 的消融实验**：这两个参数对效果影响显著
