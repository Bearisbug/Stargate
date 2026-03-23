# Conda 环境管理

> 参考：[conda 官方文档 - Managing environments](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html)

## 环境管理

```bash
# 创建环境（指定 Python 版本）
conda create -n <env> python=3.10

# 从 environment.yml 创建
conda env create -f environment.yml

# 激活 / 取消激活
conda activate <env>
conda deactivate

# 列出所有环境
conda env list

# 删除环境
conda remove --name <env> --all
```

**最佳实践**：一次性安装所有依赖，避免分次安装导致依赖冲突：
```bash
conda create -n <env> python=3.10 pytorch torchvision cudatoolkit=11.8 -c pytorch
```

## 包管理

```bash
# conda 安装
conda install -n <env> <package>

# pip 安装（激活环境后）
conda activate <env>
pip install <package>

# 查看环境内已安装的包
conda list -n <env>

# 查看变更历史
conda list --revisions
```

## 导出 / 复现环境

```bash
# 导出（含精确版本，跨平台可能有问题）
conda env export > environment.yml

# 导出（仅显式安装的包，跨平台兼容性更好）
conda env export --from-history > environment.yml

# 复现
conda env create -f environment.yml
```

## 集群上的 Conda 初始化

部分集群没有默认初始化 conda，需手动 source：

```bash
source /path/to/miniconda3/etc/profile.d/conda.sh
conda activate <env>
```

将此路径记录到 `env_handle.json` 的 `activate_cmd` 字段，后续 job script 统一使用。
