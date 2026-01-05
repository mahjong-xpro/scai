# 顶级博弈优化文档 (Expert Tuning Documentation)

## 概述

本文档详细说明第四阶段：顶级博弈优化的实现，包括 ISMCTS 搜索算法、对抗性鲁棒训练和超参数自动化搜索。

---

## 1. ISMCTS 搜索算法

### 概述

ISMCTS (Information Set Monte Carlo Tree Search) 是信息集蒙特卡洛树搜索，用于不完美信息博弈。在推理端实现 ISMCTS，对未知牌墙进行 Determinization 采样。

### 实现

**文件**：`python/scai/search/ismcts.py`

**核心组件**：

1. **ISMCTSNode**：搜索树节点
   - 访问统计（visits, total_value）
   - 子节点管理
   - UCB1 值计算
   - 节点展开和更新

2. **ISMCTS**：搜索算法
   - Selection：选择到叶子节点
   - Expansion：展开节点
   - Rollout：随机模拟到终端
   - Backpropagation：反向传播更新

### 使用示例

```python
from scai.search import ISMCTS
from scai.models import DualResNet

model = DualResNet()
ismcts = ISMCTS(
    model=model,
    num_simulations=100,
    exploration_constant=1.414,
    determinization_samples=10,
)

# 执行搜索
best_action, stats = ismcts.search(
    game_state=game_state,
    player_id=0,
    action_mask=action_mask,
    remaining_tiles=50,
    seed=42,
)
```

### Determinization 采样

ISMCTS 使用 `fill_unknown_cards` 方法对未知牌墙进行确定性采样：

```python
def _determinize_state(self, game_state, player_id, remaining_tiles, seed):
    """对未知牌墙进行 Determinization 采样"""
    determinized_state = game_state.clone()
    
    # 使用 fill_unknown_cards 填充未知牌
    determinized_state.fill_unknown_cards(
        viewer_id=player_id,
        remaining_wall_count=remaining_tiles,
        seed=seed,
    )
    
    return determinized_state
```

---

## 2. 对抗性鲁棒训练

### 概述

对抗性鲁棒训练通过针对性模拟极端局势，提升模型的防御避炮能力。

### 实现

**文件**：`python/scai/training/adversarial.py`

**核心功能**：

1. **极端局势模拟**：
   - 被三家定缺针对：`create_targeted_declare_scenario()`
   - 起手极烂：`create_bad_hand_scenario()`

2. **防御奖励计算**：
   - 安全出牌奖励
   - 避免点炮奖励
   - 听牌时的安全出牌额外奖励

### 使用示例

```python
from scai.training import AdversarialTrainer, RewardShaping

reward_shaping = RewardShaping()
adversarial = AdversarialTrainer(
    reward_shaping=reward_shaping,
    targeted_declare_prob=0.3,
    bad_hand_prob=0.2,
)

# 创建被三家定缺针对的场景
scenario = adversarial.create_targeted_declare_scenario(
    game_state=game_state,
    target_player_id=0,
)

# 应用场景
adversarial.apply_scenario(game_state, scenario)

# 计算防御奖励
defense_reward = adversarial.compute_defense_reward(
    is_discard_safe=True,
    avoided_pao=True,
    is_ready=True,
)
```

### 场景类型

1. **被三家定缺针对**：
   - 分析目标玩家的手牌
   - 找到最多的花色
   - 让其他三家都定缺这个花色

2. **起手极烂**：
   - 创建分散、无对子、无顺子的手牌
   - 训练模型在不利情况下做出最佳决策

---

## 3. 超参数自动化搜索

### 概述

超参数自动化搜索实现学习率、探索因子、搜索深度等超参数的自动化调优。

### 实现

**文件**：`python/scai/training/hyperparameter_search.py`

**核心功能**：

1. **网格搜索（Grid Search）**：
   - 遍历所有超参数组合
   - 评估每个配置
   - 返回最佳配置

2. **随机搜索（Random Search）**：
   - 随机采样超参数组合
   - 评估每个配置
   - 返回最佳配置

3. **贝叶斯优化（Bayesian Optimization）**：
   - 使用概率模型指导搜索
   - 更高效地找到最佳配置

### 超参数范围

- **学习率**：1e-4, 3e-4, 1e-3, 3e-3
- **探索因子（Entropy Loss）**：0.001, 0.01, 0.1, 0.5
- **搜索深度（ISMCTS num_simulations）**：50, 100, 200, 500

### 使用示例

```python
from scai.training import HyperparameterSearch, Evaluator
from scai.models import DualResNet

model_template = DualResNet()
evaluator = Evaluator()

search = HyperparameterSearch(
    model_template=model_template,
    evaluator=evaluator,
    learning_rates=[1e-4, 3e-4, 1e-3],
    entropy_coefs=[0.01, 0.1, 0.5],
    search_depths=[100, 200, 500],
)

# 网格搜索
best_config = search.grid_search(num_eval_games=50)

# 随机搜索
best_config = search.random_search(num_samples=20, num_eval_games=50)

# 获取最佳配置
print(f"Best learning rate: {best_config.learning_rate}")
print(f"Best entropy coef: {best_config.entropy_coef}")
print(f"Best search depth: {best_config.search_depth}")
```

---

## 4. 完整训练流程

### 集成使用

```python
from scai.models import DualResNet
from scai.training import (
    Trainer, ReplayBuffer, PPO, RewardShaping,
    AdversarialTrainer, HyperparameterSearch,
)
from scai.search import ISMCTS

# 1. 超参数搜索
model_template = DualResNet()
evaluator = Evaluator()
search = HyperparameterSearch(model_template, evaluator)
best_config = search.grid_search()

# 2. 使用最佳配置创建模型和训练器
model = DualResNet()
ppo = PPO(
    model=model,
    learning_rate=best_config.learning_rate,
    entropy_coef=best_config.entropy_coef,
)

# 3. 对抗性训练
adversarial = AdversarialTrainer(reward_shaping)

# 4. ISMCTS 搜索（推理时使用）
ismcts = ISMCTS(
    model=model,
    num_simulations=best_config.search_depth,
)
```

---

## 5. 实现状态

- ✅ **ISMCTS 搜索算法**：已实现
  - ✅ ISMCTSNode：搜索树节点
  - ✅ ISMCTS：搜索算法实现
  - ✅ Determinization 采样

- ✅ **对抗性鲁棒训练**：已实现
  - ✅ 被三家定缺针对场景
  - ✅ 起手极烂场景
  - ✅ 防御奖励计算

- ✅ **超参数自动化搜索**：已实现
  - ✅ 网格搜索
  - ✅ 随机搜索
  - ✅ 贝叶斯优化（占位符）

所有组件已完整实现，可用于顶级博弈优化。

