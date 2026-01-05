"""
Dual-ResNet 模型

完整的双头网络架构，包含：
- ResNet 骨干网络：提取特征
- Policy Head：输出动作概率
- Value Head：输出期望收益分数
"""

import torch
import torch.nn as nn
from typing import Tuple, Optional

from .backbone import ResNetBackbone
from .policy_head import PolicyHead
from .value_head import ValueHead


class DualResNet(nn.Module):
    """Dual-ResNet 模型
    
    完整的双头网络架构，用于强化学习训练。
    
    架构：
    1. ResNet Backbone：20+ 层残差网络，提取游戏状态特征
    2. Policy Head：输出动作概率分布（434 维）
    3. Value Head：输出期望收益分数（1 维）
    
    输入：
    - 游戏状态张量：形状为 (batch_size, 64, 4, 9)
    - 动作掩码（可选）：形状为 (batch_size, 434)
    
    输出：
    - 动作概率分布：形状为 (batch_size, 434)
    - 期望收益分数：形状为 (batch_size, 1)
    """
    
    def __init__(
        self,
        input_channels: int = 64,
        num_blocks: int = 20,
        base_channels: int = 128,
        feature_dim: int = 512,
        action_space_size: int = 434,
        hidden_dim: int = 256,
    ):
        """
        参数：
        - input_channels: 输入通道数（特征平面数，默认 64）
        - num_blocks: 残差块数量（默认 20）
        - base_channels: 基础通道数（默认 128）
        - feature_dim: 特征维度（默认 512）
        - action_space_size: 动作空间大小（默认 434）
        - hidden_dim: 隐藏层维度（默认 256）
        """
        super(DualResNet, self).__init__()
        
        # ResNet 骨干网络
        self.backbone = ResNetBackbone(
            input_channels=input_channels,
            num_blocks=num_blocks,
            base_channels=base_channels,
            feature_dim=feature_dim,
        )
        
        # Policy Head（策略头）
        self.policy_head = PolicyHead(
            feature_dim=feature_dim,
            action_space_size=action_space_size,
            hidden_dim=hidden_dim,
        )
        
        # Value Head（价值头）
        self.value_head = ValueHead(
            feature_dim=feature_dim,
            hidden_dim=hidden_dim,
        )
    
    def forward(
        self,
        state: torch.Tensor,
        action_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        参数：
        - state: 游戏状态张量，形状为 (batch_size, 64, 4, 9)
        - action_mask: 动作掩码，形状为 (batch_size, 434)（可选）
        
        返回：
        - policy: 动作概率分布，形状为 (batch_size, 434)
        - value: 期望收益分数，形状为 (batch_size, 1)
        """
        # 通过骨干网络提取特征
        features = self.backbone(state)
        
        # Policy Head：输出动作概率
        policy = self.policy_head(features, action_mask)
        
        # Value Head：输出期望收益分数
        value = self.value_head(features)
        
        return policy, value
    
    def get_policy(
        self,
        state: torch.Tensor,
        action_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        仅获取策略（动作概率分布）
        
        参数：
        - state: 游戏状态张量，形状为 (batch_size, 64, 4, 9)
        - action_mask: 动作掩码（可选）
        
        返回：
        - 动作概率分布，形状为 (batch_size, 434)
        """
        features = self.backbone(state)
        policy = self.policy_head(features, action_mask)
        return policy
    
    def get_value(
        self,
        state: torch.Tensor,
    ) -> torch.Tensor:
        """
        仅获取价值（期望收益分数）
        
        参数：
        - state: 游戏状态张量，形状为 (batch_size, 64, 4, 9)
        
        返回：
        - 期望收益分数，形状为 (batch_size, 1)
        """
        features = self.backbone(state)
        value = self.value_head(features)
        return value
    
    def get_model_info(self) -> dict:
        """获取模型信息"""
        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        
        return {
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
            "num_blocks": self.backbone.num_blocks,
            "feature_dim": self.backbone.feature_dim,
            "action_space_size": self.policy_head.action_space_size,
        }

