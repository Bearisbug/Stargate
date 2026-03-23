# 数据处理工具规范

## 默认工具

**按数据规模选工具**：

| 数据规模 | 默认工具 |
|---------|---------|
| < 1GB | pandas |
| 1GB – 100GB | polars（比 pandas 快 5-50x，内存占用低） |
| LLM 训练数据清洗 | Data-Juicer |
| > 100GB / 分布式 | Spark / Dask |

## 替代条件

| 替代工具 | 何时使用 | 必须说明原因 |
|---------|---------|------------|
| pandas | 数据 < 1GB，或需要与 pandas 生态（geopandas 等）集成 | ✅ |
| DuckDB | SQL 风格查询 JSONL/Parquet，单机大文件 | ✅ |
| HF Datasets | 与 HF 训练流程集成，需要 streaming 加载 | ✅ |

## 禁止用法

- **不能用 pandas 处理 > 10GB 数据**：会 OOM，改用 polars 或 DuckDB
- **不能在处理完数据后不做 sanity check**：至少检查样本数量、字段完整性、标签分布
- **不能把原始数据和处理后数据放同一目录**：原始数据只读，处理结果写新路径
