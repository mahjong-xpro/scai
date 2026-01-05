# 模型架构文档 (Model Architecture)

## 概述

本文档详细说明 Dual-ResNet 模型架构的实现，包括 ResNet 骨干网络和双头输出设计。

## 架构设计

### Dual-ResNet 模型

完整的双头网络架构，包含三个主要组件：

1. **ResNet Backbone（骨干网络）**：20+ 层残差网络，提取游戏状态特征
2. **Policy Head（策略头）**：输出动作概率分布（434 维）
3. **Value Head（价值头）**：输出期望收益分数（1 维）

---

## 1. ResNet 骨干网络 (Backbone)

### 架构设计

**文件**：`python/scai/models/backbone.py`

**类**：`ResNetBackbone`

**结构**：
- **初始卷积层**：将输入 (64, 4, 9) 转换为特征图
- **20 个残差块**：逐步提取深层特征
  - 每 5 个块为一组
  - 每组逐步增加通道数（128 → 256 → 512）
  - 第一组第一个块使用 stride=1，后续组第一个块使用 stride=2 进行下采样
- **全局平均池化**：将特征图压缩为向量
- **全连接层**：输出特征向量（512 维）

**残差块结构**：
```
输入 → Conv2d → BatchNorm → ReLU → Conv2d → BatchNorm → 残差连接 → ReLU → 输出
```

### 参数配置

- `input_channels`: 64（特征平面数）
- `num_blocks`: 20（残差块数量）
- `base_channels`: 128（基础通道数）
- `feature_dim`: 512（输出特征维度）

### 输入输出

- **输入**：`(batch_size, 64, 4, 9)` - 游戏状态张量
- **输出**：`(batch_size, 512)` - 特征向量

---

## 2. 策略头 (Policy Head)

### 架构设计

**文件**：`python/scai/models/policy_head.py`

**类**：`PolicyHead`

**结构**：
- **全连接层 1**：512 → 256
- **Dropout**：0.1（正则化）
- **全连接层 2**：256 → 256
- **Dropout**：0.1（正则化）
- **全连接层 3**：256 → 434（动作空间大小）
- **Softmax**：转换为概率分布

**动作掩码支持**：
- 如果提供 `action_mask`，将非法动作的 logits 设为负无穷
- 确保 Softmax 后非法动作的概率为 0

### 动作空间定义

- **索引 0-107**：出牌动作（108 种牌）
- **索引 108-215**：碰牌动作（108 种牌）
- **索引 216-323**：杠牌动作（108 种牌）
- **索引 324-431**：胡牌动作（108 种牌）
- **索引 432**：摸牌动作
- **索引 433**：过（放弃）动作

**总计**：434 个动作

### 输入输出

- **输入**：
  - `features`: `(batch_size, 512)` - 特征向量
  - `action_mask`: `(batch_size, 434)` - 动作掩码（可选）
- **输出**：`(batch_size, 434)` - 动作概率分布

---

## 3. 价值头 (Value Head)

### 架构设计

**文件**：`python/scai/models/value_head.py`

**类**：`ValueHead`

**结构**：
- **全连接层 1**：512 → 256
- **Dropout**：0.1（正则化）
- **全连接层 2**：256 → 256
- **Dropout**：0.1（正则化）
- **全连接层 3**：256 → 1（单个标量值）

### 价值定义

在血战到底中，价值头预测的是"最终总分"的回归值，包括：

- 胡牌得分
- 刮风下雨（杠钱）
- 查大叫/查花猪的奖惩
- 最终结算得分

### 输入输出

- **输入**：`(batch_size, 512)` - 特征向量
- **输出**：`(batch_size, 1)` - 期望收益分数

---

## 4. 完整模型 (Dual-ResNet)

### 架构设计

**文件**：`python/scai/models/dual_resnet.py`

**类**：`DualResNet`

**结构**：
```
输入 (batch_size, 64, 4, 9)
    ↓
ResNet Backbone
    ↓
特征向量 (batch_size, 512)
    ↓
    ├─→ Policy Head → 动作概率 (batch_size, 434)
    └─→ Value Head → 期望收益 (batch_size, 1)
```

### 使用示例

```python
import torch
from scai.models import DualResNet

# 创建模型
model = DualResNet(
    input_channels=64,
    num_blocks=20,
    base_channels=128,
    feature_dim=512,
    action_space_size=434,
)

# 输入
state = torch.randn(32, 64, 4, 9)  # 游戏状态
action_mask = torch.ones(32, 434)  # 动作掩码

# 前向传播
policy, value = model(state, action_mask)

# policy: (32, 434) - 动作概率分布
# value: (32, 1) - 期望收益分数
```

### 模型方法

- `forward(state, action_mask)`: 完整前向传播，返回策略和价值
- `get_policy(state, action_mask)`: 仅获取策略
- `get_value(state)`: 仅获取价值
- `get_model_info()`: 获取模型信息（参数量等）

---

## 模型参数统计

### 默认配置下的参数量

- **ResNet Backbone**：约 2-3M 参数
- **Policy Head**：约 200K 参数
- **Value Head**：约 130K 参数
- **总计**：约 2.5-3.5M 参数

### 可配置参数

- `num_blocks`: 残差块数量（默认 20，可调整）
- `base_channels`: 基础通道数（默认 128，可调整）
- `feature_dim`: 特征维度（默认 512，可调整）
- `hidden_dim`: 隐藏层维度（默认 256，可调整）

---

## 实现状态

- ✅ **ResNet 骨干网络**：已实现（20+ 层）
- ✅ **策略头**：已实现（434 维输出）
- ✅ **价值头**：已实现（1 维输出）
- ✅ **Dual-ResNet**：已实现（完整模型）

所有组件已完整实现，可用于强化学习训练。

