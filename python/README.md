# SCAI Python 训练框架

血战到底麻将 AI 的 Python 训练框架，包含神经网络模型、训练循环和自对弈系统。

## 目录结构

```
python/
├── scai/
│   ├── __init__.py
│   ├── models/              # 神经网络模型
│   │   ├── __init__.py
│   │   ├── dual_resnet.py   # Dual-ResNet 完整模型
│   │   ├── backbone.py      # ResNet 骨干网络
│   │   ├── policy_head.py   # 策略头
│   │   └── value_head.py    # 价值头
│   ├── env/                 # 环境相关（待实现）
│   ├── training/            # 训练相关（待实现）
│   └── selfplay/            # 自对弈相关（待实现）
├── requirements.txt
└── README.md
```

## 安装

1. 安装 Python 依赖：
```bash
cd python
pip install -r requirements.txt
```

2. 构建 Rust 扩展（需要先安装 maturin）：
```bash
cd ../rust
maturin develop
```

## 模型架构

### Dual-ResNet

完整的双头网络架构：

- **Backbone**：20+ 层 ResNet，提取游戏状态特征
- **Policy Head**：输出动作概率分布（434 维）
- **Value Head**：输出期望收益分数（1 维）

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

# 输入：游戏状态张量 (batch_size, 64, 4, 9)
state = torch.randn(32, 64, 4, 9)
action_mask = torch.ones(32, 434)  # 动作掩码

# 前向传播
policy, value = model(state, action_mask)

# policy: (32, 434) - 动作概率分布
# value: (32, 1) - 期望收益分数
```

## 开发状态

- ✅ **模型架构**：已实现
  - ✅ ResNet 骨干网络（20+ 层）
  - ✅ Policy Head（策略头）
  - ✅ Value Head（价值头）
  - ✅ Dual-ResNet（完整模型）

- ⏳ **训练循环**：待实现
- ⏳ **自对弈系统**：待实现
- ⏳ **环境封装**：待实现

