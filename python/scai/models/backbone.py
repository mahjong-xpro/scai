"""
ResNet 骨干网络

实现 20+ 层的残差网络，用于提取游戏状态的特征表示。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    """残差块
    
    结构：Conv2d -> BatchNorm -> ReLU -> Conv2d -> BatchNorm -> 残差连接 -> ReLU
    """
    
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super(ResidualBlock, self).__init__()
        
        self.conv1 = nn.Conv2d(
            in_channels, out_channels, 
            kernel_size=3, stride=stride, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(out_channels)
        
        self.conv2 = nn.Conv2d(
            out_channels, out_channels,
            kernel_size=3, stride=1, padding=1, bias=False
        )
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        # 如果输入输出通道数或步长不同，需要下采样
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播"""
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)  # 残差连接
        out = F.relu(out)
        return out


class ResNetBackbone(nn.Module):
    """ResNet 骨干网络
    
    20+ 层的残差网络，用于提取游戏状态的特征表示。
    
    架构：
    - 初始卷积层：将输入 (64, 4, 9) 转换为特征图
    - 20 个残差块：逐步提取深层特征
    - 全局平均池化：将特征图压缩为向量
    
    输入形状：(batch_size, 64, 4, 9)
    输出形状：(batch_size, feature_dim)
    """
    
    def __init__(
        self,
        input_channels: int = 64,
        num_blocks: int = 20,
        base_channels: int = 128,
        feature_dim: int = 512,
    ):
        """
        参数：
        - input_channels: 输入通道数（特征平面数，默认 64）
        - num_blocks: 残差块数量（默认 20）
        - base_channels: 基础通道数（默认 128）
        - feature_dim: 输出特征维度（默认 512）
        """
        super(ResNetBackbone, self).__init__()
        
        self.input_channels = input_channels
        self.num_blocks = num_blocks
        self.base_channels = base_channels
        self.feature_dim = feature_dim
        
        # 初始卷积层：将输入转换为特征图
        self.conv1 = nn.Conv2d(
            input_channels, base_channels,
            kernel_size=3, stride=1, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(base_channels)
        
        # 残差块层
        # 每 5 个块为一组，逐步增加通道数
        self.layers = nn.ModuleList()
        in_channels = base_channels
        
        # 分组：每组 5 个块
        num_groups = (num_blocks + 4) // 5  # 向上取整
        blocks_per_group = num_blocks // num_groups
        
        for i in range(num_groups):
            out_channels = base_channels * (2 ** min(i, 2))  # 最多增加到 4 倍
            
            # 每组第一个块可能需要下采样
            stride = 2 if i > 0 and in_channels != out_channels else 1
            
            # 添加该组的残差块
            for j in range(blocks_per_group):
                if i == num_groups - 1 and j == blocks_per_group - 1:
                    # 最后一组最后一个块，确保总数达到 num_blocks
                    remaining = num_blocks - (i * blocks_per_group + j)
                    if remaining > 0:
                        blocks_per_group = remaining
                
                block_stride = stride if j == 0 else 1
                self.layers.append(ResidualBlock(in_channels, out_channels, block_stride))
                in_channels = out_channels
        
        # 全局平均池化
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        
        # 全连接层：将特征图压缩为向量
        self.fc = nn.Linear(in_channels, feature_dim)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        参数：
        - x: 输入张量，形状为 (batch_size, 64, 4, 9)
        
        返回：
        - 特征向量，形状为 (batch_size, feature_dim)
        """
        # 初始卷积
        x = F.relu(self.bn1(self.conv1(x)))
        
        # 残差块
        for layer in self.layers:
            x = layer(x)
        
        # 全局平均池化
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)  # 展平
        
        # 全连接层
        x = self.fc(x)
        
        return x
    
    def get_feature_dim(self) -> int:
        """获取输出特征维度"""
        return self.feature_dim

