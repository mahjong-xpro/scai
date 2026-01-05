# 强化学习训练循环文档 (Training Loop Documentation)

## 概述

本文档详细说明强化学习训练循环的实现，包括分布式框架、PPO 算法、奖励函数和评估系统。

---

## 1. 分布式框架配置

### Ray Worker 实现

**文件**：`python/scai/selfplay/worker.py`

**功能**：
- 使用 Ray 实现分布式自对弈
- 支持数百个 Rust 实例同时生成轨迹
- 每个 Worker 运行多个游戏实例

**使用示例**：
```python
import ray
from scai.selfplay import SelfPlayWorker, create_workers, collect_trajectories_parallel

# 初始化 Ray
ray.init()

# 创建 Worker
workers = create_workers(
    num_workers=100,
    num_games_per_worker=10,
    use_oracle=True,
)

# 并行收集轨迹
trajectories = collect_trajectories_parallel(
    workers,
    model_state_dict,
)
```

---

## 2. PPO 算法核心

### 经验回放池 (Replay Buffer)

**文件**：`python/scai/training/buffer.py`

**功能**：
- 存储游戏轨迹（Trajectories）
- 支持批量采样
- 计算优势函数（GAE）

**使用示例**：
```python
from scai.training import ReplayBuffer

buffer = ReplayBuffer(capacity=100000)

# 添加数据
buffer.add(state, action, reward, value, log_prob, done, action_mask)

# 完成轨迹
buffer.finish_trajectory()

# 计算优势函数
buffer.compute_advantages(gamma=0.99, gae_lambda=0.95)

# 采样批次
batch = buffer.sample(batch_size=4096)
```

### PPO 算法实现

**文件**：`python/scai/training/ppo.py`

**功能**：
- 策略更新
- 价值函数更新
- 策略裁剪（Clipping）
- 优势函数归一化

**使用示例**：
```python
from scai.training import PPO
from scai.models import DualResNet

model = DualResNet()
ppo = PPO(
    model=model,
    learning_rate=3e-4,
    clip_epsilon=0.2,
    value_coef=0.5,
    entropy_coef=0.01,
)

# 更新策略
losses = ppo.update(batch, num_epochs=10)

# 选择动作
action, log_prob, value = ppo.get_action(state, action_mask)
```

---

## 3. 奖励函数初调

**文件**：`python/scai/training/reward_shaping.py`

**功能**：
- 引导奖惩（听牌奖励、花猪惩罚）
- 最终奖励（局末真实得分）

**使用示例**：
```python
from scai.training import RewardShaping

reward_shaping = RewardShaping(
    ready_reward=0.1,
    hu_reward=1.0,
    flower_pig_penalty=-5.0,
    final_score_weight=1.0,
)

# 计算单步奖励
step_reward = reward_shaping.compute_step_reward(
    is_ready=True,
    is_hu=False,
    is_flower_pig=False,
)

# 计算最终奖励
final_reward = reward_shaping.compute_final_reward(
    final_score=100.0,
    is_winner=True,
)

# 更新奖励列表
updated_rewards = reward_shaping.update_rewards(
    rewards,
    final_score=100.0,
    is_winner=True,
)
```

---

## 4. 评估系统

### Elo 评分机制

**文件**：`python/scai/training/evaluator.py`

**功能**：
- Elo 评分系统
- 模型评估
- 模型比较
- 最佳模型选择

**使用示例**：
```python
from scai.training import Evaluator

evaluator = Evaluator(
    checkpoint_dir='./checkpoints',
    elo_threshold=0.55,
)

# 评估模型
stats = evaluator.evaluate_model(model, model_id='model_v1', num_games=100)

# 比较模型
comparison = evaluator.compare_models(
    model_a, model_b,
    model_a_id='model_v1',
    model_b_id='model_v2',
    num_games=100,
)

# 获取最佳模型
best_model_id = evaluator.get_best_model_id()
```

### Checkpoint 管理

**文件**：`python/scai/utils/checkpoint.py`

**功能**：
- 保存和加载模型检查点
- 管理 Checkpoint 历史
- 获取最新 Checkpoint

**使用示例**：
```python
from scai.utils import CheckpointManager

manager = CheckpointManager(checkpoint_dir='./checkpoints')

# 保存 Checkpoint
checkpoint_path = manager.save_checkpoint(
    model, optimizer, iteration=1000, training_stats=stats
)

# 加载 Checkpoint
checkpoint = manager.load_checkpoint(checkpoint_path, model, optimizer)

# 获取最新 Checkpoint
latest_path = manager.get_latest_checkpoint()
```

---

## 5. 完整训练流程

### 训练器 (Trainer)

**文件**：`python/scai/training/trainer.py`

**功能**：
- 管理训练循环
- 协调各个组件
- 自动保存 Checkpoint

**使用示例**：
```python
from scai.training import Trainer, ReplayBuffer, PPO, RewardShaping
from scai.models import DualResNet

# 初始化组件
model = DualResNet()
buffer = ReplayBuffer()
ppo = PPO(model)
reward_shaping = RewardShaping()
trainer = Trainer(model, buffer, ppo, reward_shaping)

# 训练
trainer.train(
    num_iterations=1000,
    batch_size=4096,
    num_epochs=10,
    save_interval=100,
)
```

### 数据收集器 (Data Collector)

**文件**：`python/scai/selfplay/collector.py`

**功能**：
- 收集自对弈数据
- 管理轨迹数据
- 预处理和添加到缓冲区

**使用示例**：
```python
from scai.selfplay import DataCollector
from scai.training import ReplayBuffer, RewardShaping

buffer = ReplayBuffer()
reward_shaping = RewardShaping()
collector = DataCollector(
    buffer=buffer,
    reward_shaping=reward_shaping,
    num_workers=100,
    num_games_per_worker=10,
    use_oracle=True,
)

# 收集数据
stats = collector.collect(model_state_dict)
```

---

## 6. 训练配置

### 推荐配置

```python
# PPO 配置
ppo_config = {
    'learning_rate': 3e-4,
    'clip_epsilon': 0.2,
    'value_coef': 0.5,
    'entropy_coef': 0.01,
    'max_grad_norm': 0.5,
}

# 奖励函数配置
reward_config = {
    'ready_reward': 0.1,
    'hu_reward': 1.0,
    'flower_pig_penalty': -5.0,
    'final_score_weight': 1.0,
}

# 训练配置
training_config = {
    'batch_size': 4096,
    'num_epochs': 10,
    'gamma': 0.99,
    'gae_lambda': 0.95,
    'save_interval': 100,
}

# 自对弈配置
selfplay_config = {
    'num_workers': 100,
    'num_games_per_worker': 10,
    'use_oracle': True,
}
```

---

## 7. 实现状态

- ✅ **分布式框架**：已实现（Ray Worker）
- ✅ **PPO 算法**：已实现（策略更新、价值更新、裁剪）
- ✅ **经验回放池**：已实现（缓冲区、GAE）
- ✅ **奖励函数**：已实现（引导奖惩、最终奖励）
- ✅ **评估系统**：已实现（Elo 评分、Checkpoint 管理）
- ✅ **训练器**：已实现（训练循环管理）
- ✅ **数据收集器**：已实现（自对弈数据收集）

所有组件已完整实现，可用于强化学习训练。

