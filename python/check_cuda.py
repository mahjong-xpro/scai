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

# 4. 检查系统 CUDA 和驱动（如果可用）
print("\n3. 系统 CUDA 和驱动检查:")
try:
    import subprocess
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("   nvidia-smi 输出:")
        # 显示关键信息
        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if i < 15:  # 显示前15行
                print(f"   {line}")
            elif "Driver Version" in line or "CUDA Version" in line:
                print(f"   {line}")
        
        # 提取驱动版本和 CUDA 版本
        driver_version = None
        cuda_version = None
        for line in lines:
            if "Driver Version:" in line:
                parts = line.split("Driver Version:")
                if len(parts) > 1:
                    driver_version = parts[1].strip().split()[0]
            if "CUDA Version:" in line:
                parts = line.split("CUDA Version:")
                if len(parts) > 1:
                    cuda_version = parts[1].strip().split()[0]
        
        if driver_version:
            print(f"\n   📊 驱动版本: {driver_version}")
            print(f"   📊 驱动支持的最高 CUDA 版本: {cuda_version}")
            
            # 检查驱动版本是否满足要求
            try:
                driver_major = int(driver_version.split('.')[0])
                if driver_major < 450:
                    print(f"   ⚠️  驱动版本可能太旧（{driver_version}），建议 >= 450.xx")
                elif driver_major < 525:
                    print(f"   ⚠️  驱动版本可能较旧（{driver_version}），PyTorch CUDA 12.x 建议 >= 525.xx")
                elif driver_major < 535:
                    print(f"   ⚠️  驱动版本（{driver_version}），PyTorch CUDA 12.8 建议 >= 535.xx")
                else:
                    print(f"   ✓ 驱动版本看起来足够新")
            except:
                pass
    else:
        print("   ⚠️  nvidia-smi 命令失败")
except FileNotFoundError:
    print("   ⚠️  nvidia-smi 命令未找到")
except subprocess.TimeoutExpired:
    print("   ⚠️  nvidia-smi 命令超时")
except Exception as e:
    print(f"   ⚠️  检查 nvidia-smi 时出错: {e}")

# 5. 版本兼容性检查
print("\n4. 版本兼容性检查:")
try:
    import torch
    if torch.cuda.is_available():
        pytorch_cuda = torch.version.cuda
        print(f"   PyTorch CUDA 版本: {pytorch_cuda}")
        
        # 检查 CUDA 工具包版本
        try:
            result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'release' in line.lower():
                        print(f"   系统 CUDA 工具包: {line.strip()}")
        except:
            pass
    else:
        print("   ⚠️  无法检查版本兼容性（CUDA 不可用）")
except:
    pass

# 6. 建议
print("\n5. 建议:")
try:
    import torch
    if not torch.cuda.is_available():
        print("   如果 nvidia-smi 显示 GPU 但 PyTorch 检测不到，可能的原因：")
        print("   1. ⚠️  驱动版本问题（最可能）:")
        print("      - 检查驱动版本: nvidia-smi | grep 'Driver Version'")
        print("      - PyTorch CUDA 12.8 需要驱动 >= 535.xx")
        print("      - PyTorch CUDA 12.1 需要驱动 >= 525.xx")
        print("      - 如果驱动太旧，需要更新驱动")
        print("   2. PyTorch CUDA 版本与驱动不匹配:")
        print("      - 检查: python -c 'import torch; print(torch.version.cuda)'")
        print("      - 重新安装匹配的 PyTorch 版本")
        print("   3. 暂时使用 CPU 训练:")
        print("      - 在 config.yaml 中设置 gpu.enabled: false")
except:
    pass

print("\n" + "=" * 60)

