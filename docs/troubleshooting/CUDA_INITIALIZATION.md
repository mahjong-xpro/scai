# CUDA 初始化问题排查指南

## 问题描述

即使 `nvidia-smi` 显示有 GPU，PyTorch 仍然检测不到 CUDA，报错：
```
Error 101: invalid device ordinal
CUDA available: False, GPU count: 0
```

## 可能的原因

1. **CUDA_VISIBLE_DEVICES 环境变量被设置为无效值**
   - 之前运行训练时设置了不存在的 GPU ID（如 `[0,1,2,3]` 但系统只有 1 张 GPU）
   - 环境变量仍然存在于当前 shell 会话中

2. **PyTorch CUDA 版本与系统 CUDA 驱动不匹配**
   - PyTorch 编译时使用的 CUDA 版本与系统 CUDA 驱动版本不兼容
   - 例如：PyTorch CUDA 12.8 vs 系统 CUDA 12.6

3. **PyTorch CUDA 上下文被污染**
   - 如果之前运行过训练并遇到错误，PyTorch 的 CUDA 上下文可能已被污染
   - 即使清除了环境变量，错误状态可能仍然保留

## 诊断步骤

### 1. 检查环境变量

```bash
# 检查当前环境变量
echo $CUDA_VISIBLE_DEVICES

# 如果设置了，清除它
unset CUDA_VISIBLE_DEVICES
```

### 2. 运行诊断脚本

```bash
cd /data/scai/python
python check_cuda.py
```

### 3. 测试清除环境变量后的效果

```bash
# 在新的 shell 中（确保环境变量已清除）
unset CUDA_VISIBLE_DEVICES
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPUs: {torch.cuda.device_count()}')"
```

### 4. 检查版本兼容性

```bash
# PyTorch CUDA 版本
python -c "import torch; print(torch.version.cuda)"

# 系统 CUDA 版本
nvcc --version
```

## 解决方案

### 方案 1: 清除环境变量并重启 Python 进程（推荐）

```bash
# 1. 完全退出当前 Python 进程（如果正在运行训练）
# 2. 清除环境变量
unset CUDA_VISIBLE_DEVICES

# 3. 在新的 shell 中运行训练
python train.py --config config.yaml
```

### 方案 2: 重新安装匹配的 PyTorch 版本

如果版本不匹配，重新安装：

```bash
# 对于 CUDA 12.6
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# 或者对于 CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 方案 3: 暂时使用 CPU（快速解决方案）

在 `config.yaml` 中禁用 GPU：

```yaml
gpu:
  enabled: false  # 使用 CPU
```

### 方案 4: 使用修复脚本

```bash
cd /data/scai/python
python fix_cuda_env.py
```

## 预防措施

1. **在配置文件中使用有效的 GPU ID**
   - 先检查系统实际可用的 GPU 数量
   - 只使用存在的 GPU ID

2. **使用自动检测**
   - 在 `config.yaml` 中不设置 `device_ids`，让系统自动检测所有 GPU

3. **在训练脚本中处理错误**
   - 训练脚本已经改进了 GPU 检测逻辑
   - 会自动过滤无效的 GPU ID 并回退到 CPU

## 验证修复

修复后，运行以下命令验证：

```bash
# 清除环境变量
unset CUDA_VISIBLE_DEVICES

# 测试 PyTorch CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')"
```

如果仍然失败，检查：
- PyTorch 是否是用 CUDA 支持编译的（不是 CPU-only 版本）
- CUDA 驱动是否正确安装
- PyTorch CUDA 版本是否与系统 CUDA 兼容

## 常见问题

### Q: 为什么清除环境变量后仍然失败？

**A**: 如果 PyTorch 已经在当前 Python 进程中初始化过 CUDA，清除环境变量可能不够。需要：
1. 完全退出 Python 进程
2. 清除环境变量
3. 重新启动 Python

### Q: PyTorch CUDA 12.8 和系统 CUDA 12.6 兼容吗？

**A**: 通常向后兼容，但最好使用匹配的版本。如果遇到问题，建议重新安装匹配的版本。

### Q: 如何检查 PyTorch 是否支持 CUDA？

**A**: 
```bash
python -c "import torch; print(torch.cuda.is_available())"
# 如果返回 False，可能是 CPU-only 版本
```

