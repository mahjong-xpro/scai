# 核心结算逻辑审计 (Scoring Audit)

## 审计结果

### ✅ 1. "根"的指数级计算

**状态：正确**

**代码位置**：`rust/src/game/scoring.rs` 第 173-184 行

**实现**：
```rust
pub fn total_fans(&self) -> Option<u32> {
    // 根数倍率：2^根数
    let root_multiplier = 2_u32.checked_pow(self.roots as u32)?;
    
    // 动作加成倍率：2^动作加成数
    let action_multiplier = 2_u32.checked_pow(self.action_bonus as u32)?;
    
    // 总番数 = 基础番 × 根数倍率 × 动作加成倍率
    self.base_pattern
        .checked_mul(root_multiplier)?
        .checked_mul(action_multiplier)
}
```

**验证**：
- ✅ 每个根是 `2^1` 的翻倍（即乘以 `2^根数`）
- ✅ 公式：总番数 = 基础番型 × 2^根数 × 2^动作加成数
- ✅ 这是指数级计算（`checked_pow`），不是加法

**测试用例**：
- 基础番 4，1 个根：`4 × 2^1 = 8` ✅
- 基础番 4，2 个根：`4 × 2^2 = 16` ✅
- 基础番 16，2 个根，1 个动作：`16 × 2^2 × 2^1 = 128` ✅

---

### ❌ 2. 查叫最大番判定

**状态：存在缺陷**

**问题描述**：
当前实现只检查玩家当前手牌是否能直接胡牌，但没有检查玩家听的所有牌中，哪张牌能产生最高番数。

**用户要求**：
如果一个玩家听三张牌（比如 1、4、7 万），其中：
- 7 万胡了是清一色（4 番）
- 1、4 万只是平胡（1 番）

那么查叫逻辑应该自动锁定 7 万的最高番数来惩罚未听牌者。

**当前实现**（`rust/src/game/game_engine.rs` 第 630-650 行）：
```rust
if player.is_ready {
    // 计算听牌玩家的最高可能番数
    // 这里简化处理，使用基础番数
    let mut checker = WinChecker::new();
    let test_result = checker.check_win(&player.hand);
    if test_result.is_win {
        let base_fans = BaseFansCalculator::base_fans(test_result.win_type);
        let roots = RootCounter::count_roots(&player.hand, &player.melds);
        if let Some(total) = Settlement::new(base_fans, roots, 0).total_fans() {
            ready_players_max_fans = ready_players_max_fans.max(total);
            ready_players.push(player.id);
        }
    }
}
```

**问题**：
1. ❌ 只检查了当前手牌是否能直接胡牌（13 张），但听牌状态是 13 张差一张
2. ❌ 没有遍历所有可以听的牌，计算每种可能的胡牌番数
3. ❌ 没有选择最高番数作为惩罚标准

**修复方案**：
1. 使用 `ReadyChecker::check_ready()` 获取所有可以听的牌
2. 对每张可以听的牌，模拟添加后计算胡牌番数
3. 选择所有可能胡牌中的最高番数作为 `ready_players_max_fans`

---

## 修复计划

### 修复查叫最大番判定

**文件**：`rust/src/game/game_engine.rs`

**修改位置**：`final_settlement()` 方法中的听牌玩家番数计算逻辑

**新逻辑**：
```rust
if player.is_ready {
    // 获取所有可以听的牌
    let ready_tiles = player.get_ready_tiles();
    
    if !ready_tiles.is_empty() {
        let mut max_fan_for_player = 0u32;
        let mut checker = WinChecker::new();
        
        // 遍历所有可以听的牌，计算每种可能的胡牌番数
        for &ready_tile in &ready_tiles {
            // 创建测试手牌（添加这张牌）
            let mut test_hand = player.hand.clone();
            test_hand.add_tile(ready_tile);
            
            // 检查是否能胡牌
            let melds_count = player.melds.len() as u8;
            let win_result = checker.check_win_with_melds(&test_hand, melds_count);
            
            if win_result.is_win {
                // 计算该胡牌类型的番数
                let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
                let roots = RootCounter::count_roots(&test_hand, &player.melds);
                if let Some(total) = Settlement::new(base_fans, roots, 0).total_fans() {
                    max_fan_for_player = max_fan_for_player.max(total);
                }
            }
        }
        
        // 更新听牌玩家的最高番数
        if max_fan_for_player > 0 {
            ready_players_max_fans = ready_players_max_fans.max(max_fan_for_player);
            ready_players.push(player.id);
        }
    }
}
```

**测试用例**：
1. 玩家听 1、4、7 万，其中 7 万是清一色（4 番），1、4 万是平胡（1 番）
   - 预期：`ready_players_max_fans = 4`
2. 玩家听多张牌，其中一张是清七对（16 番），其他是平胡（1 番）
   - 预期：`ready_players_max_fans = 16`
3. 玩家听多张牌，其中一张是清七对 + 1 根（32 番），其他是平胡（1 番）
   - 预期：`ready_players_max_fans = 32`

---

## 总结

- ✅ **"根"的指数级计算**：实现正确，无需修改
- ❌ **查叫最大番判定**：存在缺陷，需要修复

修复后，查叫逻辑将能够正确识别听牌玩家所有可能胡牌中的最高番数，并以此作为惩罚未听牌者的标准。

