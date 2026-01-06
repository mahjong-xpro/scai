# 过胡锁定逻辑验证报告

## 问题描述

过胡锁定逻辑是AI训练中最容易导致模型崩溃的点。需要确保：

1. **锁定**：当 `Action::Hu` 可选却被放弃时，记录当前番数
2. **解锁**：必须在玩家**下一次摸牌（Draw）**后清空此限制

## 当前实现检查

### ✅ 1. Player 结构体中的字段

**位置**: `rust/src/game/player.rs:21-29`

```rust
/// 过胡锁定：记录放弃的点炮番数（None 表示未过胡）
pub passed_hu_fan: Option<u32>,
/// 过胡锁定的牌（None 表示未过胡）
pub passed_hu_tile: Option<Tile>,
```

**状态**: ✅ 已实现

### ✅ 2. 锁定逻辑（Action::Pass 处理）

**位置**: `rust/src/game/game_engine.rs:102-156`

```rust
Action::Pass => {
    // 处理过胡：如果上一个动作是出牌，且当前玩家可以胡，则记录过胡番数
    if let Some(Action::Discard { tile }) = self.state.last_action {
        let player = &self.state.players[player_id as usize];
        
        // 检查是否可以胡这张牌
        let mut test_hand = player.hand.clone();
        test_hand.add_tile(tile);
        let mut checker = WinChecker::new();
        let melds_count = player.melds.len() as u8;
        let win_result = checker.check_win_with_melds(&test_hand, melds_count);
        
        if win_result.is_win {
            // 计算完整番数（包括根数）
            let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
            let roots = RootCounter::count_roots(&test_hand, &player.melds);
            
            // 计算总番数（基础番 × 2^根数）
            let total_fans = ...;
            
            // 记录过胡番数和牌
            let player = &mut self.state.players[player_id as usize];
            player.record_passed_win(tile, total_fans);
        }
    }
    Ok(ActionResult::Passed)
}
```

**状态**: ✅ 已实现，正确记录了过胡番数和牌

### ✅ 3. 解锁逻辑（摸牌后清除）

**位置**: `rust/src/game/game_engine.rs:146-166`

```rust
fn handle_draw(&mut self, player_id: u8) -> Result<ActionResult, GameError> {
    // ...
    
    // 清除过胡锁定（规则：过胡锁定只在"下一次摸牌前"有效）
    self.state.players[player_id as usize].clear_passed_win();
    
    // 从牌墙摸牌
    if let Some(tile) = self.wall.draw() {
        self.state.players[player_id as usize].hand.add_tile(tile);
        Ok(ActionResult::Drawn { tile })
    } else {
        Err(GameError::GameOver)
    }
}
```

**状态**: ✅ 已实现，在摸牌时清除过胡锁定

### ✅ 4. 过胡限制检查

**位置**: `rust/src/game/rules.rs:77-105`

```rust
pub fn check_passed_win_restriction(
    tile: crate::tile::Tile,
    fans: u32,
    passed_hu_fan: Option<u32>,
    passed_hu_tile: Option<crate::tile::Tile>,
    is_self_draw: bool,
) -> bool {
    // 自摸不受过胡限制
    if is_self_draw {
        return true;
    }
    
    // 如果没有过胡记录，可以胡
    let Some(threshold) = passed_hu_fan else {
        return true;
    };
    
    // 检查是否是同一张牌（如果是，不能胡）
    if let Some(passed_tile) = passed_hu_tile {
        if tile == passed_tile {
            return false;
        }
    }
    
    // 如果当前番数 <= 过胡记录的番数，不能胡
    if fans <= threshold {
        return false;
    }
    
    true // 可以胡（更高番）
}
```

**状态**: ✅ 已实现，正确检查过胡限制

## 潜在问题检查

### ⚠️ 问题1：是否在所有摸牌路径都清除了过胡锁定？

**检查点**：
1. `handle_draw` - ✅ 已清除
2. 游戏初始化后的第一次摸牌 - 需要检查
3. 其他可能的摸牌路径 - 需要检查

### ⚠️ 问题2：过胡记录是否正确传递到检查逻辑？

**检查点**：
1. `ActionMask::can_win_with_player_id` - ✅ 已传递
2. `handle_win` 中的检查 - 需要检查

### ⚠️ 问题3：AI 训练时的状态一致性

**检查点**：
1. 状态克隆时是否正确保留了过胡锁定？
2. 状态重置时是否正确清除了过胡锁定？

## 建议的测试用例

1. **测试过胡锁定**：
   - 玩家A可以胡玩家B打出的1万（2番）
   - 玩家A选择Pass
   - 玩家A应该记录 `passed_hu_fan = Some(2)`, `passed_hu_tile = Some(1万)`
   - 玩家B再次打出1万，玩家A不能胡（同一张牌）
   - 玩家B打出2万（1番），玩家A不能胡（番数 <= 2）
   - 玩家B打出3万（4番），玩家A可以胡（番数 > 2）

2. **测试过胡解锁**：
   - 玩家A过胡后，摸牌
   - 玩家A的 `passed_hu_fan` 和 `passed_hu_tile` 应该被清除
   - 玩家A可以正常胡牌

3. **测试自摸不受限制**：
   - 玩家A过胡后，摸牌
   - 玩家A摸到可以自摸的牌
   - 玩家A可以自摸（不受过胡限制）

## 结论

当前实现**基本正确**，但需要验证：
1. 所有摸牌路径都清除了过胡锁定
2. 过胡记录在所有检查点都正确传递
3. AI训练时的状态一致性

建议添加完整的测试用例来验证这些场景。

