# 如何停止训练

## 正常停止（推荐）

按 `Ctrl+C` 一次，训练脚本会：
1. 保存当前 checkpoint
2. 优雅关闭 Ray workers
3. 退出

**注意**：如果按一次 `Ctrl+C` 没有响应，等待几秒钟，不要连续按多次。

## 强制停止

如果正常停止不起作用，使用以下方法：

### 方法 1: 停止 Ray 然后终止进程

```bash
# 停止 Ray
ray stop --force

# 查找并终止训练进程
pkill -f "train.py"
pkill -f "python.*scai"
```

### 方法 2: 使用 kill 命令

```bash
# 查找训练进程的 PID
ps aux | grep train.py

# 终止进程（替换 <PID> 为实际进程 ID）
kill -9 <PID>

# 或者强制终止所有相关进程
pkill -9 -f "train.py|ray|python.*scai"
```

### 方法 3: 停止所有 Ray 相关进程

```bash
# 停止 Ray 集群
ray stop --force

# 清理所有 Ray 进程
pkill -9 ray
pkill -9 raylet
pkill -9 plasma
```

## 检查进程是否已停止

```bash
# 检查训练进程
ps aux | grep train.py

# 检查 Ray 进程
ps aux | grep ray

# 检查 Python 进程
ps aux | grep python
```

## 清理资源

停止训练后，可能需要清理：

```bash
# 停止 Ray（如果还在运行）
ray stop --force

# 清理临时文件（可选）
rm -rf /tmp/ray-*
```

## 常见问题

### Q: 按 Ctrl+C 后进程还在运行？

**A**: 可能是 Ray workers 没有响应信号。尝试：
1. 等待 10-15 秒，让主进程尝试关闭 Ray
2. 如果还是不行，使用强制停止方法

### Q: 训练卡住无法停止？

**A**: 可能是 Ray workers 卡死。使用强制停止：
```bash
ray stop --force
pkill -9 -f train.py
```

### Q: 停止后 Ray 还在运行？

**A**: 手动停止 Ray：
```bash
ray stop --force
```

## 预防措施

为了避免无法停止的问题：

1. **减少 Worker 数量**：在 `config.yaml` 中设置较少的 workers
   ```yaml
   selfplay:
     num_workers: 10  # 而不是 100
   ```

2. **定期保存 Checkpoint**：设置较短的保存间隔
   ```yaml
   training:
     save_interval: 10  # 每 10 次迭代保存一次
   ```

3. **监控资源使用**：确保有足够的内存和 CPU，避免系统卡死

