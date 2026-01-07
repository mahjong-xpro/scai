# 5000端口无法访问问题排查

## 问题描述

无法访问训练仪表板（`http://localhost:5000`），可能的原因和解决方法。

## 快速检查

### 使用检查脚本

```bash
# 检查仪表板状态
python scripts/check_dashboard.py

# 同时检查配置
python scripts/check_dashboard.py --check-config
```

## 常见原因和解决方法

### 1. 训练脚本未运行

**检查方法**：
```bash
# 检查训练进程
ps aux | grep train.py

# 或
pgrep -f train.py
```

**解决方法**：
```bash
# 启动训练脚本
cd python
python train.py --config config.yaml
```

### 2. 仪表板未启用

**检查配置**：
```yaml
curriculum_learning:
  enabled: true                 # 必须启用
  dashboard:
    enabled: true               # 必须启用
    port: 5000
```

**解决方法**：
1. 检查 `config.yaml` 中的配置
2. 确保 `curriculum_learning.enabled: true`
3. 确保 `curriculum_learning.dashboard.enabled: true`
4. 重启训练脚本

### 3. 端口被占用

**检查方法**：
```bash
# Linux/macOS
lsof -i :5000

# 或
netstat -an | grep 5000

# 或使用检查脚本
python scripts/check_dashboard.py
```

**解决方法**：
```bash
# 方法1：停止占用端口的进程
kill -9 <PID>

# 方法2：使用其他端口
# 修改 config.yaml:
# curriculum_learning.dashboard.port: 5001
```

### 4. 防火墙阻止

**检查方法**：
```bash
# Linux (ufw)
sudo ufw status

# Linux (firewalld)
sudo firewall-cmd --list-all

# macOS
# 系统偏好设置 -> 安全性与隐私 -> 防火墙
```

**解决方法**：
```bash
# Linux (ufw)
sudo ufw allow 5000/tcp

# Linux (firewalld)
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload

# macOS
# 在系统偏好设置中允许Python或终端访问网络
```

### 5. 服务启动失败

**检查方法**：
```bash
# 查看训练日志
tail -f logs/training_*.log | grep -i dashboard

# 或查看所有日志
tail -100 logs/training_*.log
```

**常见错误**：
- `Address already in use`：端口被占用
- `Permission denied`：权限不足
- `ModuleNotFoundError`：缺少依赖

**解决方法**：
- 根据错误信息解决具体问题
- 检查依赖是否安装完整
- 检查端口权限

### 6. 远程服务器访问问题

**如果是在远程服务器上**：

**检查方法**：
```bash
# 在服务器上检查
python scripts/check_dashboard.py --host 0.0.0.0

# 检查监听地址
netstat -tlnp | grep 5000
```

**解决方法**：
1. **使用SSH隧道**（推荐）：
   ```bash
   # 使用提供的脚本
   python scripts/ssh_tunnel_dashboard.py --host <服务器地址> --user <用户名>
   ```

2. **修改监听地址**：
   ```yaml
   curriculum_learning:
     dashboard:
       host: 0.0.0.0  # 监听所有网络接口
       port: 5000
   ```

3. **配置防火墙**：
   ```bash
   # 允许5000端口
   sudo ufw allow 5000/tcp
   ```

## 诊断步骤

### 步骤1：检查训练脚本是否运行

```bash
ps aux | grep train.py
```

**如果没有运行**：
- 启动训练脚本

### 步骤2：检查配置文件

```bash
# 检查配置
grep -A 5 "dashboard:" python/config.yaml
```

**应该看到**：
```yaml
dashboard:
  enabled: true
  host: 0.0.0.0
  port: 5000
```

### 步骤3：检查端口状态

```bash
# 检查端口是否开放
python scripts/check_dashboard.py

# 或手动检查
lsof -i :5000
```

### 步骤4：检查日志

