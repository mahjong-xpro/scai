# 过胡锁定（Pass-Winning Restriction）修复

## 问题描述

在血战到底麻将中，为了防止玩家恶意"钓鱼"，有一条核心规则：
- **如果玩家放弃了当前点炮，在下一次摸牌前，不能胡同一张牌或番数更低的点炮牌**

## 修复内容

### 1. Player 结构体增强

在 `Player` 结构体中添加了 `passed_hu_fan: Option<u32>` 字段：

```rust
pub struct Player {
    // ... 其他字段
    /// 过胡锁定：记录放弃的点炮番数（None 表示未过胡）
    /// 
    /// 规则：如果玩家放弃了当前点炮，在下一次摸牌前，不能胡同一张牌或番数 <= 该记录值的点炮牌
    /// 注意：自摸不受此限制
    pub passed_hu_fan: Option<u32>,
}
```

### 2. Player 方法

添加了两个新方法：

- `record_passed_win(fans: u32)`: 记录过胡番数
  - 如果当前没有过胡记录，或新的番数更小，则更新记录（取更严格的限制）
  
- `clear_passed_win()`: 清除过胡锁定
  - 在玩家摸牌后调用，因为过胡锁定只在"下一次摸牌前"有效

### 3. 规则检查函数

在 `rules.rs` 中添加了新函数：

```rust
pub fn check_passed_win_restriction(
    fans: u32,
    passed_hu_fan: Option<u32>,
    is_self_draw: bool,
) -> bool
```

**规则**：
- 自摸不受过胡限制（`is_self_draw == true` 时总是返回 `true`）
- 如果没有过胡记录，可以胡任何番数的点炮
- 如果当前番数 <= 过胡记录的番数，不能胡（返回 `false`）
- 如果当前番数 > 过胡记录的番数，可以胡（返回 `true`）

### 4. ActionMask 更新

更新了 `ActionMask::can_win` 方法，添加了 `is_self_draw` 参数：

```rust
pub fn can_win(
    &self,
    hand: &Hand,
    tile: &Tile,
    state: &GameState,
    declared_suit: Option<Suit>,
    fans: u32,
    is_self_draw: bool,  // 新增参数
) -> bool
```

### 5. GameEngine 更新

- **`handle_draw`**: 在玩家摸牌后自动清除过胡锁定
- **`handle_pass`**: 当玩家选择 Pass 时，如果上一个动作是出牌且当前玩家可以胡，则记录过胡番数

## 使用示例

### 场景 1：玩家放弃点炮

```rust
// 玩家 A 出牌，玩家 B 可以胡（2 番），但选择 Pass
let mut player_b = Player::new(1);
player_b.record_passed_win(2);  // 记录过胡：2 番

// 在下一次摸牌前，玩家 B 不能胡 1 番或 2 番的点炮
assert!(!rules::check_passed_win_restriction(1, player_b.passed_hu_fan, false));
assert!(!rules::check_passed_win_restriction(2, player_b.passed_hu_fan, false));

// 但可以胡 3 番及以上的点炮（番数更高）
assert!(rules::check_passed_win_restriction(3, player_b.passed_hu_fan, false));

// 自摸不受限制
assert!(rules::check_passed_win_restriction(1, player_b.passed_hu_fan, true));
```

### 场景 2：玩家摸牌后清除锁定

```rust
// 玩家 B 摸牌
player_b.clear_passed_win();

// 清除后可以胡任何番数的点炮
assert!(rules::check_passed_win_restriction(1, player_b.passed_hu_fan, false));
assert!(rules::check_passed_win_restriction(2, player_b.passed_hu_fan, false));
```

### 场景 3：多次过胡

```rust
let mut player = Player::new(0);

// 第一次过胡：放弃 3 番
player.record_passed_win(3);
assert_eq!(player.passed_hu_fan, Some(3));

// 第二次过胡：放弃 2 番（更新为更小的值，更严格的限制）
player.record_passed_win(2);
assert_eq!(player.passed_hu_fan, Some(2));

// 第三次过胡：放弃 5 番（不更新，因为 5 > 2）
player.record_passed_win(5);
assert_eq!(player.passed_hu_fan, Some(2));  // 保持为 2
```

## 测试覆盖

新增了 `tests/passed_win_test.rs`，包含以下测试：

1. `test_passed_win_restriction`: 测试基本的过胡锁定逻辑
2. `test_record_passed_win_multiple_times`: 测试多次过胡的情况
3. `test_passed_win_clear_on_draw`: 测试摸牌后清除过胡锁定

所有测试均通过 ✅

## 兼容性

- 保留了旧版的 `can_win_after_pass` 函数（基于 `PassedWin` 记录），确保向后兼容
- 新版的 `check_passed_win_restriction` 函数使用 `Player.passed_hu_fan`，更符合用户需求
- 两个机制可以同时工作，提供双重保护

## 注意事项

1. **自摸不受限制**：自摸时 `is_self_draw` 参数必须为 `true`，否则会被错误地应用过胡限制
2. **摸牌后清除**：必须在玩家摸牌后调用 `clear_passed_win()`，否则过胡锁定会一直有效
3. **番数比较**：使用 `<=` 进行比较，即不能胡相同或更低番数的点炮

## 修复完成

✅ 所有功能已实现并测试通过
✅ 代码编译无错误
✅ 所有现有测试仍然通过

