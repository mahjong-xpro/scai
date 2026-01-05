#!/usr/bin/env python3
"""
测试 Dual-ResNet 模型架构

验证模型是否能正常初始化和前向传播。
"""

try:
    import torch
    from scai.models import DualResNet
    
    print("=" * 60)
    print("测试 Dual-ResNet 模型架构")
    print("=" * 60)
    
    # 创建模型
    print("\n1. 创建模型...")
    model = DualResNet(
        input_channels=64,
        num_blocks=20,
        base_channels=128,
        feature_dim=512,
        action_space_size=434,
    )
    print("✅ 模型创建成功")
    
    # 获取模型信息
    print("\n2. 模型信息:")
    info = model.get_model_info()
    for key, value in info.items():
        print(f"   {key}: {value:,}")
    
    # 测试前向传播
    print("\n3. 测试前向传播...")
    batch_size = 4
    state = torch.randn(batch_size, 64, 4, 9)
    action_mask = torch.ones(batch_size, 434)
    
    # 前向传播
    policy, value = model(state, action_mask)
    
    print(f"   输入形状: {state.shape}")
    print(f"   策略输出形状: {policy.shape}")
    print(f"   价值输出形状: {value.shape}")
    print("✅ 前向传播成功")
    
    # 验证输出
    print("\n4. 验证输出:")
    print(f"   策略概率和: {policy.sum(dim=1).mean().item():.4f} (应该接近 1.0)")
    print(f"   价值范围: [{value.min().item():.2f}, {value.max().item():.2f}]")
    
    # 测试单独获取策略和价值
    print("\n5. 测试单独获取策略和价值...")
    policy_only = model.get_policy(state, action_mask)
    value_only = model.get_value(state)
    print(f"   策略形状: {policy_only.shape}")
    print(f"   价值形状: {value_only.shape}")
    print("✅ 单独获取成功")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请先安装 PyTorch: pip install torch")
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

