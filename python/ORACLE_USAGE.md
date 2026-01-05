# Oracle 特征使用指南

## 概述

Oracle 特征为训练阶段提供"上帝视角"（完美信息），包括对手的暗牌和牌堆余牌分布。这些特征仅在训练时使用，可以加速模型收敛。

## 使用方法

### 1. 训练时启用 Oracle 特征

```python
import scai_engine
import numpy as np

# 创建游戏状态
game_state = scai_engine.PyGameState()

# 计算牌堆余牌分布（108 个浮点数）
# 每个值表示该牌在牌堆中剩余的数量（0-4）
wall_tile_distribution = calculate_wall_distribution(game_state)

# 转换为 Tensor（启用 Oracle 特征）
tensor = scai_engine.state_to_tensor(
    game_state,
    player_id=0,
    remaining_tiles=50,
    use_oracle=True,  # 启用 Oracle 特征
    wall_tile_distribution=wall_tile_distribution,  # 牌堆余牌分布
)

# 或者使用 PyGameState 的方法
tensor = game_state.to_tensor(
    player_id=0,
    remaining_tiles=50,
    use_oracle=True,
    wall_tile_distribution=wall_tile_distribution,
)
```

### 2. 推理时禁用 Oracle 特征

```python
# 转换为 Tensor（禁用 Oracle 特征）
tensor = scai_engine.state_to_tensor(
    game_state,
    player_id=0,
    remaining_tiles=50,
    use_oracle=False,  # 禁用 Oracle 特征
    wall_tile_distribution=None,  # 不需要牌堆余牌分布
)
```

### 3. 计算牌堆余牌分布

```python
def calculate_wall_distribution(game_state, wall):
    """
    计算牌堆余牌分布
    
    参数：
    - game_state: 游戏状态
    - wall: 牌墙对象（需要从 GameEngine 获取）
    
    返回：
    - wall_distribution: 108 个浮点数，每张牌的剩余数量（0-4）
    """
    # 初始化：每种牌有 4 张
    distribution = [4.0] * 108
    
    # 减去所有玩家的手牌
    for player_id in range(4):
        hand = game_state.get_player_hand(player_id)
        for tile_str, count in hand.items():
            tile_idx = tile_to_index(tile_str)
            if tile_idx < 108:
                distribution[tile_idx] -= count
    
    # 减去所有玩家的副露（碰/杠）
    for player_id in range(4):
        melds = game_state.get_player_melds(player_id)
        for meld in melds:
            tile_idx = tile_to_index(meld['tile'])
            if tile_idx < 108:
                distribution[tile_idx] -= meld['count']
    
    # 减去所有弃牌
    for discard in game_state.discard_history:
        tile_idx = tile_to_index(discard['tile'])
        if tile_idx < 108:
            distribution[tile_idx] -= 1.0
    
    # 确保值在 [0, 4] 范围内
    distribution = [max(0.0, min(4.0, count)) for count in distribution]
    
    return distribution
```

## 特征平面说明

### Oracle 特征平面

| 平面范围 | 特征 | 说明 |
|---------|------|------|
| 13-24 | 对手暗牌 | 显示对手的手牌（仅 Oracle 模式） |
| 46-55 | 牌堆余牌分布 | 显示每张牌在牌堆中剩余的数量（仅 Oracle 模式） |

### 非 Oracle 特征平面

| 平面范围 | 特征 | 说明 |
|---------|------|------|
| 0-3 | 自身手牌 | 总是可见 |
| 4-10 | 弃牌 | 总是可见 |
| 11 | 剩余牌数 | 总是可见 |
| 12 | 定缺掩码 | 总是可见 |
| 25-45 | 其他信息 | 总是可见 |

## 训练流程建议

### 阶段 1：Oracle 引导训练（前 50% 训练时间）

- 启用 Oracle 特征：`use_oracle=True`
- 模型在完美信息下学习最优策略
- 加速收敛，理解游戏规则

### 阶段 2：混合训练（中间 30% 训练时间）

- 随机启用/禁用 Oracle 特征（50% 概率）
- 模型逐步适应不完美信息
- 策略迁移

### 阶段 3：不完美信息训练（最后 20% 训练时间）

- 完全禁用 Oracle 特征：`use_oracle=False`
- 模型在不完美信息下做出决策
- 准备推理部署

## 注意事项

1. **推理时必须禁用**：实际对局时，`use_oracle` 必须设置为 `False`
2. **数据一致性**：确保训练和推理时的特征编码一致
3. **模型容量**：Oracle 特征会增加输入维度，需要确保模型有足够的容量
4. **过拟合风险**：过度依赖 Oracle 特征可能导致模型无法适应不完美信息

## 示例代码

完整示例请参考 `python/examples/oracle_training.py`（待实现）