```bash
# 查看训练日志
tail -f logs/training_*.log

# 搜索dashboard相关日志
grep -i dashboard logs/training_*.log
```

**应该看到**：
```
Dashboard enabled, starting web server on 0.0.0.0:5000
```

### 步骤5：测试连接

```bash
# 本地测试
curl http://localhost:5000

# 或使用浏览器访问
# http://localhost:5000
```

## 使用检查脚本

### 基本用法

```bash
# 检查本地仪表板
python scripts/check_dashboard.py

# 检查远程服务器（如果配置了SSH）
python scripts/check_dashboard.py --host <服务器IP>

# 检查其他端口
python scripts/check_dashboard.py --port 5001

# 同时检查配置
python scripts/check_dashboard.py --check-config
```

### 脚本输出示例

**成功**：
```
============================================================
🔍 检查训练仪表板
============================================================

1️⃣  检查端口 5000 是否开放...
   ✅ 端口 5000 已开放

2️⃣  检查HTTP服务...
   ✅ HTTP服务正常（状态码: 200）
   📊 仪表板地址: http://localhost:5000

============================================================
✅ 仪表板运行正常！
============================================================

📊 访问地址: http://localhost:5000
```

**失败**：
```
============================================================
🔍 检查训练仪表板
============================================================

1️⃣  检查端口 5000 是否开放...
   ❌ 端口 5000 未开放或无法访问

可能的原因：
   1. 训练脚本未运行
   2. 仪表板未启用（curriculum_learning.dashboard.enabled: false）
   3. 防火墙阻止了端口
   4. 服务启动失败

💡 解决建议
============================================================
...
```

## 常见错误信息

### 错误1：`Address already in use`

**原因**：端口被其他进程占用

**解决**：
```bash
# 查找占用端口的进程
lsof -i :5000

# 停止进程
kill -9 <PID>

# 或使用其他端口
```

### 错误2：`ModuleNotFoundError: No module named 'flask'`

**原因**：缺少依赖

**解决**：
```bash
pip install flask
```

### 错误3：`Permission denied`

**原因**：权限不足（某些系统需要root权限绑定1024以下端口）

**解决**：
- 使用5000以上端口（推荐）
- 或使用sudo运行（不推荐）

### 错误4：连接被拒绝（远程服务器）

**原因**：防火墙或网络配置问题

**解决**：
- 使用SSH隧道（推荐）
- 配置防火墙规则
- 检查服务器网络配置

## 验证修复

修复后，验证步骤：

1. **检查端口**：
   ```bash
   python scripts/check_dashboard.py
   ```

2. **访问仪表板**：
   - 本地：`http://localhost:5000`
   - 远程：使用SSH隧道后访问 `http://localhost:5000`

3. **查看内容**：
   - 应该看到训练状态
   - 当前阶段信息
   - 奖励配置
   - 训练指标

## 预防措施

1. **配置检查**：
   - 启动训练前检查配置文件
   - 确保 `dashboard.enabled: true`

2. **端口管理**：
   - 使用5000以上端口（避免权限问题）
   - 检查端口是否被占用

3. **日志监控**：
   - 定期查看训练日志
   - 关注dashboard启动信息

4. **防火墙配置**：
   - 提前配置防火墙规则
   - 使用SSH隧道（更安全）

## 总结

5000端口无法访问的常见原因：

1. ✅ **训练脚本未运行** - 启动训练脚本
2. ✅ **仪表板未启用** - 检查配置文件
3. ✅ **端口被占用** - 停止占用进程或更换端口
4. ✅ **防火墙阻止** - 配置防火墙规则
5. ✅ **服务启动失败** - 查看日志，解决具体错误
6. ✅ **远程访问问题** - 使用SSH隧道

**推荐解决方案**：
- 使用 `scripts/check_dashboard.py` 快速诊断
- 使用 `scripts/ssh_tunnel_dashboard.py` 访问远程服务器
- 检查配置文件确保仪表板已启用

