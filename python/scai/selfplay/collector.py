"""
数据收集器 (Data Collector)

收集自对弈数据，管理轨迹数据的存储和预处理。
"""

import numpy as np
from typing import List, Dict, Optional
from collections import defaultdict

from .worker import SelfPlayWorker, create_workers, collect_trajectories_parallel
from ..training.buffer import ReplayBuffer
from ..training.reward_shaping import RewardShaping


class DataCollector:
    """数据收集器
    
    收集自对弈数据，管理轨迹数据的存储和预处理。
    """
    
    def __init__(
        self,
        buffer: ReplayBuffer,
        reward_shaping: RewardShaping,
        num_workers: int = 100,
        num_games_per_worker: int = 10,
        use_oracle: bool = True,
    ):
        """
        参数：
        - buffer: 经验回放缓冲区
        - reward_shaping: 奖励函数初调实例
        - num_workers: Worker 数量（默认 100）
        - num_games_per_worker: 每个 Worker 运行的游戏数量（默认 10）
        - use_oracle: 是否使用 Oracle 特征（默认 True）
        """
        self.buffer = buffer
        self.reward_shaping = reward_shaping
        self.num_workers = num_workers
        self.num_games_per_worker = num_games_per_worker
        self.use_oracle = use_oracle
        
        # Worker 列表
        self.workers = None
    
    def initialize_workers(self):
        """初始化 Worker"""
        if self.workers is None:
            self.workers = create_workers(
                num_workers=self.num_workers,
                num_games_per_worker=self.num_games_per_worker,
                use_oracle=self.use_oracle,
            )
    
    def collect(
        self,
        model_state_dict: Dict,
    ) -> Dict[str, int]:
        """
        收集轨迹数据
        
        参数：
        - model_state_dict: 模型状态字典
        
        返回：
        - 包含收集统计信息的字典
        """
        if self.workers is None:
            self.initialize_workers()
        
        # 并行收集轨迹
        trajectories = collect_trajectories_parallel(
            self.workers,
            model_state_dict,
        )
        
        # 处理轨迹，添加到缓冲区
        num_trajectories = len(trajectories)
        total_steps = 0
        
        for trajectory in trajectories:
            # 更新奖励
            rewards = self.reward_shaping.update_rewards(
                trajectory['rewards'],
                trajectory['final_score'],
                is_winner=trajectory['final_score'] > 0,
            )
            
            # 添加到缓冲区
            for i in range(len(trajectory['states'])):
                self.buffer.add(
                    state=trajectory['states'][i],
                    action=trajectory['actions'][i],
                    reward=rewards[i],
                    value=trajectory['values'][i],
                    log_prob=trajectory['log_probs'][i],
                    done=trajectory['dones'][i],
                    action_mask=trajectory['action_masks'][i] if 'action_masks' in trajectory else None,
                )
                total_steps += 1
            
            # 完成轨迹
            self.buffer.finish_trajectory()
        
        # 计算优势函数
        self.buffer.compute_advantages()
        
        return {
            'num_trajectories': num_trajectories,
            'total_steps': total_steps,
            'buffer_size': self.buffer.size(),
        }
    
    def collect_batch(
        self,
        model_state_dict: Dict,
        num_batches: int = 1,
    ) -> Dict[str, int]:
        """
        批量收集轨迹数据
        
        参数：
        - model_state_dict: 模型状态字典
        - num_batches: 批次数（默认 1）
        
        返回：
        - 包含收集统计信息的字典
        """
        total_stats = {
            'num_trajectories': 0,
            'total_steps': 0,
        }
        
        for _ in range(num_batches):
            stats = self.collect(model_state_dict)
            total_stats['num_trajectories'] += stats['num_trajectories']
            total_stats['total_steps'] += stats['total_steps']
        
        total_stats['buffer_size'] = self.buffer.size()
        
        return total_stats

