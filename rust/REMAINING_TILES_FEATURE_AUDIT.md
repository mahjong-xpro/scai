# "残牌感知"特征审计报告

## 问题描述

顶级高手会算"绝张"。如果特征里没有"剩余未见牌张数"，AI 永远学不会"这张牌场上已经现了 3 张，我手里有 1 张，所以我打出去绝对不会有点炮风险"这种高级防御策略。

### 核心逻辑

```
Remaining(Tile) = 4 - Self(Tile) - Discarded(Tile) - Melded(Tile)
```

其中：
- `Self(Tile)`: 自己手牌中的该牌数量
- `Discarded(Tile)`: 所有玩家弃牌中的该牌数量
- `Melded(Tile)`: 所有玩家碰/杠中的该牌数量

## 当前实现分析

### ✅ Plane 13: 每张牌在场上已出现的张数（已实现）

**位置**: `rust/src/python/tensor.rs:185-232`

**实现**:
```rust
// Plane 13: 每张牌在场上已出现的张数（0-4，归一化到 [0, 1]）
// 统计所有可见的牌：手牌 + 碰/杠 + 弃牌
let mut tile_visibility = [0u8; 27]; // 27 种牌

// 统计所有玩家的手牌
for player in &game_state.players {
    for (tile, &count) in player.hand.tiles_map() {
        tile_visibility[tile_idx] += count;
    }
}

// 统计已碰/杠的牌
for player in &game_state.players {
    for meld in &player.melds {
        tile_visibility[tile_idx] += count;
    }
}

// 统计弃牌历史
for discard_record in &game_state.discard_history {
    tile_visibility[tile_idx] += 1;
}

// 填充到 Plane 13（归一化到 [0, 1] 范围，除以 4）
let normalized = (count as f32 / 4.0).min(1.0);
data[[13, suit, rank]] = normalized;
```

**问题**:
- ✅ 记录了"已出现的张数"
- ❌ **没有记录"剩余未见牌张数"**
- ❌ AI 需要自己计算：剩余 = 4 - 已出现（增加了学习难度）

### ❌ 缺失：剩余未见牌张数

**需求**: 在 4D tensor 中，必须有一个平面记录每张牌的剩余未见牌张数（0-4）

**重要性**:
- AI 需要学会"算牌"
- 判断某张牌是否已经绝张（剩余 = 0）
- 判断某张牌是否还有剩余（用于决定是否博杠）
- 判断打某张牌是否有点炮风险（如果剩余 = 0，绝对安全）

## 改进方案

### 方案1：添加新平面记录剩余未见牌张数（推荐）

**位置**: 使用 Plane 30（在弃牌序列之后）

**实现**:
```rust
// Plane 30: 每张牌的剩余未见牌张数（0-4，归一化到 [0, 1]）
// 计算公式：Remaining(Tile) = 4 - Self(Tile) - Discarded(Tile) - Melded(Tile)
for suit in 0..3 {
    for rank in 0..9 {
        let tile_idx = suit * 9 + rank;
        let appeared_count = tile_visibility[tile_idx];
        let remaining_count = 4u8.saturating_sub(appeared_count);
        
        // 归一化到 [0, 1] 范围（除以 4）
        let normalized = (remaining_count as f32 / 4.0).min(1.0);
        data[[30, suit, rank]] = normalized;
    }
}
```

**优点**:
- ✅ 直接提供剩余数量，AI 不需要计算
- ✅ 推理时可用（不依赖 Oracle）
- ✅ 帮助 AI 学习"绝张"判断和防御策略

### 方案2：修改 Plane 13 记录剩余数量

**位置**: 修改 Plane 13 的实现

**实现**: 将 Plane 13 从"已出现的张数"改为"剩余未见牌张数"

**优点**:
- ✅ 不需要新平面
- ✅ 推理时可用

**缺点**:
- ⚠️ 失去了"已出现的张数"信息（但可以通过 4 - 剩余计算）

### 方案3：同时记录已出现和剩余（最完整）

**位置**: 使用 Plane 13 和 Plane 30

**实现**:
- Plane 13: 每张牌已出现的张数（0-4，归一化到 [0, 1]）
- Plane 30: 每张牌剩余未见牌张数（0-4，归一化到 [0, 1]）

**优点**:
- ✅ 信息最完整
- ✅ 两种表示方式，方便模型学习
- ✅ 可以验证：已出现 + 剩余 = 4

**缺点**:
- ⚠️ 占用两个平面

## 推荐实现

**推荐方案3**：同时记录已出现和剩余数量

**理由**:
1. 这是 AI 训练的关键特征
2. 推理时必须可用（不能依赖 Oracle）
3. 两种表示方式，方便模型学习
4. 可以验证数据一致性

## 实现步骤

1. **保持 Plane 13**: 每张牌已出现的张数（已有实现）
2. **添加 Plane 30**: 每张牌剩余未见牌张数（新实现）
3. **更新文档**: 更新特征编码文档

## 测试用例

应该添加测试用例来验证：

1. **测试1：剩余数量计算**
   ```rust
   // 如果某张牌已出现 3 张，剩余应该是 1 张
   // 如果某张牌已出现 4 张，剩余应该是 0 张（绝张）
   // 如果某张牌已出现 0 张，剩余应该是 4 张
   ```

2. **测试2：绝张判断**
   ```rust
   // 如果剩余 = 0，该牌已经绝张
   // 打绝张绝对安全（不会点炮）
   ```

3. **测试3：防御策略**
   ```rust
   // 如果剩余 = 0，可以安全打出
   // 如果剩余 = 1，需要谨慎（可能是对手听牌）
   ```

