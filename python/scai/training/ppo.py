"""
PPO (Proximal Policy Optimization) 算法实现

实现 PPO 算法的核心逻辑，包括：
- 策略更新
- 价值函数更新
- 策略裁剪（Clipping）
- 优势函数计算
"""

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, Optional
import numpy as np

from ..models import DualResNet


class PPO:
    """PPO (Proximal Policy Optimization) 算法
    
    实现 PPO 算法的核心逻辑，用于策略优化。
    """
    
    def __init__(
        self,
        model: DualResNet,
        learning_rate: float = 3e-4,
        clip_epsilon: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        device: str = 'cpu',
    ):
        """
        参数：
        - model: Dual-ResNet 模型
        - learning_rate: 学习率（默认 3e-4）
        - clip_epsilon: 裁剪参数（默认 0.2）
        - value_coef: 价值损失系数（默认 0.5）
        - entropy_coef: 熵系数（默认 0.01）
        - max_grad_norm: 梯度裁剪阈值（默认 0.5）
        - device: 设备（'cpu' 或 'cuda'）
        """
        self.model = model.to(device)
        self.device = device
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        
        # 优化器
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
    
    def update(
        self,
        batch: Dict[str, torch.Tensor],
        num_epochs: int = 10,
    ) -> Dict[str, float]:
        """
        更新策略和价值函数
        
        参数：
        - batch: 批次数据（包含 states, actions, advantages, returns, old_log_probs）
        - num_epochs: 更新轮数（默认 10）
        
        返回：
        - 包含损失信息的字典
        """
        states = batch['states'].to(self.device)
        actions = batch['actions'].to(self.device)
        advantages = batch['advantages'].to(self.device)
        returns = batch['returns'].to(self.device)
        old_log_probs = batch['old_log_probs'].to(self.device)
        action_masks = batch.get('action_masks', None)
        if action_masks is not None:
            action_masks = action_masks.to(self.device)
        
        # 归一化优势函数
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy_loss = 0.0
        
        # 多轮更新
        for epoch in range(num_epochs):
            # 前向传播
            policy, value = self.model(states, action_masks)
            
            # 计算新的对数概率
            log_probs = torch.log(policy.gather(1, actions.unsqueeze(1)).squeeze(1) + 1e-8)
            
            # 计算比率
            ratio = torch.exp(log_probs - old_log_probs)
            
            # 策略损失（带裁剪）
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1.0 - self.clip_epsilon, 1.0 + self.clip_epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # 价值损失
            value_loss = nn.functional.mse_loss(value.squeeze(), returns)
            
            # 熵损失（鼓励探索）
            entropy = -(policy * torch.log(policy + 1e-8)).sum(dim=1).mean()
            entropy_loss = -entropy
            
            # 总损失
            loss = policy_loss + self.value_coef * value_loss + self.entropy_coef * entropy_loss
            
            # 反向传播
            self.optimizer.zero_grad()
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
            
            self.optimizer.step()
            
            # 累计损失
            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()
            total_entropy_loss += entropy_loss.item()
        
        # 平均损失
        num_epochs_float = float(num_epochs)
        return {
            'policy_loss': total_policy_loss / num_epochs_float,
            'value_loss': total_value_loss / num_epochs_float,
            'entropy_loss': total_entropy_loss / num_epochs_float,
            'total_loss': (total_policy_loss + self.value_coef * total_value_loss + 
                          self.entropy_coef * total_entropy_loss) / num_epochs_float,
        }
    
    def get_action(
        self,
        state: np.ndarray,
        action_mask: Optional[np.ndarray] = None,
        deterministic: bool = False,
    ) -> Tuple[int, float, float]:
        """
        根据当前策略选择动作
        
        参数：
        - state: 游戏状态（2412 维向量）
        - action_mask: 动作掩码（可选）
        - deterministic: 是否使用确定性策略（默认 False，使用随机策略）
        
        返回：
        - (action, log_prob, value) 元组
        """
        self.model.eval()
        
        with torch.no_grad():
            # 转换为张量
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            if action_mask is not None:
                action_mask_tensor = torch.FloatTensor(action_mask).unsqueeze(0).to(self.device)
            else:
                action_mask_tensor = None
            
            # 前向传播
            policy, value = self.model(state_tensor, action_mask_tensor)
            
            # 选择动作
            if deterministic:
                action = policy.argmax(dim=1).item()
            else:
                # 采样动作
                action = torch.multinomial(policy, 1).item()
            
            # 计算对数概率
            log_prob = torch.log(policy[0, action] + 1e-8).item()
            value_estimate = value.item()
        
        self.model.train()
        
        return action, log_prob, value_estimate
    
    def save(self, path: str):
        """保存模型"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        }, path)
    
    def load(self, path: str):
        """加载模型"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

