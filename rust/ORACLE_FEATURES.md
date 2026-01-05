# Oracle 特征设计文档 (Oracle Features Design)

## 概述

Oracle 特征是指在训练阶段为 AI 提供"上帝视角"（完美信息）的特征，包括对手的暗牌和牌堆余牌分布。这些特征仅在训练时使用，可以加速模型收敛。在推理（实际对局）时，这些特征会被移除。

## 设计原理

### 为什么需要 Oracle 特征？

在麻将游戏中，玩家只能看到：
- 自己的手牌
- 所有玩家的明牌（碰/杠）
- 所有玩家的弃牌

但看不到：
- 对手的暗牌（手牌）
- 牌堆中剩余的具体牌

这导致模型在训练初期非常困惑，难以学习有效的策略。

### Oracle 引导训练

通过提供"上帝视角"特征，模型可以：
1. **理解因果关系**：知道"为什么刚才那张牌会点炮"
2. **学习最优策略**：在完美信息下学习最佳决策
3. **加速收敛**：更快地理解游戏规则和策略

训练完成后，在推理时移除这些特征，模型需要基于不完美信息做出决策。

---

## 实现细节

### Oracle 特征平面

**文件**：`rust/src/python/tensor.rs` - `state_to_tensor()` 函数

#### 1. 对手暗牌（手牌）

**平面范围**：Plane 13-24

**编码方式**：
- 每个对手占用 4 个平面（Plane 13-16, 17-20, 21-24）
- 每个平面表示该对手手牌中该牌的数量（1-4 张）
- One-hot 编码

**实现**：
```rust
if use_oracle {
    // 填充 Plane 13-24 显示对手手牌
    for other_player_id in 0..4 {
        if other_player_id == player_id {
            continue;
        }
        for count in 1..=4 {
            // 记录对手手牌中数量为 count 的牌
            // ...
        }
    }
}
```

**说明**：
- 仅在 `use_oracle=true` 时填充
- 如果 `use_oracle=false`，这些平面保持为 0

#### 2. 牌堆余牌分布

**平面范围**：Plane 46-55

**编码方式**：
- Plane 46-50: One-hot 编码，表示每张牌在牌堆中剩余的数量（0-4 张）
- Plane 51-55: 归一化值，表示每张牌在牌堆中剩余的数量（0.0-1.0）

**实现**：
```rust
if use_oracle {
    if let Some(wall_dist) = wall_tile_distribution {
        // wall_dist: 108 个浮点数，每张牌的剩余数量（0-4）
        // 填充 Plane 46-55
        // ...
    }
}
```

**参数**：
- `wall_tile_distribution`: `Vec<f32>`，长度为 108
  - 索引对应：`suit_idx * 9 + rank_idx`
  - 值范围：0.0-4.0，表示该牌在牌堆中剩余的数量

---

## 使用方法

### Rust 端

```rust
use scai_engine::python::tensor::state_to_tensor;

// 训练时（使用 Oracle 特征）
let tensor = state_to_tensor(
    &game_state,
    player_id,
    Some(remaining_tiles),
    Some(true),  // use_oracle = true
    Some(wall_tile_distribution),  // 牌堆余牌分布
    py,
)?;

// 推理时（不使用 Oracle 特征）
let tensor = state_to_tensor(
    &game_state,
    player_id,
    Some(remaining_tiles),
    Some(false),  // use_oracle = false
    None,  // 不需要牌堆余牌分布
    py,
)?;
```

### Python 端

```python
import scai_engine

# 训练时
tensor = scai_engine.state_to_tensor(
    game_state,
    player_id=0,
    remaining_tiles=50,
    use_oracle=True,  # 启用 Oracle 特征
    wall_tile_distribution=wall_dist,  # 108 个浮点数
)

# 推理时
tensor = scai_engine.state_to_tensor(
    game_state,
    player_id=0,
    remaining_tiles=50,
    use_oracle=False,  # 禁用 Oracle 特征
    wall_tile_distribution=None,
)
```

---

## 特征平面分配总结

| 平面范围 | 特征类型 | Oracle 模式 | 说明 |
|---------|---------|------------|------|
| 0-3 | 自身手牌 | 总是可见 | One-hot 编码 |
| 4-10 | 弃牌 | 总是可见 | 三个对手的弃牌 |
| 11 | 剩余牌数 | 总是可见 | 归一化后的剩余牌数 |
| 12 | 定缺掩码 | 总是可见 | 各家定缺色 |
| 13-24 | **对手暗牌** | **仅 Oracle** | 对手的手牌（训练时可见） |
| 25-28 | 副露 | 总是可见 | 已碰/杠的牌 |
| 29-32 | 玩家状态 | 总是可见 | 是否离场 |
| 33-36 | 听牌状态 | 总是可见 | 是否听牌 |
| 37-45 | 其他信息 | 总是可见 | 回合信息、当前玩家等 |
| 46-55 | **牌堆余牌分布** | **仅 Oracle** | 每张牌在牌堆中剩余的数量（训练时可见） |
| 56-63 | 保留 | - | 用于未来扩展 |

---

## 训练流程

### 阶段 1：Oracle 引导训练

1. **启用 Oracle 特征**：`use_oracle=true`
2. **提供完美信息**：包括对手暗牌和牌堆余牌分布
3. **模型学习**：在完美信息下学习最优策略
4. **加速收敛**：更快理解游戏规则和因果关系

### 阶段 2：不完美信息训练

1. **逐步禁用 Oracle**：`use_oracle=false`
2. **模型适应**：学习在不完美信息下做出决策
3. **策略迁移**：将完美信息下的策略迁移到不完美信息

### 阶段 3：推理部署

1. **完全禁用 Oracle**：`use_oracle=false`
2. **实际对局**：模型基于不完美信息做出决策
3. **性能评估**：评估模型在实际对局中的表现

---

## 注意事项

1. **仅训练时使用**：Oracle 特征必须在推理时禁用
2. **数据一致性**：确保训练和推理时的特征编码一致
3. **模型容量**：Oracle 特征会增加输入维度，需要确保模型有足够的容量
4. **过拟合风险**：过度依赖 Oracle 特征可能导致模型无法适应不完美信息

---

## 实现状态

- ✅ **对手暗牌特征**：已实现（Plane 13-24）
- ✅ **牌堆余牌分布**：已实现（Plane 46-55）
- ✅ **Oracle 模式控制**：已实现（`use_oracle` 参数）
- ✅ **Python 接口**：已实现（`state_to_tensor` 函数）

所有 Oracle 特征已完整实现，可用于训练阶段的引导学习。

