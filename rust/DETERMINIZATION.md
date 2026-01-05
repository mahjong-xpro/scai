# 确定性填充支持 (Determinization)

## 问题描述

顶级 AI 必须使用 ISMCTS（信息集蒙特卡洛树搜索）。这要求 Rust 引擎支持"假定对手手牌"的功能。

## 实现方案

### 方法签名

```rust
pub fn fill_unknown_cards(
    &mut self,
    viewer_id: u8,
    remaining_wall_count: usize,
    seed: u64
)
```

### 参数说明

- **viewer_id**: 观察者玩家 ID（当前玩家视角，只有该玩家的手牌是已知的）
- **remaining_wall_count**: 牌墙剩余牌数（用于计算未知牌数）
- **seed**: 随机数种子（用于确定性随机分配）

### 算法流程

1. **统计所有已知的牌**：
   - 观察者的手牌（已知）
   - 所有玩家的明牌（碰/杠的牌组，已知）
   - 所有玩家的弃牌（已知）

2. **计算剩余未知的牌**：
   ```
   未知牌数 = 108 - 已知牌数 - 牌墙剩余牌数 - 对手已有手牌数
   ```

3. **生成可用牌池**：
   - 生成所有可能的牌（每种牌 4 张）
   - 减去已知的牌
   - 得到可用牌池

4. **使用 seed 生成确定性随机数**：
   - 使用 `StdRng::seed_from_u64(seed)` 创建确定性随机数生成器
   - 对可用牌池进行随机打乱

5. **计算每个对手需要的手牌数量**：
   - 初始 13 张
   - 每碰一次减 3 张
   - 每杠一次减 4 张
   - 减去当前已有手牌数 = 需要填充的牌数

6. **将剩余牌随机分配给对手**：
   - 只分配给对手（不包括观察者）
   - 跳过已离场的玩家
   - 确保每种牌不超过 4 张

### 关键特性

#### 1. 确定性（Deterministic）

使用相同的 `seed` 会产生相同的分配结果，这对于 ISMCTS 的重复模拟非常重要。

```rust
// 相同 seed 产生相同结果
state1.fill_unknown_cards(0, 50, 12345);
state2.fill_unknown_cards(0, 50, 12345);
// state1 和 state2 的对手手牌应该相同
```

#### 2. 正确处理碰/杠

自动计算对手的手牌数量，考虑已碰/杠的牌：

```rust
// 对手碰了 1 次：13 - 3 = 10 张手牌
// 对手杠了 1 次：13 - 4 = 9 张手牌
// 对手碰了 2 次：13 - 6 = 7 张手牌
```

#### 3. 跳过已离场玩家

已离场的玩家不会被填充，避免无效操作。

#### 4. 防止超过最大数量

确保每种牌不超过 4 张，符合麻将规则。

### 使用场景

#### ISMCTS 模拟

```rust
// 在 ISMCTS 的每个信息集节点中
let mut simulated_state = game_state.clone();
simulated_state.fill_unknown_cards(
    current_player_id,
    wall.remaining_count(),
    simulation_seed
);

// 使用填充后的状态进行模拟推演
let result = simulate_game(&simulated_state);
```

#### 多线程并行模拟

```rust
// 每个线程使用不同的 seed
for thread_id in 0..num_threads {
    let mut state = game_state.clone();
    state.fill_unknown_cards(
        player_id,
        remaining_count,
        thread_id as u64 * 1000 + iteration
    );
    // 并行模拟
}
```

### 已知牌统计

#### 观察者的手牌

```rust
// 观察者的手牌是已知的
for (tile, &count) in self.players[viewer_id].hand.tiles_map() {
    known_tiles.entry(*tile).or_insert(0) += count;
}
```

#### 所有玩家的明牌

```rust
// 碰/杠的牌组是明牌，所有玩家可见
for player in &self.players {
    for meld in &player.melds {
        match meld {
            Meld::Triplet { tile } => {
                known_tiles.entry(*tile).or_insert(0) += 3; // 碰：3 张
            }
            Meld::Kong { tile, .. } => {
                known_tiles.entry(*tile).or_insert(0) += 4; // 杠：4 张
            }
        }
    }
}
```

#### 所有玩家的弃牌

```rust
// 弃牌历史是公开信息
for discard_record in &self.discard_history {
    known_tiles.entry(discard_record.tile).or_insert(0) += 1;
}
```

### 注意事项

1. **牌墙剩余牌数**：需要从 `GameEngine` 或 `Wall` 获取，调用者需要传入正确的值
2. **对手已有手牌**：如果对手的手牌已经被部分填充（在之前的模拟中），需要正确计算差值
3. **已离场玩家**：已离场的玩家不会被填充，其手牌保持不变
4. **确定性**：使用相同的 seed 和相同的游戏状态，应该产生相同的填充结果

### 测试覆盖

✅ 基本功能测试
✅ 确定性测试（相同 seed 产生相同结果）
✅ 已离场玩家处理
✅ 碰/杠情况处理
✅ 最大牌数限制（每种牌不超过 4 张）

### 性能考虑

- **时间复杂度**：O(108 + n)，n 为对手数量（通常为 3）
- **空间复杂度**：O(108)，用于存储可用牌池
- **随机数生成**：使用 `StdRng`，性能良好

### 实现完成

✅ `fill_unknown_cards` 方法实现
✅ 已知牌统计（观察者手牌、明牌、弃牌）
✅ 可用牌池生成
✅ 确定性随机数生成
✅ 对手手牌数量计算（考虑碰/杠）
✅ 牌分配逻辑
✅ 完整测试覆盖

确定性填充支持已实现，可以用于 ISMCTS 的模拟推演。

