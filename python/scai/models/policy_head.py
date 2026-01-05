"""
策略头 (Policy Head)

输出所有可能动作的概率分布，用于指导 AI 的动作选择。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class PolicyHead(nn.Module):
    """策略头
    
    将骨干网络提取的特征转换为动作概率分布。
    
    输入：特征向量 (batch_size, feature_dim)
    输出：动作概率分布 (batch_size, action_space_size)
    
    动作空间大小：434
    - 索引 0-107: 出牌动作（108 种牌）
    - 索引 108-215: 碰牌动作（108 种牌）
    - 索引 216-323: 杠牌动作（108 种牌）
    - 索引 324-431: 胡牌动作（108 种牌）
    - 索引 432: 摸牌动作
    - 索引 433: 过（放弃）动作
    """
    
    def __init__(
        self,
        feature_dim: int = 512,
        action_space_size: int = 434,
        hidden_dim: int = 256,
    ):
        """
        参数：
        - feature_dim: 输入特征维度（默认 512）
        - action_space_size: 动作空间大小（默认 434）
        - hidden_dim: 隐藏层维度（默认 256）
        """
        super(PolicyHead, self).__init__()
        
        self.feature_dim = feature_dim
        self.action_space_size = action_space_size
        self.hidden_dim = hidden_dim
        
        # 全连接层
        self.fc1 = nn.Linear(feature_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, action_space_size)
        
        # Dropout 用于正则化
        self.dropout = nn.Dropout(0.1)
    
    def forward(
        self, 
        features: torch.Tensor,
        action_mask: torch.Tensor = None,
    ) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - features: 特征向量，形状为 (batch_size, feature_dim)
        - action_mask: 动作掩码，形状为 (batch_size, action_space_size)，
                       1.0 表示合法动作，0.0 表示非法动作（可选）
        
        返回：
        - 动作概率分布，形状为 (batch_size, action_space_size)
        """
        # 全连接层
        x = F.relu(self.fc1(features))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        
        # 应用动作掩码（如果提供）
        if action_mask is not None:
            # 将非法动作的 logits 设为负无穷，这样 softmax 后概率为 0
            x = x.masked_fill(action_mask == 0.0, float('-inf'))
        
        # Softmax 转换为概率分布
        probs = F.softmax(x, dim=-1)
        
        return probs
    
    def get_action_space_size(self) -> int:
        """获取动作空间大小"""
        return self.action_space_size

