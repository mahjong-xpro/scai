# 杠钱退税逻辑修复

## 问题描述

血战到底的杠钱是即时结算的，但存在"追溯期"。原实现存在两个逻辑缺陷：

1. **杠上炮退税缺失**：当 A 玩家杠牌后点炮给 B，A 必须把刚才收到的杠钱全部转交给 B
2. **查大叫退税不完整**：在流局（牌抓完）时，没听牌的人必须把本局收到的所有杠钱退还

## 修复内容

### 1. 杠上炮退税（呼叫转移）

#### 实现位置
- `rust/src/game/game_engine.rs::handle_win_internal()`

#### 逻辑
当点炮胡发生时：
1. 检查点炮者是否刚刚杠过牌（通过 `last_action` 和 `gang_earnings`）
2. 如果点炮者刚刚杠过牌，执行杠上炮退税：
   - 点炮者把杠钱全部转交给胡牌者
   - 更新双方的 `gang_earnings`
3. 将退税信息添加到 `ActionResult::Won` 的 `gang_pao_refund` 字段

#### 代码示例

```rust
// 检查是否是杠上炮
if let Some(Action::Gang { .. }) = self.state.last_action {
    let discarder = &self.state.players[discarder_id as usize];
    if discarder.gang_earnings > 0 {
        // 执行杠上炮退税
        let refund_amount = discarder.gang_earnings;
        gang_pao_refund = Some(GangSettlement::calculate_gang_pao_refund(
            discarder_id,
            player_id,
            refund_amount,
        ));
        
        // 更新玩家杠钱收入
        self.state.players[discarder_id as usize].gang_earnings = 0;
        self.state.players[player_id as usize].add_gang_earnings(refund_amount);
    }
}
```

### 2. 查大叫退税（流局时未听牌玩家退还杠钱）

#### 实现位置
- `rust/src/game/game_engine.rs::final_settlement()`

#### 逻辑
在流局结算时：
1. **第一步：查大叫退税**
   - 遍历所有未离场的玩家
   - 如果玩家未听牌且有杠钱收入，必须退还所有杠钱
   - 杠钱退还给所有其他未离场的玩家（平均分配）

2. **第二步：查花猪退税**
   - 遍历所有杠牌记录
   - 如果杠牌者已听牌但被查出花猪，也需要退税
   - 注意：未听牌的杠牌者已在第一步处理

#### 代码示例

```rust
// 4. 查大叫退税（流局时，没听牌的人必须把本局收到的所有杠钱退还）
for player in &self.state.players {
    if !player.is_out && !player.is_ready {
        let refund_amount = player.gang_earnings;
        if refund_amount > 0 {
            let original_payers: Vec<u8> = (0..4u8)
                .filter(|&id| id != player.id && !self.state.players[id as usize].is_out)
                .collect();
            
            if !original_payers.is_empty() {
                let refund_settlement = FinalSettlement::refund_gang_money(
                    player.id,
                    refund_amount,
                    &original_payers,
                );
                all_settlements.push(refund_settlement);
            }
        }
    }
}
```

## 测试覆盖

新增了 `tests/gang_refund_test.rs`，包含以下测试：

1. `test_gang_pao_refund`: 测试杠上炮退税的基本逻辑
2. `test_not_ready_refund`: 测试单个未听牌玩家的查大叫退税
3. `test_multiple_not_ready_refund`: 测试多个未听牌玩家的查大叫退税

所有测试均通过 ✅

## 关键改进

### 1. ActionResult::Won 增强

添加了 `gang_pao_refund` 字段，用于记录杠上炮退税信息：

```rust
pub enum ActionResult {
    Won { 
        player_id: u8, 
        win_result: WinResult, 
        settlement: Settlement, 
        can_continue: bool,
        discarder_id: Option<u8>,
        gang_pao_refund: Option<SettlementResult>, // 新增
    },
    // ...
}
```

### 2. 退税逻辑分离

将退税逻辑分为两个独立的部分：
- **查大叫退税**：所有未听牌玩家退还杠钱
- **查花猪退税**：已听牌但被查出花猪的杠牌者退还杠钱

这样可以避免重复处理，确保逻辑清晰。

### 3. 原始支付者识别

在退税时，正确识别原始支付者：
- 对于查大叫退税：所有其他未离场的玩家
- 对于查花猪退税：所有非杠牌者的未离场玩家

## 使用场景

### 场景 1：杠上炮

```
1. 玩家 A 杠牌，收到 6 分（来自玩家 B、C、D）
2. 玩家 A 出牌，点炮给玩家 E
3. 玩家 A 必须把 6 分全部转交给玩家 E
```

### 场景 2：查大叫退税

```
1. 流局时，玩家 A 未听牌，但之前杠牌收了 6 分
2. 玩家 A 必须退还 6 分
3. 6 分平均分配给其他未离场的玩家（B、C、D 各得 2 分）
```

### 场景 3：多个未听牌玩家

```
1. 流局时，玩家 A 和 B 都未听牌
2. 玩家 A 杠牌收了 6 分，玩家 B 杠牌收了 3 分
3. 玩家 A 退还 6 分给 B、C、D（各 2 分）
4. 玩家 B 退还 3 分给 A、C、D（各 1 分）
```

## 注意事项

1. **杠上炮退税是即时执行的**：在点炮胡发生时立即执行，不需要等到流局
2. **查大叫退税只在流局时执行**：只有在牌抓完时才检查未听牌玩家的杠钱
3. **杠钱收入会实时更新**：杠上炮退税会立即更新双方的 `gang_earnings`
4. **避免重复退税**：查大叫退税和查花猪退税分开处理，避免重复

## 修复完成

✅ 杠上炮退税已实现并测试通过
✅ 查大叫退税已实现并测试通过
✅ 所有现有测试仍然通过
✅ 代码编译无错误

