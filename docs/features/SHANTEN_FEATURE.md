# 向听数特征使用指南

## 概述

向听数（Shanten Number）是麻将中一个重要的概念，表示当前手牌距离听牌还需要多少步。在初期训练阶段，向听数可以帮助AI更好地理解手牌质量，学习"做牌"策略。

## 向听数定义

- **0**: 已听牌（差1张就能胡牌）
- **1**: 一向听（差1张牌听牌）
- **2**: 二向听（差2张牌听牌）
- **3+**: 三向听及以上

## 实现位置

### 1. Rust端计算 (`rust/src/game/shanten.rs`)

```rust
use crate::game::shanten::ShantenCalculator;

let shanten = ShantenCalculator::calculate_shanten(&hand, &melds);
```

### 2. Python绑定 (`rust/src/python/game_state.rs`)

```python
import scai_engine

state = engine.state
shanten = state.get_player_shanten(player_id)  # 获取指定玩家的向听数
```

### 3. 观察张量特征 (`rust/src/python/tensor.rs`)

- **Plane 43-46**: 每个玩家的向听数（归一化到 [0, 1]）
  - Plane 43: 玩家0的向听数
  - Plane 44: 玩家1的向听数
  - Plane 45: 玩家2的向听数
  - Plane 46: 玩家3的向听数
  - 归一化公式：`shanten / 8.0`（0表示已听牌，1表示八向听）

### 4. 奖励函数 (`python/scai/training/reward_shaping.py`)

```python
from scai.training.reward_shaping import RewardShaping

reward_shaping = RewardShaping(
    shanten_reward_weight=0.05,  # 向听数奖励权重
    use_shanten_reward=True,     # 启用向听数奖励（初期阶段）
)

# 计算奖励时传入向听数
reward = reward_shaping.compute_step_reward(
    is_ready=False,
    is_hu=False,
    is_flower_pig=False,
    shanten=current_shanten,        # 当前向听数
    previous_shanten=prev_shanten,  # 上一步的向听数
)
```

## 奖励机制

### 向听数改善奖励

- **向听数减少**：给予奖励（`shanten_improvement * shanten_reward_weight`）
  - 例如：从3向听改善到2向听，奖励 = `1 * 0.05 = 0.05`
- **达到听牌**：给予额外奖励（`ready_reward * 0.5`）

### 配置建议

**初期阶段（定缺、学胡、基础）**：
```python
RewardShaping(
    shanten_reward_weight=0.05,  # 向听数奖励权重较高
    use_shanten_reward=True,      # 启用向听数奖励
)
```

**进阶阶段（防御、高级、专家）**：
```python
RewardShaping(
    shanten_reward_weight=0.01,  # 向听数奖励权重降低
    use_shanten_reward=False,     # 可以禁用向听数奖励，主要依赖最终得分
)
```

## 在Worker中使用

在 `python/scai/selfplay/worker.py` 中，可以在收集轨迹时记录向听数：

```python
# 获取当前玩家的向听数
state = engine.state
current_shanten = state.get_player_shanten(current_player)

# 计算奖励时使用
reward = self.reward_shaping.compute_step_reward(
    is_ready=state.is_player_ready(current_player),
    is_hu=False,
    is_flower_pig=False,
    shanten=current_shanten,
    previous_shanten=previous_shanten,  # 需要记录上一步的向听数
)
```

## 在喂牌机制中使用

可以在喂牌机制中生成特定向听数的手牌：

```python
from scai.selfplay.feeding_games import FeedingGameGenerator

generator = FeedingGameGenerator()

# 生成一向听的手牌（更容易学习）
feeding_hand = generator.generate_feeding_hand(
    target_player_id=0,
    win_type='basic',
    target_shanten=1,  # 目标向听数
)
```

## 优势

1. **初期学习加速**：向听数奖励帮助AI更快理解手牌质量
2. **渐进式学习**：从高向听数到低向听数，逐步改善手牌
3. **策略理解**：帮助AI学习"做牌"策略，而不是盲目打牌
4. **特征丰富**：观察张量中包含向听数，AI可以直接感知手牌质量

## 注意事项

1. **计算性能**：向听数计算可能较慢，建议使用简化算法（`calculate_shanten`）而不是精确算法（`calculate_shanten_precise`）
2. **奖励权重**：向听数奖励权重不宜过高，避免AI过度优化向听数而忽略其他策略
3. **阶段调整**：在进阶阶段可以降低或禁用向听数奖励，主要依赖最终得分

## 总结

向听数特征在初期训练阶段非常有用，可以帮助AI：
- ✅ 理解手牌质量
- ✅ 学习"做牌"策略
- ✅ 更快达到听牌状态
- ✅ 在观察张量中直接感知手牌质量

建议在**定缺阶段**、**学胡阶段**和**基础阶段**启用向听数奖励，在进阶阶段逐步降低权重或禁用。

