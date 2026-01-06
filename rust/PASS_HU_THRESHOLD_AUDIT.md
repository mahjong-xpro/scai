# "过胡锁定"番数阈值审计报告

## 问题描述

四川麻将规则是：放弃点炮后，不能胡同番或低番的点炮，但如果番数变大（比如摸到了根，或者场面变化导致番数增加），是可以胡的。另外自摸可以胡牌。

### 为什么重要

- 如果实现为全锁死（bool），AI 会变得极其胆小，不敢博大牌
- 如果不锁定，AI 会学会利用规则"钓鱼"，导致在正式对局中判定违规

## 当前实现分析

### ✅ 已正确实现的部分

1. **使用番数阈值而非 bool**：
   - `Player` 结构体中有 `passed_hu_fan: Option<u32>` - 这是番数阈值，不是 bool ✅
   - `check_passed_win_restriction` 函数正确检查番数阈值 ✅

2. **自摸不受限制**：
   - `check_passed_win_restriction` 中，如果 `is_self_draw` 为 true，直接返回 true ✅

3. **同一张牌不能胡**：
   - 如果 `tile == passed_hu_tile`，不能胡 ✅

4. **番数阈值检查**：
   - 如果 `fans <= threshold`，不能胡 ✅
   - 如果 `fans > threshold`，可以胡 ✅

### ❌ 潜在问题

#### 问题1：`record_passed_win` 记录的是"最小番数"而非"最大番数"

**当前实现**：
```rust
pub fn record_passed_win(&mut self, tile: Tile, fans: u32) {
    match self.passed_hu_fan {
        None => {
            self.passed_hu_fan = Some(fans);
            self.passed_hu_tile = Some(tile);
        }
        Some(existing_fans) => {
            if fans < existing_fans {  // ❌ 这里记录的是最小番数
                self.passed_hu_fan = Some(fans);
                self.passed_hu_tile = Some(tile);
            }
        }
    }
}
```

**问题**：
- 如果玩家先放弃了 2 番的点炮，然后放弃了 1 番的点炮
- 当前实现会记录 1 番（最小），但应该记录 2 番（最大）
- 因为规则是"不能胡同番或低番的点炮"，所以应该记录"最高番数"

**正确实现**：
```rust
pub fn record_passed_win(&mut self, tile: Tile, fans: u32) {
    match self.passed_hu_fan {
        None => {
            self.passed_hu_fan = Some(fans);
            self.passed_hu_tile = Some(tile);
        }
        Some(existing_fans) => {
            // 记录最大番数（更严格的限制）
            if fans > existing_fans {
                self.passed_hu_fan = Some(fans);
                self.passed_hu_tile = Some(tile);
            }
        }
    }
}
```

**为什么重要**：
- 如果玩家先放弃了 2 番，然后放弃了 1 番
- 如果记录 1 番，玩家可以胡 2 番的点炮（错误！）
- 如果记录 2 番，玩家不能胡 2 番或更低的点炮（正确！）

#### 问题2：需要确认"同一张牌"的限制是否正确

**当前实现**：
```rust
// 检查是否是同一张牌（如果是，不能胡）
if let Some(passed_tile) = passed_hu_tile {
    if tile == passed_tile {
        return false; // 不能胡同一张牌
    }
}
```

**分析**：
- 这个逻辑是正确的 ✅
- 如果玩家放弃了某张牌的点炮，在下一次摸牌前，不能胡同一张牌

## 改进方案

### 方案1：修复 `record_passed_win` 逻辑（推荐）

修改 `record_passed_win` 函数，记录"最大番数"而非"最小番数"：

```rust
pub fn record_passed_win(&mut self, tile: Tile, fans: u32) {
    match self.passed_hu_fan {
        None => {
            // 第一次过胡，直接记录
            self.passed_hu_fan = Some(fans);
            self.passed_hu_tile = Some(tile);
        }
        Some(existing_fans) => {
            // 记录最大番数（更严格的限制）
            // 规则：不能胡同番或低番的点炮，所以应该记录最高番数
            if fans > existing_fans {
                self.passed_hu_fan = Some(fans);
                self.passed_hu_tile = Some(tile);
            }
            // 注意：如果 fans <= existing_fans，不需要更新
            // 因为 existing_fans 已经是更严格的限制了
        }
    }
}
```

### 方案2：添加注释说明

在 `record_passed_win` 函数中添加详细注释，说明为什么记录最大番数：

```rust
/// 记录过胡（放弃点炮）
/// 
/// # 参数
/// 
/// - `tile`: 放弃的牌
/// - `fans`: 放弃时的番数
/// 
/// # 规则
/// 
/// 如果玩家多次过胡，记录最大番数（最严格的限制）。
/// 例如：如果玩家先放弃了 2 番，然后放弃了 1 番，
/// 应该记录 2 番（因为不能胡 2 番或更低的点炮）。
/// 
/// 如果当前没有过胡记录，或新的番数更大，则更新记录。
pub fn record_passed_win(&mut self, tile: Tile, fans: u32) {
    // ...
}
```

## 测试用例

应该添加测试用例来验证：

1. **测试1：记录最大番数**
   ```rust
   // 玩家先放弃 2 番，然后放弃 1 番
   // 应该记录 2 番（最大），而不是 1 番（最小）
   player.record_passed_win(Tile::Wan(1), 2);
   player.record_passed_win(Tile::Wan(2), 1);
   assert_eq!(player.passed_hu_fan, Some(2)); // 应该是 2，不是 1
   ```

2. **测试2：番数阈值检查**
   ```rust
   // 玩家放弃了 2 番的点炮
   player.record_passed_win(Tile::Wan(1), 2);
   
   // 不能胡 2 番或更低的点炮
   assert!(!rules::check_passed_win_restriction(
       Tile::Wan(2), 1, player.passed_hu_fan, player.passed_hu_tile, false
   ));
   assert!(!rules::check_passed_win_restriction(
       Tile::Wan(2), 2, player.passed_hu_fan, player.passed_hu_tile, false
   ));
   
   // 可以胡 3 番或更高的点炮
   assert!(rules::check_passed_win_restriction(
       Tile::Wan(2), 3, player.passed_hu_fan, player.passed_hu_tile, false
   ));
   ```

3. **测试3：自摸不受限制**
   ```rust
   // 玩家放弃了 2 番的点炮
   player.record_passed_win(Tile::Wan(1), 2);
   
   // 自摸不受限制，可以胡任何番数
   assert!(rules::check_passed_win_restriction(
       Tile::Wan(2), 1, player.passed_hu_fan, player.passed_hu_tile, true // 自摸
   ));
   ```

4. **测试4：同一张牌不能胡**
   ```rust
   // 玩家放弃了 1 万的点炮（2 番）
   player.record_passed_win(Tile::Wan(1), 2);
   
   // 不能胡同一张牌（即使番数更高）
   assert!(!rules::check_passed_win_restriction(
       Tile::Wan(1), 3, player.passed_hu_fan, player.passed_hu_tile, false
   ));
   
   // 可以胡其他牌（如果番数更高）
   assert!(rules::check_passed_win_restriction(
       Tile::Wan(2), 3, player.passed_hu_fan, player.passed_hu_tile, false
   ));
   ```

## 总结

当前实现**基本正确**，但有一个关键问题：

- ❌ `record_passed_win` 记录的是"最小番数"，应该记录"最大番数"
- ✅ 其他逻辑（番数阈值检查、自摸不受限制、同一张牌不能胡）都是正确的

修复后，实现将完全符合四川麻将规则。

