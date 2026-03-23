# AutoDL 连接指南

> 参考：[AutoDL 帮助文档 - SSH](https://www.autodl.com/docs/ssh/) | [文件存储](https://www.autodl.com/docs/fs/)

## 连接方式

AutoDL 控制台 → 实例详情 → 复制 SSH 登录命令：

```bash
ssh -p <port> root@<host>
# 示例：ssh -p 10309 root@connect.nmb1.seetacloud.com
```

- 用户名固定为 `root`
- 端口每个实例不同，从控制台复制
- 密码在控制台查看，或配置 SSH 公钥免密登录

## 免密登录配置

```bash
# 本地生成密钥（若未生成）
ssh-keygen -t rsa

# 将 ~/.ssh/id_rsa.pub 内容粘贴到 AutoDL 控制台 → 密钥登录
```

## 存储结构

| 路径 | 类型 | 说明 |
|------|------|------|
| `/root/` | 系统盘 | 环境和代码，实例保留，**容量较小** |
| `/root/autodl-tmp/` | 本地数据盘 | 高速 I/O，训练数据/模型首选，实例保留 |
| `/root/autodl-fs/` | 网络文件存储 | 同区实例共享，200GB 默认容量，超 20GB/天 计费 |

**约定**：
- 数据集和模型权重 → `autodl-tmp/`
- 需跨实例共享的数据 → `autodl-fs/`
- 代码 → `/root/`

`autodl-fs` 有 200,000 inode 限制，小文件过多时即使有空间也会报"磁盘已满"。

## 文件传输

```bash
# 上传到实例
scp -P <port> local_file.py root@<host>:/root/

# 从实例下载
scp -P <port> root@<host>:/root/autodl-tmp/result.json ./
```

## 运行训练任务

AutoDL 不支持 Slurm，需在 tmux 中运行保证 SSH 断线后任务不中断：

```bash
tmux new -s train
python train.py
# Ctrl+B, D 分离，之后可安全断开 SSH
```

→ tmux 详细用法见 `references/servers/connection.md`

## 注意

- 实例**关机不计费**，训练完成后及时关机
- 系统盘空间小，避免在 `/root/` 存大文件
