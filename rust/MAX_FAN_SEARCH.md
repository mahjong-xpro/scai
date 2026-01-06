# 查大叫"最大收益"算法 (Max-Fan Search)

## 问题描述

在流局（牌抓完）结算查大叫时，规则要求未听牌者按听牌者可能胡到的**最高番数**赔付。

### 为什么重要

如果只检查"能否胡牌"或只取第一张可听牌的番数，AI 会学会"混日子"而不是追求高番。例如：
- 玩家听1万（平胡，1番）和7万（清一色，4番）
- 如果只按1番计算，未听牌玩家只需赔付1番
- 但实际上玩家可能胡到4番，应该按4番赔付

## 实现方案

### 当前实现

在 `GameEngine::final_settlement()` 方法中（lines 698-735），已经实现了最大收益算法：

```rust
// 遍历所有可以听的牌，计算每种可能的胡牌番数
for &ready_tile in &ready_tiles {
    // 创建测试手牌（添加这张牌）
    let mut test_hand = player.hand.clone();
    test_hand.add_tile(ready_tile);
    
    // 检查是否能胡牌
    let win_result = checker.check_win_with_melds(&test_hand, melds_count);
    
    if win_result.is_win {
        // 计算该胡牌类型的番数
        let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
        let roots = RootCounter::count_roots(&test_hand, &player.melds);
        let total = Settlement::new(base_fans, roots, 0).total_fans();
        
        max_fan_for_player = max_fan_for_player.max(total);
    }
}
```

### 算法步骤

1. **获取所有可听牌**：使用 `player.get_ready_tiles()` 获取玩家所有可以听的牌
2. **遍历每张可听牌**：对每张可听牌进行以下操作：
   - 创建测试手牌（添加这张牌）
   - 检查是否能胡牌
   - 如果能胡，计算番数（基础番 + 根数倍率）
   - 更新最大番数
3. **取最大值**：在所有可听牌中，选择番数最高的作为该玩家的最大可能番数
4. **全局最大值**：在所有听牌玩家中，选择最高的最大可能番数作为 `ready_players_max_fans`

### 关键点

1. **遍历所有可听牌**：必须遍历 `ready_tiles` 中的每一张牌，不能只取第一张
2. **计算完整番数**：包括基础番数和根数倍率（2^根数）
3. **不考虑动作加成**：在流局结算时，无法确定玩家会以什么方式胡牌，因此不考虑动作加成（自摸、杠上开花等）
4. **龙七对特殊处理**：龙七对的基础番数已经包含了根数倍率，需要特殊处理

### 改进

在最新实现中，我们改进了龙七对的处理：

```rust
// 对于龙七对，需要特殊处理
let total = if win_result.win_type == WinType::DragonSevenPairs {
    // 龙七对的基础番数已经包含了根数倍率
    BaseFansCalculator::dragon_seven_pairs_fans(roots)
} else {
    // 其他牌型：基础番 × 2^根数
    Settlement::new(base_fans, roots, 0).total_fans().unwrap_or(0)
};
```

## 测试建议

### 测试场景1：单玩家多张可听牌

- 玩家听1万（平胡，1番）和7万（清一色，4番）
- 验证：`ready_players_max_fans` 应该是 4

### 测试场景2：多个听牌玩家

- 玩家0听牌，最高可能4番
- 玩家1听牌，最高可能8番
- 玩家2未听牌
- 验证：玩家2应该按8番赔付

### 测试场景3：龙七对

- 玩家听龙七对（2根，16番）
- 验证：`ready_players_max_fans` 应该是 16

## 注意事项

1. **性能考虑**：遍历所有可听牌并计算番数可能比较耗时，但这是必要的，因为规则要求按最高番数赔付
2. **溢出处理**：如果番数计算溢出，应该跳过该牌，避免程序崩溃
3. **动作加成**：在流局结算时，不考虑动作加成是合理的，因为无法确定玩家会以什么方式胡牌

## 相关代码

- `GameEngine::final_settlement()`: 最终结算方法
- `Player::get_ready_tiles()`: 获取所有可听牌
- `BaseFansCalculator::base_fans()`: 计算基础番数
- `RootCounter::count_roots()`: 统计根数
- `Settlement::total_fans()`: 计算总番数

