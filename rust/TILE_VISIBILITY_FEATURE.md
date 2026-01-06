# 墙内残余牌感（Tile Visibility Feature）实现审计

## 问题描述

AI 需要学会"算牌"（例如：判断某张牌是否已经绝张，从而决定是否博杠）。这要求在特征张量中包含：

**每张牌在场上已出现的张数**（万、筒、条共 27 种牌，每种牌 4 张，共 108 张）

## 当前实现状态

### ✅ 1. 牌池可见性特征（已实现，但位置不对）

**位置**: `rust/src/python/game_state.rs:196-230`

**实现**: `compute_tile_visibility()` 方法

```rust
fn compute_tile_visibility(&self) -> Vec<f32> {
    let mut visibility = vec![0.0f32; 108];
    
    // 统计所有玩家的手牌
    for player in &self.inner.players {
        for (tile, &count) in player.hand.tiles_map() {
            if let Some(idx) = ActionMask::tile_to_index(*tile) {
                visibility[idx] += count as f32;
            }
        }
    }
    
    // 统计已碰/杠的牌
    for player in &self.inner.players {
        for meld in &player.melds {
            let (tile, count) = match meld {
                Meld::Triplet { tile } => (*tile, 3),
                Meld::Kong { tile, .. } => (*tile, 4),
            };
            if let Some(idx) = ActionMask::tile_to_index(tile) {
                visibility[idx] += count as f32;
            }
        }
    }
    
    // 统计弃牌历史
    for discard_record in &self.inner.discard_history {
        if let Some(idx) = ActionMask::tile_to_index(discard_record.tile) {
            visibility[idx] += 1.0;
        }
    }
    
    visibility
}
```

**问题**: 
- ✅ 计算了每张牌的出现次数
- ❌ 但这是在扁平化的张量中（`to_tensor()` 方法中追加到结果末尾）
- ❌ **不在 4D tensor 的平面中**，AI 模型可能无法有效利用

### ⚠️ 2. Plane 11: 剩余牌堆计数（不完整）

**位置**: `rust/src/python/tensor.rs:111-119`

**实现**:
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

**问题**:
- ❌ 只记录了**总的剩余牌数**，归一化后填充到所有位置
- ❌ **没有记录每张牌的出现次数**
- ❌ AI 无法判断某张牌是否已经绝张

### ⚠️ 3. Oracle 特征（仅训练时使用）

**位置**: `rust/src/python/tensor.rs:256-301`

**实现**: Plane 46-55 记录牌堆余牌分布

**问题**:
- ❌ 只在 `use_oracle=true` 时填充
- ❌ 推理时（`use_oracle=false`）不可用
- ❌ 需要外部传入 `wall_tile_distribution`，不是从游戏状态计算

## 缺失的关键特征

### ❌ 每张牌的出现次数（推理时可用）

**需求**: 在 4D tensor 中，必须有一个平面记录每张牌在场上已出现的张数（0-4）

**重要性**: 
- AI 需要学会"算牌"
- 判断某张牌是否已经绝张（4 张都已出现）
- 判断某张牌是否还有剩余（用于决定是否博杠）

**当前状态**: 
- ❌ 没有在 4D tensor 的平面中实现
- ✅ 有 `compute_tile_visibility()` 但只在扁平化张量中

## 改进方案

### 方案1: 在 4D tensor 中添加新平面（推荐）

**位置**: 使用 Plane 13（或重新分配平面）

**实现**: 在 `state_to_tensor()` 中添加：

```rust
// Plane 13: 每张牌在场上已出现的张数（0-4，归一化到 [0, 1]）
// 统计所有可见的牌：手牌 + 碰/杠 + 弃牌
let mut tile_visibility = [0u8; 27]; // 27 种牌，每种最多 4 张

// 统计所有玩家的手牌
for player in &game_state.players {
    for (tile, &count) in player.hand.tiles_map() {
        let (suit_idx, rank_idx) = tile_to_indices(tile);
        let tile_idx = suit_idx * 9 + rank_idx;
        tile_visibility[tile_idx] += count;
    }
}

// 统计已碰/杠的牌
for player in &game_state.players {
    for meld in &player.melds {
        let (tile, count) = match meld {
            Meld::Triplet { tile } => (*tile, 3),
            Meld::Kong { tile, .. } => (*tile, 4),
        };
        let (suit_idx, rank_idx) = tile_to_indices(&tile);
        let tile_idx = suit_idx * 9 + rank_idx;
        tile_visibility[tile_idx] += count;
    }
}

// 统计弃牌历史
for discard_record in &game_state.discard_history {
    let (suit_idx, rank_idx) = tile_to_indices(&discard_record.tile);
    let tile_idx = suit_idx * 9 + rank_idx;
    tile_visibility[tile_idx] += 1;
}

// 填充到 Plane 13
for suit in 0..3 {
    for rank in 0..9 {
        let tile_idx = suit * 9 + rank;
        let count = tile_visibility[tile_idx];
        // 归一化到 [0, 1] 范围（除以 4）
        let normalized = (count as f32 / 4.0).min(1.0);
        data[[13, suit, rank]] = normalized;
    }
}
```

**优点**:
- ✅ 推理时可用（不依赖 Oracle）
- ✅ 在 4D tensor 的平面中，模型可以直接使用
- ✅ 计算简单，从游戏状态直接计算

**缺点**:
- ⚠️ 需要重新分配平面（Plane 13 当前用于 Oracle 特征）

### 方案2: 使用现有 Plane 11（修改实现）

**位置**: 修改 Plane 11 的实现

**实现**: 将 Plane 11 从"剩余牌数"改为"每张牌的出现次数"

**优点**:
- ✅ 不需要重新分配平面
- ✅ 推理时可用

**缺点**:
- ⚠️ 失去了"剩余牌数"信息（但可以通过 108 - 总出现次数计算）

### 方案3: 添加多个平面（最完整）

**位置**: 使用 Plane 13-15

**实现**:
- Plane 13: 每张牌的出现次数（归一化到 [0, 1]）
- Plane 14: 每张牌的剩余数量（4 - 出现次数，归一化到 [0, 1]）
- Plane 15: 是否绝张（出现次数 == 4，One-hot）

**优点**:
- ✅ 信息最完整
- ✅ 推理时可用
- ✅ 多种表示方式，方便模型学习

**缺点**:
- ⚠️ 占用更多平面

## 推荐实现

**推荐方案1**: 在 Plane 13 添加每张牌的出现次数（推理时可用）

**理由**:
1. 这是 AI 训练的关键特征
2. 推理时必须可用（不能依赖 Oracle）
3. 计算简单，从游戏状态直接计算
4. 可以重新分配平面（将 Oracle 特征向后移动）

## 实现步骤

1. **修改 `state_to_tensor()`**: 在 Plane 13 添加每张牌的出现次数
2. **调整 Oracle 特征**: 将 Plane 13-24 向后移动到 Plane 14-25
3. **更新文档**: 更新 `FEATURE_ENCODING.md`

