# 云厂商 GPU 主机连接指南

> 参考：[AWS EC2 SSH 连接](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-linux-inst-ssh.html) | [阿里云 ECS SSH 连接](https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-an-ssh-key-pair)

## 连接方式

### 密钥登录（推荐）

```bash
# 设置密钥权限（必须，否则 SSH 拒绝连接）
chmod 400 key-pair-name.pem

# 连接
ssh -i /path/key-pair-name.pem <user>@<public_ip>
```

### 各厂商默认用户名

| 厂商 / 镜像 | 默认用户名 |
|-------------|-----------|
| AWS Amazon Linux | `ec2-user` |
| AWS Ubuntu | `ubuntu` |
| AWS RHEL / CentOS | `ec2-user` 或 `root` |
| AWS Debian | `admin` |
| 阿里云 / 腾讯云 Linux | `root` 或 `ubuntu`（取决于镜像） |

## 安全组 / 防火墙

SSH 端口（默认 22）必须在安全组**入站规则**中放开，否则连接超时。
训练期间通常无需开放其他端口，TensorBoard 等通过 SSH 隧道访问：

```bash
ssh -i key.pem -L 6006:localhost:6006 <user>@<public_ip>
```

## 存储

| 类型 | 说明 |
|------|------|
| 系统盘 | 默认较小（40–100G），存代码和环境 |
| 数据盘 | 挂载后使用，存数据集和模型权重 |
| 对象存储 | S3 / OSS，大文件长期存储，需 CLI 工具 |

查看磁盘挂载情况：
```bash
df -h
lsblk
```

## 注意

- 按量计费实例**按运行时长收费**，训练完成后及时**关机**（停止，不是终止）
- `.pem` 文件权限必须为 `400`，否则 SSH 报 `WARNING: UNPROTECTED PRIVATE KEY FILE!`
- 实例公网 IP 在停止后可能变更，建议绑定弹性 IP（EIP）

## 无调度系统

云 GPU 主机通常没有 Slurm，直接在 tmux 中运行：

```bash
tmux new -s train
python train.py
# Ctrl+B, D 分离后可安全断开 SSH
```

→ tmux 详细用法见 `references/servers/connection.md`
