"""
价值头 (Value Head)

预测当前局面的期望收益分数，用于评估状态价值。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ValueHead(nn.Module):
    """价值头
    
    将骨干网络提取的特征转换为期望收益分数。
    
    输入：特征向量 (batch_size, feature_dim)
    输出：期望收益分数 (batch_size, 1)
    
    在血战到底中，价值头预测的是"最终总分"的回归值。
    这包括：
    - 胡牌得分
    - 刮风下雨（杠钱）
    - 查大叫/查花猪的奖惩
    - 最终结算得分
    """
    
    def __init__(
        self,
        feature_dim: int = 512,
        hidden_dim: int = 256,
    ):
        """
        参数：
        - feature_dim: 输入特征维度（默认 512）
        - hidden_dim: 隐藏层维度（默认 256）
        """
        super(ValueHead, self).__init__()
        
        self.feature_dim = feature_dim
        self.hidden_dim = hidden_dim
        
        # 全连接层
        self.fc1 = nn.Linear(feature_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, 1)  # 输出单个标量值
        
        # Dropout 用于正则化
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - features: 特征向量，形状为 (batch_size, feature_dim)
        
        返回：
        - 期望收益分数，形状为 (batch_size, 1)
        """
        # 全连接层
        x = F.relu(self.fc1(features))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        
        return x
    
    def get_output_dim(self) -> int:
        """获取输出维度（始终为 1）"""
        return 1

