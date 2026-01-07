#!/usr/bin/env python3
"""
CUDA 诊断脚本

检查 CUDA 和 GPU 的可用性，帮助诊断 PyTorch CUDA 问题。
"""

import os
import sys

print("=" * 60)
print("CUDA 诊断信息")
print("=" * 60)

# 1. 检查环境变量
print("\n1. 环境变量检查:")
cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES", "not set")
print(f"   CUDA_VISIBLE_DEVICES: {cuda_visible}")

# 2. 清除可能无效的环境变量
if "CUDA_VISIBLE_DEVICES" in os.environ:
    print("   清除 CUDA_VISIBLE_DEVICES...")
    del os.environ["CUDA_VISIBLE_DEVICES"]

# 3. 检查 PyTorch
print("\n2. PyTorch CUDA 检查:")
try:
    import torch
    print(f"   PyTorch version: {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"   CUDA version (PyTorch): {torch.version.cuda}")
        print(f"   cuDNN version: {torch.backends.cudnn.version()}")
        print(f"   GPU count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
    else:
        print("   ⚠️  PyTorch 无法检测到 CUDA")
        print("   可能的原因:")
        print("     - PyTorch 是用 CPU-only 版本安装的")
        print("     - PyTorch CUDA 版本与系统 CUDA 驱动不匹配")
        print("     - CUDA 驱动未正确安装")
        
except Exception as e:
    print(f"   ❌ 导入 PyTorch 时出错: {e}")

# 4. 检查系统 CUDA（如果可用）
print("\n3. 系统 CUDA 检查:")
try:
    import subprocess
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("   nvidia-smi 输出:")
        # 只显示前几行
        lines = result.stdout.split('\n')[:10]
        for line in lines:
            print(f"   {line}")
    else:
        print("   ⚠️  nvidia-smi 命令失败")
except FileNotFoundError:
    print("   ⚠️  nvidia-smi 命令未找到")
except subprocess.TimeoutExpired:
    print("   ⚠️  nvidia-smi 命令超时")
except Exception as e:
    print(f"   ⚠️  检查 nvidia-smi 时出错: {e}")

# 5. 建议
print("\n4. 建议:")
if not torch.cuda.is_available():
    print("   如果 nvidia-smi 显示 GPU 但 PyTorch 检测不到:")
    print("   1. 检查 PyTorch CUDA 版本:")
    print("      python -c 'import torch; print(torch.version.cuda)'")
    print("   2. 检查系统 CUDA 版本:")
    print("      nvcc --version")
    print("   3. 重新安装匹配的 PyTorch 版本:")
    print("      https://pytorch.org/get-started/locally/")
    print("   4. 或者暂时使用 CPU 训练（在 config.yaml 中设置 gpu.enabled: false）")

print("\n" + "=" * 60)

