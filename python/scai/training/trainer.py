"""
训练器 (Trainer)

管理训练循环，协调 PPO 算法、经验回放缓冲区和奖励函数。
"""

import torch
import numpy as np
from typing import Dict, Optional, List
from tqdm import tqdm
import os

from .ppo import PPO
from .buffer import ReplayBuffer
from .reward_shaping import RewardShaping
from ..models import DualResNet
from ..utils.checkpoint import CheckpointManager


class Trainer:
    """训练器
    
    管理训练循环，协调各个组件。
    """
    
    def __init__(
        self,
        model: DualResNet,
        buffer: ReplayBuffer,
        ppo: PPO,
        reward_shaping: RewardShaping,
        checkpoint_dir: str = './checkpoints',
        device: str = 'cpu',
    ):
        """
        参数：
        - model: Dual-ResNet 模型
        - buffer: 经验回放缓冲区
        - ppo: PPO 算法实例
        - reward_shaping: 奖励函数初调实例
        - checkpoint_dir: Checkpoint 保存目录
        - device: 设备（'cpu' 或 'cuda'）
        """
        self.model = model
        self.buffer = buffer
        self.ppo = ppo
        self.reward_shaping = reward_shaping
        self.checkpoint_dir = checkpoint_dir
        self.device = device
        
        # Checkpoint 管理器
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        
        # 训练统计
        self.training_stats = {
            'total_iterations': 0,
            'total_games': 0,
            'total_steps': 0,
        }
    
    def train_step(
        self,
        batch_size: int = 4096,
        num_epochs: int = 10,
    ) -> Dict[str, float]:
        """
        执行一步训练
        
        参数：
        - batch_size: 批次大小（默认 4096）
        - num_epochs: 更新轮数（默认 10）
        
        返回：
        - 包含损失信息的字典
        """
        if not self.buffer.is_ready(min_size=batch_size):
            return {}
        
        # 采样批次
        batch = self.buffer.sample(batch_size)
        
        # PPO 更新
        losses = self.ppo.update(batch, num_epochs)
        
        # 更新统计
        self.training_stats['total_iterations'] += 1
        
        return losses
    
    def train(
        self,
        num_iterations: int = 1000,
        batch_size: int = 4096,
        num_epochs: int = 10,
        save_interval: int = 100,
        verbose: bool = True,
    ):
        """
        执行训练循环
        
        参数：
        - num_iterations: 训练迭代次数
        - batch_size: 批次大小
        - num_epochs: 更新轮数
        - save_interval: 保存间隔（每 N 次迭代保存一次）
        - verbose: 是否显示进度条
        """
        if verbose:
            pbar = tqdm(range(num_iterations), desc="Training")
        else:
            pbar = range(num_iterations)
        
        for iteration in pbar:
            # 训练一步
            losses = self.train_step(batch_size, num_epochs)
            
            # 更新进度条
            if verbose and losses:
                pbar.set_postfix(losses)
            
            # 保存 Checkpoint
            if (iteration + 1) % save_interval == 0:
                self.save_checkpoint(iteration + 1)
    
    def save_checkpoint(self, iteration: int):
        """保存 Checkpoint"""
        checkpoint_path = self.checkpoint_manager.save_checkpoint(
            self.model,
            self.ppo.optimizer,
            iteration,
            self.training_stats,
        )
        return checkpoint_path
    
    def load_checkpoint(self, checkpoint_path: str, strict: bool = True):
        """
        加载 Checkpoint
        
        参数：
        - checkpoint_path: Checkpoint 文件路径
        - strict: 是否严格匹配模型参数（默认 True）
        
        返回：
        - Checkpoint 字典
        """
        checkpoint = self.checkpoint_manager.load_checkpoint(
            checkpoint_path=checkpoint_path,
            model=self.model,
            optimizer=self.ppo.optimizer,
            device=self.device,
            strict=strict,
        )
        # 恢复训练统计
        self.training_stats = checkpoint.get('training_stats', self.training_stats)
        return checkpoint

