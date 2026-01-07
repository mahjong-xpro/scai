#!/usr/bin/env python3
"""
修复 CUDA 环境变量问题

清除可能无效的 CUDA_VISIBLE_DEVICES，然后测试 PyTorch CUDA 可用性。
"""

import os
import sys

print("=" * 60)
print("修复 CUDA 环境变量")
print("=" * 60)

# 1. 检查当前环境变量
print("\n1. 当前环境变量:")
cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES", "not set")
print(f"   CUDA_VISIBLE_DEVICES: {cuda_visible}")

# 2. 清除环境变量
print("\n2. 清除 CUDA_VISIBLE_DEVICES...")
if "CUDA_VISIBLE_DEVICES" in os.environ:
    del os.environ["CUDA_VISIBLE_DEVICES"]
    print("   ✓ 已清除")

# 3. 测试 PyTorch
print("\n3. 测试 PyTorch CUDA:")
try:
    import torch
    print(f"   PyTorch version: {torch.__version__}")
    print(f"   PyTorch CUDA version: {torch.version.cuda}")
    
    # 尝试检测 GPU
    try:
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_count = torch.cuda.device_count()
            print(f"   ✓ CUDA available: True")
            print(f"   ✓ GPU count: {gpu_count}")
            for i in range(gpu_count):
                print(f"   ✓ GPU {i}: {torch.cuda.get_device_name(i)}")
        else:
            print(f"   ✗ CUDA available: False")
            print(f"   这可能是因为:")
            print(f"     - PyTorch CUDA 版本 ({torch.version.cuda}) 与系统 CUDA (12.6) 不匹配")
            print(f"     - 或者 PyTorch 是 CPU-only 版本")
    except Exception as e:
        print(f"   ✗ 检测 GPU 时出错: {e}")
        
except ImportError:
    print("   ✗ PyTorch 未安装")
except Exception as e:
    print(f"   ✗ 导入 PyTorch 时出错: {e}")

print("\n" + "=" * 60)
print("建议:")
print("1. 如果仍然检测不到 GPU，尝试重新安装匹配的 PyTorch:")
print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126")
print("2. 或者暂时使用 CPU 训练（在 config.yaml 中设置 gpu.enabled: false）")
print("=" * 60)

