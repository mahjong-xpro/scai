# SSH隧道脚本使用指南

## 概述

这些脚本用于通过SSH隧道访问运行在远程服务器上的训练仪表板（Dashboard）。

训练仪表板默认运行在服务器的 `5000` 端口，通过SSH隧道可以将远程端口映射到本地，从而在本地浏览器中访问。

## 脚本说明

### 1. Python脚本 (`ssh_tunnel_dashboard.py`)

**优点**：
- 跨平台（Windows、macOS、Linux）
- 功能丰富（自动打开浏览器、更好的错误处理）
- 支持更多选项

**使用方法**：

```bash
# 基本用法
python scripts/ssh_tunnel_dashboard.py --host <服务器地址> --user <用户名>

# 完整示例
python scripts/ssh_tunnel_dashboard.py \
    --host 192.168.1.100 \
    --user root \
    --ssh-port 22 \
    --remote-port 5000 \
    --local-port 5000 \
    --key ~/.ssh/id_rsa \
    --open-browser
```

**参数说明**：
- `--host`: 远程服务器地址（IP或域名）**必需**
- `--user`: SSH用户名 **必需**
- `--ssh-port`: SSH端口（默认: 22）
- `--remote-port`: 远程服务器端口（默认: 5000，训练仪表板端口）
- `--local-port`: 本地端口（默认: 5000）
- `--key`: SSH私钥文件路径（可选，默认使用 ~/.ssh/id_rsa）
- `--open-browser`: 自动在浏览器中打开仪表板

### 2. Shell脚本 (`ssh_tunnel_dashboard.sh`)

**优点**：
- 简单直接
- 无需Python依赖
- 适合Linux/macOS

**使用方法**：

```bash
# 添加执行权限
chmod +x scripts/ssh_tunnel_dashboard.sh

# 基本用法
./scripts/ssh_tunnel_dashboard.sh <服务器地址> <用户名>

# 完整示例
./scripts/ssh_tunnel_dashboard.sh 192.168.1.100 root 22 5000 5000
```

**参数说明**：
1. 服务器地址（必需）
2. 用户名（必需）
3. SSH端口（可选，默认: 22）
4. 本地端口（可选，默认: 5000）
5. 远程端口（可选，默认: 5000）

## 使用示例

### 示例1：基本连接

```bash
# Python脚本
python scripts/ssh_tunnel_dashboard.py --host 192.168.1.100 --user root

# Shell脚本
./scripts/ssh_tunnel_dashboard.sh 192.168.1.100 root
```

访问：`http://localhost:5000`

### 示例2：使用自定义端口

```bash
# Python脚本
python scripts/ssh_tunnel_dashboard.py \
    --host example.com \
    --user ubuntu \
    --ssh-port 2222 \
    --local-port 8080

# Shell脚本
./scripts/ssh_tunnel_dashboard.sh example.com ubuntu 2222 8080 5000
```

访问：`http://localhost:8080`

### 示例3：使用SSH密钥

```bash
# Python脚本
python scripts/ssh_tunnel_dashboard.py \
    --host example.com \
    --user ubuntu \
    --key ~/.ssh/my_key \
    --open-browser

# Shell脚本（需要在SSH配置中设置，或使用ssh-agent）
./scripts/ssh_tunnel_dashboard.sh example.com ubuntu
```

### 示例4：自动打开浏览器

```bash
# Python脚本
python scripts/ssh_tunnel_dashboard.py \
    --host 192.168.1.100 \
    --user root \
    --open-browser
```

## 常见问题

### Q1: 连接失败，提示 "Connection refused"

**可能原因**：
1. 远程服务器未运行训练脚本
2. 训练仪表板未启用（`curriculum_learning.dashboard.enabled: false`）
3. 防火墙阻止了5000端口

**解决方法**：
1. 检查远程服务器上训练脚本是否运行
2. 检查 `config.yaml` 中的 `curriculum_learning.dashboard.enabled` 是否为 `true`
3. 检查防火墙设置，确保5000端口可访问

### Q2: 本地端口已被占用

**解决方法**：
- 使用不同的本地端口：
  ```bash
  python scripts/ssh_tunnel_dashboard.py --host <host> --user <user> --local-port 8080
  ```

### Q3: SSH连接需要密码

**解决方法**：
1. 使用SSH密钥（推荐）：
   ```bash
   python scripts/ssh_tunnel_dashboard.py --host <host> --user <user> --key ~/.ssh/id_rsa
   ```

2. 或使用 `ssh-agent`：
   ```bash
   ssh-add ~/.ssh/id_rsa
   python scripts/ssh_tunnel_dashboard.py --host <host> --user <user>
   ```

### Q4: 连接不稳定，经常断开

**解决方法**：
- 脚本已包含保活机制（`ServerAliveInterval=60`）
- 如果仍然断开，可以增加保活频率（需要修改脚本）

### Q5: 无法自动打开浏览器

**解决方法**：
- 手动访问：`http://localhost:5000`
- 或使用 `--no-browser` 参数禁用自动打开

## 安全注意事项

1. **SSH密钥安全**：
   - 不要将SSH私钥文件提交到版本控制
   - 使用强密码保护私钥文件
   - 定期轮换SSH密钥

2. **端口转发安全**：
   - SSH隧道是加密的，数据传输安全
   - 但确保远程服务器的仪表板只监听 `localhost`（默认配置）

3. **防火墙**：
   - 确保远程服务器的防火墙允许SSH连接
   - 仪表板端口（5000）不需要对外开放，只需SSH隧道即可

## 停止隧道

- **Python脚本**：按 `Ctrl+C`
- **Shell脚本**：按 `Ctrl+C`

脚本会自动清理SSH进程。

## 高级用法

### 后台运行（Python脚本）

```bash
# 使用 nohup
nohup python scripts/ssh_tunnel_dashboard.py --host <host> --user <user> > tunnel.log 2>&1 &

# 查看进程
ps aux | grep ssh_tunnel_dashboard

# 停止进程
pkill -f ssh_tunnel_dashboard
```

### 使用SSH配置文件

在 `~/.ssh/config` 中添加：

```
Host training-server
    HostName 192.168.1.100
    User root
    Port 22
    IdentityFile ~/.ssh/id_rsa
```

然后使用：

```bash
python scripts/ssh_tunnel_dashboard.py --host training-server --user root
```

## 相关文档

- [训练配置指南](../docs/troubleshooting/CONFIG_4X4090_GUIDE.md)
- [课程学习文档](../python/scai/coach/README.md)

