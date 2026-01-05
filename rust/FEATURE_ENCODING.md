# 特征编码设计文档 (Feature Encoding Design)

## 概述

本文档详细说明 AI 训练中使用的特征编码设计，所有特征都在 `state_to_tensor()` 函数中实现。

## 特征编码结构

特征编码使用 4D Tensor 格式：**64 × 4 × 9**
- **64 个特征平面**：不同的特征类型
- **4 个玩家**：每个玩家的信息
- **9 种牌**：每种花色的 1-9 号牌

---

## 基础层特征 (Basic Features)

### ✅ 1. 手牌（4 层）

**实现位置**：Plane 0-3

**编码方式**：
- Plane 0: 手牌中数量为 1 的牌
- Plane 1: 手牌中数量为 2 的牌
- Plane 2: 手牌中数量为 3 的牌
- Plane 3: 手牌中数量为 4 的牌

**代码位置**：`rust/src/python/tensor.rs` 第 54-64 行

```rust
// Plane 0-3: 自身手牌（One-hot 表示 1-4 张）
for count in 1..=4 {
    let player = &game_state.players[player_id as usize];
    for (tile, &tile_count) in player.hand.tiles_map() {
        if tile_count == count {
            let (suit_idx, rank_idx) = tile_to_indices(tile);
            data[[(count - 1) as usize, suit_idx, rank_idx]] = 1.0;
        }
    }
}
```

**说明**：使用 One-hot 编码，每个平面表示手牌中该牌的数量。

---

### ✅ 2. 弃牌

**实现位置**：Plane 4-10

**编码方式**：
- Plane 4-5: 对手 1 的弃牌（最近 2 张）
- Plane 6-7: 对手 2 的弃牌（最近 2 张）
- Plane 8-9: 对手 3 的弃牌（最近 2 张）
- Plane 10: 最近一次弃牌（全局视角）

**代码位置**：`rust/src/python/tensor.rs` 第 66-101 行

**说明**：
- 按对手分别记录弃牌，保留顺序信息
- 最近弃牌优先记录
- Plane 10 提供全局视角的最近弃牌信息

---

### ✅ 3. 副露

**实现位置**：Plane 25-28

**编码方式**：
- 每个玩家占用一个平面（Plane 25-28）
- 记录该玩家已碰/杠的牌

**代码位置**：`rust/src/python/tensor.rs` 第 149-162 行

```rust
// 平面 25-28: 已碰/杠的牌（4 个玩家）
for p_id in 0..4 {
    for meld in &game_state.players[p_id].melds {
        let tile = match meld {
            crate::game::scoring::Meld::Triplet { tile } => *tile,
            crate::game::scoring::Meld::Kong { tile, .. } => *tile,
        };
        let (suit_idx, rank_idx) = tile_to_indices(&tile);
        if plane_idx < 64 {
            data[[plane_idx, suit_idx, rank_idx]] = 1.0;
        }
    }
    plane_idx += 1;
}
```

**说明**：
- 碰（Triplet）：3 张相同牌
- 杠（Kong）：4 张相同牌
- 每个玩家的副露信息独立记录

---

## 全局层特征 (Global Features)

### ✅ 1. 剩余牌数

**实现位置**：Plane 11

**编码方式**：
- 将剩余牌数归一化到 [0, 1] 范围
- 公式：`normalized_count = (remaining / 108.0).min(1.0)`
- 所有位置（4 个玩家 × 9 种牌）都填充相同的归一化值

**代码位置**：`rust/src/python/tensor.rs` 第 103-111 行

```rust
// Plane 11: 场上剩余牌堆计数
let remaining = remaining_tiles.unwrap_or(0);
let normalized_count = (remaining as f32 / 108.0).min(1.0);
for suit in 0..3 {
    for rank in 0..9 {
        data[[11, suit, rank]] = normalized_count;
    }
}
```

**说明**：归一化后的剩余牌数，帮助 AI 判断游戏进度。

---

### ✅ 2. 当前局势（谁已胡、谁离场）

**实现位置**：Plane 29-32

**编码方式**：
- Plane 29: 玩家 0 是否离场
- Plane 30: 玩家 1 是否离场
- Plane 31: 玩家 2 是否离场
- Plane 32: 玩家 3 是否离场

**代码位置**：`rust/src/python/tensor.rs` 第 164-176 行

```rust
// 平面 29-32: 玩家状态（是否离场）
for p_id in 0..4 {
    if game_state.players[p_id].is_out {
        for suit in 0..3 {
            for rank in 0..9 {
                if plane_idx < 64 {
                    data[[plane_idx, suit, rank]] = 1.0;
                }
            }
        }
    }
    plane_idx += 1;
}
```

**说明**：
- 如果玩家已离场（`is_out = true`），该玩家的平面全部填充 1.0
- 如果玩家未离场，该玩家的平面全部填充 0.0
- 帮助 AI 了解当前游戏状态和剩余玩家

**额外信息**：
- Plane 33-36: 听牌状态（每个玩家是否听牌）
- Plane 41-44: 当前玩家信息（标记当前回合的玩家）

---

### ✅ 3. 各家定缺色

**实现位置**：Plane 12

**编码方式**：
- 每个玩家占用一个维度（4 个玩家）
- 在该玩家的定缺花色位置标记 1.0

**代码位置**：`rust/src/python/tensor.rs` 第 113-123 行

```rust
// Plane 12: 定缺掩码
for p_id in 0..4 {
    if let Some(declared) = game_state.players[p_id].declared_suit {
        let suit_idx = declared as usize;
        // 在该玩家的定缺花色位置标记
        for rank in 0..9 {
            data[[12, p_id, rank]] = 1.0;
        }
    }
}
```

**说明**：
- 标记每个玩家的定缺花色（万、筒、条）
- 帮助 AI 理解玩家的策略和限制
- 定缺色是血战到底的核心规则之一

---

## 特征平面分配总结

| 平面范围 | 特征类型 | 说明 |
|---------|---------|------|
| 0-3 | 自身手牌 | 4 层 One-hot 编码 |
| 4-10 | 弃牌 | 三个对手的弃牌 + 最近弃牌 |
| 11 | 剩余牌数 | 归一化后的剩余牌数 |
| 12 | 定缺掩码 | 各家定缺色 |
| 13-24 | 对手手牌 | 其他三个玩家的手牌（每个玩家 4 层） |
| 25-28 | 副露 | 已碰/杠的牌（4 个玩家） |
| 29-32 | 玩家状态 | 是否离场 |
| 33-36 | 听牌状态 | 是否听牌 |
| 37-40 | 回合信息 | 回合数编码 |
| 41-44 | 当前玩家 | 当前回合的玩家 |
| 45 | 最后一张牌 | 是否最后一张牌 |
| 46-63 | 保留 | 用于未来扩展 |

---

## 实现状态

- ✅ **基础层**：全部实现
  - ✅ 手牌（4 层）
  - ✅ 弃牌
  - ✅ 副露

- ✅ **全局层**：全部实现
  - ✅ 剩余牌数
  - ✅ 当前局势（谁已胡、谁离场）
  - ✅ 各家定缺色

所有特征编码已完整实现，可用于 AI 训练。

