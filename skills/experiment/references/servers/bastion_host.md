# 堡垒机 / 跳板机连接指南

> 参考：[ssh_config(5) - Linux man page](https://man7.org/linux/man-pages/man5/ssh_config.5.html)

## ProxyJump 方式（推荐）

### ~/.ssh/config 配置

```
Host bastion
  HostName <堡垒机 IP>
  User <user>
  IdentityFile ~/.ssh/id_rsa

Host target
  HostName <目标服务器内网 IP>
  User <user>
  ProxyJump bastion
```

配置后直接连接：
```bash
ssh target
scp file.py target:/path/
rsync -avz ./code/ target:/path/code/
```

### 命令行方式（无需修改 config）

```bash
ssh -J <user>@<bastion_ip> <user>@<target_ip>

# 多级跳板（逗号分隔，按顺序访问）
ssh -J <user>@<bastion1>,<user>@<bastion2> <user>@<target_ip>
```

## 注意事项

- `ProxyJump` 和 `ProxyCommand` 互斥，同时指定时先出现的生效
- `~/.ssh/config` 中对目标主机的配置**不会**自动应用到跳板机，跳板机需单独配置
- 部分堡垒机系统不支持 `ProxyJump`（较老版本的 SSH），需改用 `ProxyCommand`：
  ```
  ProxyCommand ssh -W %h:%p <user>@<bastion_ip>
  ```
- 堡垒机通常有登录审计，操作会被记录

## SCP / rsync 通过跳板机

```bash
# SCP
scp -J <user>@<bastion> file.py <user>@<target>:/path/

# rsync
rsync -avz -e "ssh -J <user>@<bastion>" ./code/ <user>@<target>:/path/code/
```
