# CUDA 初始化问题排查指南

## 问题描述

即使 `nvidia-smi` 显示有 GPU，PyTorch 仍然检测不到 CUDA，报错：
```
Error 101: invalid device ordinal
CUDA available: False, GPU count: 0
```

## 可能的原因

1. **CUDA 驱动问题（最可能）** ⚠️
   - CUDA 驱动版本与 PyTorch 编译的 CUDA 版本不匹配
   - CUDA 驱动未正确安装或损坏
   - 驱动版本太旧，不支持 PyTorch 需要的 CUDA 版本
   - 例如：PyTorch CUDA 12.8 需要驱动 >= 535.xx，但系统驱动可能是 525.xx

2. **CUDA_VISIBLE_DEVICES 环境变量被设置为无效值**
   - 之前运行训练时设置了不存在的 GPU ID（如 `[0,1,2,3]` 但系统只有 1 张 GPU）
   - 环境变量仍然存在于当前 shell 会话中

3. **PyTorch CUDA 版本与系统 CUDA 工具包不匹配**
   - PyTorch 编译时使用的 CUDA 版本与系统 CUDA 工具包版本不兼容
   - 例如：PyTorch CUDA 12.8 vs 系统 CUDA 12.6

4. **PyTorch CUDA 上下文被污染**
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

### 4. 检查驱动和版本兼容性

```bash
# 检查 NVIDIA 驱动版本
nvidia-smi | grep "Driver Version"

# PyTorch CUDA 版本
python -c "import torch; print(torch.version.cuda)"

# 系统 CUDA 工具包版本
nvcc --version

# 检查 CUDA 运行时版本（驱动支持的最高 CUDA 版本）
nvidia-smi | grep "CUDA Version"
```

**重要：** 检查驱动版本是否满足 PyTorch 的要求：
- PyTorch CUDA 12.x 通常需要驱动 >= 535.xx
- PyTorch CUDA 11.x 通常需要驱动 >= 450.xx
- 如果驱动版本太低，即使 nvidia-smi 能显示 GPU，PyTorch 也可能无法使用

## 解决方案

### 方案 1: 完全重启 Python 进程（最重要）⚠️

**关键：** 如果 PyTorch 已经在当前进程中初始化过 CUDA 并遇到错误，仅仅清除环境变量是不够的。**必须完全退出 Python 进程**。

```bash
# 1. 完全退出当前 Python 进程（如果正在运行训练）
#    按 Ctrl+C 退出，或者 kill 进程
#    重要：不要只是清除环境变量，必须退出进程

# 2. 打开新的 shell/终端（确保是全新的进程）

# 3. 清除环境变量（在新 shell 中）
unset CUDA_VISIBLE_DEVICES

# 4. 验证环境变量已清除
echo $CUDA_VISIBLE_DEVICES  # 应该显示空或 "not set"

# 5. 在新的 shell 中运行训练
cd /data/scai/python
python train.py --config config.yaml
```

**为什么需要重启进程？**
- PyTorch 在导入时会初始化 CUDA 上下文
- 如果初始化时遇到错误（如无效的 CUDA_VISIBLE_DEVICES），错误状态会保留在进程中
- 即使后来清除了环境变量，PyTorch 的 CUDA 上下文仍然处于错误状态
- 只有完全退出 Python 进程，才能重置 CUDA 上下文

### 方案 2: 检查并更新 NVIDIA 驱动（如果是驱动问题）

如果驱动版本不匹配，需要更新驱动：

```bash
# 1. 检查当前驱动版本
nvidia-smi | grep "Driver Version"

# 2. 检查驱动支持的最高 CUDA 版本
nvidia-smi | grep "CUDA Version"

# 3. 如果驱动版本太低，需要更新驱动
# 注意：更新驱动需要 root 权限，可能需要重启系统
# Ubuntu/Debian:
# sudo apt update
# sudo apt install nvidia-driver-535  # 或更新版本

# CentOS/RHEL:
# sudo yum install nvidia-driver-535  # 或更新版本
```

**驱动版本要求：**
- PyTorch CUDA 12.8 需要驱动 >= 535.xx
- PyTorch CUDA 12.1 需要驱动 >= 525.xx
- PyTorch CUDA 11.8 需要驱动 >= 450.xx

### 方案 3: 重新安装匹配的 PyTorch 版本

如果驱动无法更新，安装与驱动兼容的 PyTorch 版本：

```bash
# 检查驱动支持的最高 CUDA 版本
nvidia-smi | grep "CUDA Version"

# 根据驱动支持的 CUDA 版本安装 PyTorch
# 例如：如果驱动支持 CUDA 12.6，但 PyTorch 只有 12.1，使用 12.1
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 或者使用 CPU 版本（如果驱动完全不兼容）
pip install torch torchvision torchaudio
```

### 方案 4: 暂时使用 CPU（快速解决方案）

在 `config.yaml` 中禁用 GPU：

```yaml
gpu:
  enabled: false  # 使用 CPU
```

### 方案 5: 使用修复脚本

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

