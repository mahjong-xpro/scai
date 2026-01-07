#!/usr/bin/env python3
"""
修复 CUDA 环境变量问题

清除可能无效的 CUDA_VISIBLE_DEVICES，然后测试 PyTorch CUDA 可用性。
注意：如果 PyTorch 已经在当前进程中初始化过 CUDA，可能需要重启 Python 进程。
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
else:
    print("   ✓ 未设置（无需清除）")

# 3. 检查驱动版本
print("\n3. 检查 NVIDIA 驱动:")
try:
    import subprocess
    result = subprocess.run(['nvidia-smi', '--query-gpu=driver_version,cuda_version', '--format=csv,noheader'], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        for i, line in enumerate(lines):
            parts = line.split(', ')
            if len(parts) >= 2:
                driver = parts[0].strip()
                cuda = parts[1].strip()
                print(f"   GPU {i}: 驱动版本 {driver}, 支持 CUDA {cuda}")
                
                # 检查驱动版本
                try:
                    driver_major = int(driver.split('.')[0])
                    if driver_major < 450:
                        print(f"      ⚠️  驱动版本可能太旧")
                    elif driver_major < 525:
                        print(f"      ⚠️  驱动版本较旧，PyTorch CUDA 12.x 建议 >= 525.xx")
                    elif driver_major < 535:
                        print(f"      ⚠️  驱动版本，PyTorch CUDA 12.8 建议 >= 535.xx")
                except:
                    pass
    else:
        print("   ⚠️  无法获取驱动信息")
except Exception as e:
    print(f"   ⚠️  检查驱动时出错: {e}")

# 4. 测试 PyTorch（在新的导入中）
print("\n4. 测试 PyTorch CUDA:")
print("   注意：如果之前已经导入过 torch，可能需要重启 Python 进程")
try:
    # 如果 torch 已经导入，先尝试重置（但这通常不起作用）
    if 'torch' in sys.modules:
        print("   ⚠️  torch 已经在当前进程中导入，错误状态可能已保留")
        print("   建议：退出当前 Python 进程，在新的进程中运行此脚本")
    
    import torch
    print(f"   PyTorch version: {torch.__version__}")
    
    # 检查是否有 CUDA 支持
    if hasattr(torch.version, 'cuda') and torch.version.cuda:
        print(f"   PyTorch CUDA version: {torch.version.cuda}")
    else:
        print(f"   ⚠️  PyTorch 可能是 CPU-only 版本（没有 CUDA 支持）")
    
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
            print(f"\n   可能的原因:")
            print(f"   1. ⚠️  驱动版本问题（最可能）")
            print(f"      - PyTorch CUDA {torch.version.cuda if hasattr(torch.version, 'cuda') else 'unknown'} 需要特定驱动版本")
            print(f"      - 检查驱动版本是否满足要求")
            print(f"   2. PyTorch CUDA 版本与驱动不匹配")
            print(f"   3. PyTorch 是 CPU-only 版本")
            print(f"   4. 如果之前设置过无效的 CUDA_VISIBLE_DEVICES，需要重启 Python 进程")
    except RuntimeError as e:
        if "invalid device ordinal" in str(e) or "Error 101" in str(e):
            print(f"   ✗ CUDA 初始化错误: {e}")
            print(f"\n   ⚠️  这是典型的 'Error 101: invalid device ordinal' 错误")
            print(f"   可能的原因:")
            print(f"   1. 之前设置过无效的 CUDA_VISIBLE_DEVICES（如 GPU ID 不存在）")
            print(f"   2. PyTorch 的 CUDA 上下文已被污染")
            print(f"   3. 驱动版本不匹配")
            print(f"\n   解决方案:")
            print(f"   1. 完全退出当前 Python 进程")
            print(f"   2. 在新的 shell 中运行: unset CUDA_VISIBLE_DEVICES")
            print(f"   3. 然后运行训练脚本")
            print(f"   4. 或者暂时使用 CPU（在 config.yaml 中设置 gpu.enabled: false）")
        else:
            print(f"   ✗ 检测 GPU 时出错: {e}")
    except Exception as e:
        print(f"   ✗ 检测 GPU 时出错: {e}")
        
except ImportError:
    print("   ✗ PyTorch 未安装")
except Exception as e:
    print(f"   ✗ 导入 PyTorch 时出错: {e}")

print("\n" + "=" * 60)
print("建议:")
print("1. 如果出现 'Error 101: invalid device ordinal':")
print("   - 完全退出 Python 进程（不要只是清除环境变量）")
print("   - 在新的 shell 中运行训练")
print("2. 如果驱动版本太低，更新驱动或安装匹配的 PyTorch 版本")
print("3. 或者暂时使用 CPU 训练（在 config.yaml 中设置 gpu.enabled: false）")
print("=" * 60)

