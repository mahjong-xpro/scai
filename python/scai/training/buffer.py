"""
经验回放缓冲区 (Replay Buffer)

用于存储和采样训练数据，支持 PPO 算法的经验回放。
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque
import torch


class ReplayBuffer:
    """经验回放缓冲区
    
    存储游戏轨迹（Trajectories），支持批量采样和更新。
    
    数据结构：
    - states: 游戏状态张量列表
    - actions: 动作列表
    - rewards: 奖励列表
    - values: 价值估计列表
    - log_probs: 动作的对数概率列表
    - dones: 是否结束标志列表
    - advantages: 优势函数值（计算后填充）
    - returns: 回报值（计算后填充）
    """
    
    def __init__(self, capacity: int = 100000):
        """
        参数：
        - capacity: 缓冲区容量（默认 100000）
        """
        self.capacity = capacity
        
        # 存储轨迹数据
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
        self.action_masks = []
        
        # 计算后的数据
        self.advantages = []
        self.returns = []
        
        # 当前轨迹
        self.current_trajectory = {
            'states': [],
            'actions': [],
            'rewards': [],
            'values': [],
            'log_probs': [],
            'dones': [],
            'action_masks': [],
        }
    
    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        value: float,
        log_prob: float,
        done: bool,
        action_mask: Optional[np.ndarray] = None,
    ):
        """
        添加一个时间步的数据
        
        参数：
        - state: 游戏状态（2412 维向量）
        - action: 动作索引
        - reward: 即时奖励
        - value: 价值估计
        - log_prob: 动作的对数概率
        - done: 是否结束
        - action_mask: 动作掩码（可选）
        """
        self.current_trajectory['states'].append(state)
        self.current_trajectory['actions'].append(action)
        self.current_trajectory['rewards'].append(reward)
        self.current_trajectory['values'].append(value)
        self.current_trajectory['log_probs'].append(log_prob)
        self.current_trajectory['dones'].append(done)
        if action_mask is not None:
            self.current_trajectory['action_masks'].append(action_mask)
    
    def finish_trajectory(self):
        """完成当前轨迹，将其添加到缓冲区"""
        if len(self.current_trajectory['states']) == 0:
            return
        
        # 添加到缓冲区
        self.states.extend(self.current_trajectory['states'])
        self.actions.extend(self.current_trajectory['actions'])
        self.rewards.extend(self.current_trajectory['rewards'])
        self.values.extend(self.current_trajectory['values'])
        self.log_probs.extend(self.current_trajectory['log_probs'])
        self.dones.extend(self.current_trajectory['dones'])
        if len(self.current_trajectory['action_masks']) > 0:
            self.action_masks.extend(self.current_trajectory['action_masks'])
        
        # 清空当前轨迹
        self.current_trajectory = {
            'states': [],
            'actions': [],
            'rewards': [],
            'values': [],
            'log_probs': [],
            'dones': [],
            'action_masks': [],
        }
        
        # 如果超过容量，删除最旧的数据
        if len(self.states) > self.capacity:
            excess = len(self.states) - self.capacity
            self.states = self.states[excess:]
            self.actions = self.actions[excess:]
            self.rewards = self.rewards[excess:]
            self.values = self.values[excess:]
            self.log_probs = self.log_probs[excess:]
            self.dones = self.dones[excess:]
            if len(self.action_masks) > 0:
                self.action_masks = self.action_masks[excess:]
    
    def compute_advantages(
        self,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        last_value: float = 0.0,
    ):
        """
        计算优势函数（GAE - Generalized Advantage Estimation）
        
        参数：
        - gamma: 折扣因子（默认 0.99）
        - gae_lambda: GAE 参数（默认 0.95）
        - last_value: 最后一个状态的价值估计（默认 0.0）
        """
        # 检查所有轨迹是否已完成
        if len(self.current_trajectory['states']) > 0:
            raise ValueError("Cannot compute advantages: current trajectory is not finished. Call finish_trajectory() first.")
        
        # 验证数据一致性
        n = len(self.rewards)
        if len(self.values) != n or len(self.dones) != n:
            raise ValueError(f"Data length mismatch: rewards={n}, values={len(self.values)}, dones={len(self.dones)}")
        
        advantages = []
        returns = []
        
        # 从后往前计算
        gae = 0.0
        next_value = last_value
        
        for i in reversed(range(len(self.rewards))):
            if self.dones[i]:
                gae = 0.0
                next_value = 0.0
            
            delta = self.rewards[i] + gamma * next_value - self.values[i]
            gae = delta + gamma * gae_lambda * gae
            advantages.insert(0, gae)
            
            # 计算回报
            returns.insert(0, gae + self.values[i])
            
            next_value = self.values[i]
        
        self.advantages = advantages
        self.returns = returns
    
    def sample(self, batch_size: int) -> Dict[str, torch.Tensor]:
        """
        采样一个批次的数据
        
        参数：
        - batch_size: 批次大小
        
        返回：
        - 包含 states, actions, advantages, returns, log_probs, action_masks 的字典
        """
        if len(self.states) == 0:
            raise ValueError("Buffer is empty")
        
        # 随机采样索引
        indices = np.random.choice(len(self.states), size=batch_size, replace=True)
        
        # 转换为张量
        states = torch.FloatTensor(np.array([self.states[i] for i in indices]))
        actions = torch.LongTensor([self.actions[i] for i in indices])
        advantages = torch.FloatTensor([self.advantages[i] for i in indices])
        returns = torch.FloatTensor([self.returns[i] for i in indices])
        old_log_probs = torch.FloatTensor([self.log_probs[i] for i in indices])
        
        result = {
            'states': states,
            'actions': actions,
            'advantages': advantages,
            'returns': returns,
            'old_log_probs': old_log_probs,
        }
        
        # 如果有动作掩码，也包含
        if len(self.action_masks) > 0:
            result['action_masks'] = torch.FloatTensor(
                np.array([self.action_masks[i] for i in indices])
            )
        
        return result
    
    def clear(self):
        """清空缓冲区"""
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
        self.action_masks = []
        self.advantages = []
        self.returns = []
        self.current_trajectory = {
            'states': [],
            'actions': [],
            'rewards': [],
            'values': [],
            'log_probs': [],
            'dones': [],
            'action_masks': [],
        }
    
    def size(self) -> int:
        """返回缓冲区中的数据量"""
        return len(self.states)
    
    def is_ready(self, min_size: int = 1000) -> bool:
        """检查缓冲区是否有足够的数据"""
        return len(self.states) >= min_size

