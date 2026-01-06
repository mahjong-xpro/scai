# SCAI Python 训练框架

血战到底麻将 AI 的 Python 训练框架，包含神经网络模型、训练循环和自对弈系统。

## 目录结构

```
python/
├── scai/
│   ├── __init__.py
│   ├── models/              # 神经网络模型
│   │   ├── dual_resnet.py   # Dual-ResNet 完整模型
│   │   ├── backbone.py      # ResNet 骨干网络
│   │   ├── policy_head.py   # 策略头
│   │   └── value_head.py    # 价值头
│   ├── training/            # 训练相关
│   │   ├── ppo.py           # PPO 算法
│   │   ├── trainer.py       # 训练器
│   │   ├── evaluator.py     # 评估器
│   │   ├── reward_shaping.py # 奖励函数
│   │   ├── buffer.py        # 经验回放缓冲区
│   │   ├── adversarial.py   # 对抗训练
│   │   └── hyperparameter_search.py # 超参数搜索
│   ├── selfplay/            # 自对弈系统
│   │   ├── worker.py        # Ray Worker
│   │   ├── collector.py     # 数据收集器
│   │   ├── opponent_pool.py # 对手池
│   │   └── feeding_games.py # 喂牌机制
│   ├── search/              # 搜索算法
│   │   └── ismcts.py        # ISMCTS 搜索
│   ├── coach/               # 课程学习
│   │   ├── curriculum.py   # 课程规划
│   │   ├── document_generator.py # 文档生成
│   │   └── automation.py   # 自动化
│   └── utils/               # 工具类
│       ├── checkpoint.py    # 检查点管理
│       ├── logger.py        # 日志系统
│       ├── data_validator.py # 数据验证
│       └── data_augmentation.py # 数据增强
├── train.py                 # 主训练脚本
├── config.yaml              # 配置文件
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

- ✅ **训练循环**：已实现
  - ✅ PPO 算法实现
  - ✅ 训练器（Trainer）
  - ✅ 主训练脚本（train.py）
  - ✅ 检查点管理
  - ✅ 日志系统

- ✅ **自对弈系统**：已实现
  - ✅ Ray 分布式 Worker
  - ✅ 数据收集器（DataCollector）
  - ✅ 经验回放缓冲区（ReplayBuffer）
  - ✅ 对手池系统（OpponentPool）
  - ✅ 喂牌机制（FeedingGames）

- ✅ **训练支持系统**：已实现
  - ✅ 评估器（Evaluator）和 Elo 评分
  - ✅ 奖励函数（RewardShaping）
  - ✅ 课程学习（CurriculumLearning）
  - ✅ 数据验证（DataValidator）
  - ✅ 数据增强（DataAugmentation）

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 编译 Rust 扩展
cd ../rust
maturin develop
cd ../python
```

### 2. 配置训练

编辑 `config.yaml` 文件，配置训练参数。

### 3. 启动训练

```bash
python train.py --config config.yaml
```

## 文档

📚 **完整文档请查看 [docs/README.md](../docs/README.md)**

主要文档：
- [训练指南](../docs/training/TRAINING_GUIDE.md) - 完整的训练流程
- [课程学习](../docs/training/CURRICULUM_LEARNING.md) - 分阶段训练策略
- [功能特性](../docs/features/) - 各功能模块详细说明

