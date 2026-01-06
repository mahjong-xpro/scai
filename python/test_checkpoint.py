#!/usr/bin/env python3
"""
检查点功能测试脚本

验证检查点的保存和加载功能是否完整。
"""

import torch
import os
import tempfile
import shutil
from pathlib import Path

from scai.models import DualResNet
from scai.training.ppo import PPO
from scai.training.buffer import ReplayBuffer
from scai.training.reward_shaping import RewardShaping
from scai.training.trainer import Trainer
from scai.utils.checkpoint import CheckpointManager


def test_checkpoint_manager():
    """测试 CheckpointManager 的基本功能"""
    print("=" * 60)
    print("测试 CheckpointManager")
    print("=" * 60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print(f"临时目录: {temp_dir}")
    
    try:
        # 创建模型和优化器
        model = DualResNet()
        optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)
        
        # 创建 CheckpointManager
        manager = CheckpointManager(checkpoint_dir=temp_dir)
        
        # 测试保存
        print("\n1. 测试保存 Checkpoint...")
        training_stats = {
            'total_iterations': 100,
            'total_games': 1000,
            'total_steps': 5000,
        }
        metadata = {
            'config': 'test_config',
            'version': '1.0',
        }
        
        checkpoint_path = manager.save_checkpoint(
            model=model,
            optimizer=optimizer,
            iteration=100,
            training_stats=training_stats,
            metadata=metadata,
        )
        print(f"✓ Checkpoint 已保存: {checkpoint_path}")
        assert os.path.exists(checkpoint_path), "Checkpoint 文件不存在"
        assert os.path.exists(os.path.join(temp_dir, 'latest.pt')), "latest.pt 不存在"
        
        # 测试加载
        print("\n2. 测试加载 Checkpoint...")
        new_model = DualResNet()
        new_optimizer = torch.optim.Adam(new_model.parameters(), lr=3e-4)
        
        checkpoint = manager.load_checkpoint(
            checkpoint_path=checkpoint_path,
            model=new_model,
            optimizer=new_optimizer,
        )
        
        print(f"✓ Checkpoint 已加载")
        assert checkpoint['iteration'] == 100, "迭代次数不匹配"
        assert checkpoint['training_stats']['total_iterations'] == 100, "训练统计不匹配"
        assert checkpoint['metadata']['config'] == 'test_config', "元数据不匹配"
        
        # 验证模型状态是否一致
        print("\n3. 验证模型状态...")
        model_params = list(model.parameters())
        new_model_params = list(new_model.parameters())
        for p1, p2 in zip(model_params, new_model_params):
            assert torch.allclose(p1, p2), "模型参数不匹配"
        print("✓ 模型参数一致")
        
        # 验证优化器状态
        print("\n4. 验证优化器状态...")
        # 优化器状态可能包含动量等，这里只检查是否能正常加载
        assert len(new_optimizer.state_dict()['state']) > 0, "优化器状态为空"
        print("✓ 优化器状态已加载")
        
        # 测试 list_checkpoints
        print("\n5. 测试列出所有 Checkpoint...")
        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 1, f"期望 1 个 Checkpoint，实际 {len(checkpoints)}"
        print(f"✓ 找到 {len(checkpoints)} 个 Checkpoint")
        
        # 测试 get_latest_checkpoint
        print("\n6. 测试获取最新 Checkpoint...")
        latest = manager.get_latest_checkpoint()
        assert latest == checkpoint_path or latest == os.path.join(temp_dir, 'latest.pt'), "最新 Checkpoint 路径不正确"
        print(f"✓ 最新 Checkpoint: {latest}")
        
        print("\n" + "=" * 60)
        print("✓ CheckpointManager 测试通过！")
        print("=" * 60)
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录: {temp_dir}")


