# 过胡锁定（Pass-Hu Lock）审计报告

## 检查点

根据用户要求，检查以下三个关键点：

1. ✅ **Player 结构体是否有 `passed_hu_fan` 字段**
2. ✅ **`handle_pass` 时是否记录了番数**
3. ✅ **`handle_draw` 时是否清空了锁定状态**

## 实现状态

### 1. Player 结构体字段 ✅

**位置**: `rust/src/game/player.rs:21-25`

```rust
/// 过胡锁定：记录放弃的点炮番数（None 表示未过胡）
/// 
/// 规则：如果玩家放弃了当前点炮，在下一次摸牌前，不能胡同一张牌或番数 <= 该记录值的点炮牌
/// 注意：自摸不受此限制
pub passed_hu_fan: Option<u32>,
```

**状态**: ✅ **已实现**

### 2. handle_pass 时记录番数 ✅

**位置**: `rust/src/game/game_engine.rs:102-124`

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
            // 计算番数
            use crate::game::scoring::BaseFansCalculator;
            let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
            
            // 记录过胡番数
            let player = &mut self.state.players[player_id as usize];
            player.record_passed_win(base_fans);
        }
    }
    Ok(ActionResult::Passed)
},
```

**状态**: ✅ **已实现**

**逻辑**:
- 检查上一个动作是否是出牌
- 如果可以胡这张牌，计算番数
- 调用 `player.record_passed_win(base_fans)` 记录番数

### 3. handle_draw 时清空锁定 ✅

**位置**: `rust/src/game/game_engine.rs:130-150`

```rust
pub fn handle_draw(&mut self, player_id: u8) -> Result<ActionResult, GameError> {
    // ... 摸牌逻辑 ...
    
    // 清除过胡锁定（规则：过胡锁定只在"下一次摸牌前"有效）
    let player = &mut self.state.players[player_id as usize];
    player.clear_passed_win();
    
    // ... 其他逻辑 ...
}
```

**状态**: ✅ **已实现**

**逻辑**:
- 在玩家摸牌后，立即调用 `player.clear_passed_win()` 清空过胡锁定
- 符合规则："过胡锁定只在'下一次摸牌前'有效"

## 过胡限制检查

### 检查函数

**位置**: `rust/src/game/rules.rs:75-96`

```rust
pub fn check_passed_win_restriction(
    fans: u32,
    passed_hu_fan: Option<u32>,
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
    
    // 如果当前番数 <= 过胡记录的番数，不能胡
    if fans <= threshold {
        return false;
    }
    
    true // 可以胡（番数更高）
}
```

**状态**: ✅ **已实现**

### 使用位置

1. **动作掩码生成**: `rust/src/engine/action_mask.rs:94`
   - 在生成动作掩码时，检查过胡限制
   - 如果被限制，不允许胡牌动作

2. **胡牌处理**: `rust/src/game/game_engine.rs:350, 569`
   - 在处理点炮胡时，检查过胡限制
   - 如果被限制，不允许胡牌

## 潜在问题

### 问题1: 番数计算不完整 ⚠️

**位置**: `rust/src/game/game_engine.rs:117`

```rust
let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
```

**问题**: 只计算了基础番数，没有考虑根数（Gen）和动作加成。

**影响**: 
- 如果玩家听牌有多种可能，其中一种有根数，过胡时只记录了基础番数
- 可能导致过胡限制不够严格

**建议**: 应该计算完整番数（包括根数），但不需要考虑动作加成（因为动作加成是实际胡牌时才确定的）。

### 问题2: 同一张牌的过胡限制 ⚠️

**规则**: "不能胡同一张牌或番数 <= 该记录值的点炮牌"

**当前实现**: 只检查番数，没有检查是否是同一张牌。

**位置**: `rust/src/game/rules.rs:75-96`

```rust
pub fn check_passed_win_restriction(
    fans: u32,
    passed_hu_fan: Option<u32>,
    is_self_draw: bool,
) -> bool {
    // ... 只检查番数，没有检查牌 ...
}
```

**建议**: 应该同时检查：
1. 是否是同一张牌（如果是，不能胡）
2. 番数是否 <= 记录值（如果是，不能胡）

## 改进建议

### 改进1: 完善番数计算

在 `handle_pass` 时，应该计算完整番数（包括根数）：

```rust
if win_result.is_win {
    // 计算完整番数（包括根数）
    let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
    let roots = RootCounter::count_roots(&test_hand, &player.melds);
    
    // 计算总番数（不考虑动作加成，因为动作加成是实际胡牌时才确定的）
    let total_fans = if win_result.win_type == WinType::DragonSevenPairs {
        BaseFansCalculator::dragon_seven_pairs_fans(roots)
    } else {
        // 基础番 × 2^根数
        base_fans * 2_u32.pow(roots as u32)
    };
    
    // 记录过胡番数
    player.record_passed_win(total_fans);
}
```

### 改进2: 记录过胡的牌

在 `Player` 结构体中添加 `passed_hu_tile: Option<Tile>` 字段，记录过胡的牌：

```rust
pub struct Player {
    // ... 其他字段 ...
    pub passed_hu_fan: Option<u32>,
    pub passed_hu_tile: Option<Tile>, // 新增：记录过胡的牌
}
```

在 `check_passed_win_restriction` 中同时检查牌和番数：

```rust
pub fn check_passed_win_restriction(
    tile: Tile,
    fans: u32,
    passed_hu_fan: Option<u32>,
    passed_hu_tile: Option<Tile>,
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
    
    // 检查是否是同一张牌
    if let Some(passed_tile) = passed_hu_tile {
        if tile == passed_tile {
            return false; // 不能胡同一张牌
        }
    }
    
    // 如果当前番数 <= 过胡记录的番数，不能胡
    if fans <= threshold {
        return false;
    }
    
    true // 可以胡（番数更高）
}
```

## 总结

### ✅ 已实现的功能

1. Player 结构体有 `passed_hu_fan` 字段
2. `handle_pass` 时记录了番数
3. `handle_draw` 时清空了锁定状态
4. 过胡限制检查函数已实现
5. 在动作掩码和胡牌处理中使用了过胡限制

### ⚠️ 需要改进的地方

1. **番数计算不完整**: 只计算了基础番数，没有考虑根数
2. **同一张牌限制**: 没有检查是否是同一张牌，只检查了番数

### 建议优先级

1. **P0 (高优先级)**: 完善番数计算，包括根数
2. **P1 (中优先级)**: 添加同一张牌的过胡限制检查