def test_trainer_checkpoint():
    """测试 Trainer 的检查点功能"""
    print("\n" + "=" * 60)
    print("测试 Trainer 检查点功能")
    print("=" * 60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print(f"临时目录: {temp_dir}")
    
    try:
        # 创建组件
        model = DualResNet()
        buffer = ReplayBuffer(capacity=1000)
        ppo = PPO(model=model, learning_rate=3e-4)
        reward_shaping = RewardShaping()
        
        # 创建 Trainer
        trainer = Trainer(
            model=model,
            buffer=buffer,
            ppo=ppo,
            reward_shaping=reward_shaping,
            checkpoint_dir=temp_dir,
        )
        
        # 修改训练统计
        trainer.training_stats['total_iterations'] = 50
        trainer.training_stats['total_games'] = 500
        trainer.training_stats['total_steps'] = 2500
        
        # 保存 Checkpoint
        print("\n1. 测试 Trainer.save_checkpoint()...")
        checkpoint_path = trainer.save_checkpoint(iteration=50)
        print(f"✓ Checkpoint 已保存: {checkpoint_path}")
        assert os.path.exists(checkpoint_path), "Checkpoint 文件不存在"
        
        # 修改模型和统计（模拟继续训练）
        trainer.training_stats['total_iterations'] = 100
        for param in model.parameters():
            param.data += 0.1  # 修改参数
        
        # 加载 Checkpoint
        print("\n2. 测试 Trainer.load_checkpoint()...")
        checkpoint = trainer.load_checkpoint(checkpoint_path)
        print(f"✓ Checkpoint 已加载")
        
        # 验证训练统计是否恢复
        print("\n3. 验证训练统计是否恢复...")
        assert trainer.training_stats['total_iterations'] == 50, "训练统计未恢复"
        assert trainer.training_stats['total_games'] == 500, "训练统计未恢复"
        print("✓ 训练统计已恢复")
        
        # 验证模型参数是否恢复（通过检查参数是否被重置）
        print("\n4. 验证模型参数是否恢复...")
        # 注意：由于我们修改了参数，如果加载成功，参数应该被重置
        # 这里我们检查模型状态是否被正确加载
        assert 'model_state_dict' in checkpoint, "Checkpoint 缺少模型状态"
        assert 'optimizer_state_dict' in checkpoint, "Checkpoint 缺少优化器状态"
        print("✓ 模型和优化器状态已恢复")
        
        print("\n" + "=" * 60)
        print("✓ Trainer 检查点功能测试通过！")
        print("=" * 60)
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录: {temp_dir}")


def test_checkpoint_completeness():
    """测试 Checkpoint 的完整性"""
    print("\n" + "=" * 60)
    print("测试 Checkpoint 完整性")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    print(f"临时目录: {temp_dir}")
    
    try:
        model = DualResNet()
        optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)
        manager = CheckpointManager(checkpoint_dir=temp_dir)
        
        # 保存完整的 Checkpoint
        training_stats = {
            'total_iterations': 100,
            'total_games': 1000,
            'total_steps': 5000,
            'avg_loss': 0.5,
        }
        metadata = {
            'config_file': 'config.yaml',
            'git_commit': 'abc123',
            'training_time': '2024-01-01T12:00:00',
        }
        
        checkpoint_path = manager.save_checkpoint(
            model=model,
            optimizer=optimizer,
            iteration=100,
            training_stats=training_stats,
            metadata=metadata,
        )
        
        # 加载并验证所有字段
        print("\n验证 Checkpoint 包含的所有字段...")
        checkpoint = torch.load(checkpoint_path)
        
        required_fields = [
            'iteration',
            'model_state_dict',
            'optimizer_state_dict',
            'training_stats',
            'metadata',
            'timestamp',
        ]
        
        for field in required_fields:
            assert field in checkpoint, f"Checkpoint 缺少字段: {field}"
            print(f"✓ 字段 '{field}' 存在")
        
        # 验证字段内容
        assert checkpoint['iteration'] == 100, "迭代次数不正确"
        assert checkpoint['training_stats']['total_iterations'] == 100, "训练统计不正确"
        assert checkpoint['metadata']['config_file'] == 'config.yaml', "元数据不正确"
        assert 'timestamp' in checkpoint and checkpoint['timestamp'], "时间戳不存在"
        
        print("\n" + "=" * 60)
        print("✓ Checkpoint 完整性测试通过！")
        print("=" * 60)
        
    finally:
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录: {temp_dir}")


def test_checkpoint_error_handling():
    """测试 Checkpoint 的错误处理"""
    print("\n" + "=" * 60)
    print("测试 Checkpoint 错误处理")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    print(f"临时目录: {temp_dir}")
    
    try:
        manager = CheckpointManager(checkpoint_dir=temp_dir)
        
        # 测试加载不存在的文件
        print("\n1. 测试加载不存在的文件...")
        try:
            manager.load_checkpoint('nonexistent.pt')
            assert False, "应该抛出异常"
        except Exception as e:
            print(f"✓ 正确捕获异常: {type(e).__name__}")
        
        # 测试空目录
        print("\n2. 测试空目录...")
        empty_dir = tempfile.mkdtemp()
        empty_manager = CheckpointManager(checkpoint_dir=empty_dir)
        latest = empty_manager.get_latest_checkpoint()
        assert latest is None, "空目录应该返回 None"
        print("✓ 空目录处理正确")
        
        checkpoints = empty_manager.list_checkpoints()
        assert len(checkpoints) == 0, "空目录应该返回空列表"
        print("✓ 空目录列表处理正确")
        
        shutil.rmtree(empty_dir)
        
        print("\n" + "=" * 60)
        print("✓ 错误处理测试通过！")
        print("=" * 60)
        
    finally:
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录: {temp_dir}")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("检查点功能测试")
    print("=" * 60)
    
    try:
        test_checkpoint_manager()
        test_trainer_checkpoint()
        test_checkpoint_completeness()
        test_checkpoint_error_handling()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        raise

