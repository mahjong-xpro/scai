# "呼叫转移"状态机深度审计报告

## 问题描述

在血战到底中，杠钱的转移是有"物理记忆"的。如果 A 杠了 B 得到 2 分，随后 A 打出一张牌点炮给 C（杠上炮），规则要求 A 必须把刚从 B 那里收到的杠钱转给 C。

### 为什么重要

如果漏掉这个，AI 会变得非常喜欢盲目开杠，因为它意识不到杠牌后的点炮风险包含"收益没收"。

## 当前实现分析

### ✅ 已实现的部分

1. **InstantPayment 记录系统**：
   - `GameState` 中有 `instant_payments: Vec<InstantPayment>`
   - 在 `handle_gang` 中记录了每笔杠钱的支付记录（第281-287行）
   - `PaymentTracker` 提供了查找最近一次杠的支付者的方法

2. **杠上炮检查**：
   - 在 `handle_win_internal` 中检查了 `gang_history`（第482-507行）
   - 检查了 `gang_earnings` 是否大于0
   - 执行了杠上炮退税

### ❌ 潜在问题

#### 问题1：无法追溯到具体的支付者

**当前实现**：
```rust
// 在 handle_win_internal 中
if discarder.gang_earnings > 0 {
    let refund_amount = discarder.gang_earnings;
    gang_pao_refund = Some(GangSettlement::calculate_gang_pao_refund(
        discarder_id,
        player_id,
        refund_amount,
    ));
}
```

**问题**：
- `gang_earnings` 只是一个累计值，无法追溯到具体的支付者
- 如果 A 杠了 B 和 C 的牌（各2分），A 的 `gang_earnings` 是 4 分
- 但如果 A 点炮给 D，应该退还的是"最近一次杠的钱"（2分），而不是所有杠钱（4分）

**正确实现**：
应该使用 `PaymentTracker::get_latest_kong_payers` 来获取最近一次杠的支付者列表，然后只退还最近一次杠的钱。

#### 问题2：无法确认是否是"紧跟在杠之后"

**当前实现**：
```rust
if let Some(last_gang) = self.state.gang_history.last() {
    if last_gang.player_id == discarder_id {
        let turn_diff = self.state.turn.saturating_sub(last_gang.turn);
        if turn_diff <= 1 {
            // 执行退税
        }
    }
}
```

**问题**：
- 只检查了 `turn_diff <= 1`，但这不够精确
- 如果 A 杠了牌，然后 B 摸牌、出牌，然后 A 再摸牌、出牌点炮，`turn_diff` 可能是 2，但这不是"紧跟在杠之后"
- 需要检查：点炮的出牌动作是否紧跟在杠动作之后（中间没有其他玩家的动作）

**正确实现**：
应该检查 `last_action` 是否是 `Action::Gang`，或者检查 `discard_history` 中最近一次弃牌是否是点炮者，且之前是杠动作。

#### 问题3：没有记录"呼叫转移"的支付记录

**当前实现**：
- 杠上炮退税只更新了 `gang_earnings`，但没有在 `instant_payments` 中记录退税记录
- 这导致无法追溯"这笔钱是从哪里来的"

**正确实现**：
应该在 `instant_payments` 中记录退税记录，使用 `PaymentReason::GangPaoRefund`。

## 改进方案

### 方案1：使用 InstantPayment 追溯杠钱来源

在 `handle_win_internal` 中：

```rust
// 检查是否是杠上炮
if let Some((discarder_id, tile)) = discard_info {
    // 使用 PaymentTracker 获取最近一次杠的支付者
    let latest_kong_payers = PaymentTracker::get_latest_kong_payers(
        &self.state.instant_payments,
        discarder_id,
    );
    
    if !latest_kong_payers.is_empty() {
        // 检查是否是"紧跟在杠之后"
        // 方法1：检查 last_action 是否是 Gang
        let is_immediately_after_gang = matches!(
            self.state.last_action,
            Some(Action::Gang { .. })
        );
        
        // 方法2：检查 discard_history 中最近一次弃牌是否是点炮者
        let is_discarder_last_discard = self.state.discard_history
            .last()
            .map(|r| r.player_id == discarder_id)
            .unwrap_or(false);
        
        if is_immediately_after_gang && is_discarder_last_discard {
            // 计算最近一次杠的总收入
            let refund_amount: i32 = latest_kong_payers
                .iter()
                .map(|(_, amount)| *amount)
                .sum();
            
            // 执行杠上炮退税
            gang_pao_refund = Some(GangSettlement::calculate_gang_pao_refund(
                discarder_id,
                player_id,
                refund_amount,
            ));
            
            // 记录退税支付记录
            let refund_payment = InstantPayment::new(
                discarder_id,
                player_id,
                refund_amount,
                PaymentReason::GangPaoRefund,
                self.state.turn,
                Some(tile),
            );
            self.state.instant_payments.push(refund_payment);
            
            // 更新玩家杠钱收入
            self.state.players[discarder_id as usize].gang_earnings -= refund_amount;
            self.state.players[player_id as usize].add_gang_earnings(refund_amount);
        }
    }
}
```

### 方案2：在 GameState 中记录"最近一次动作"

添加一个字段来记录最近一次动作的类型和玩家：

```rust
pub struct GameState {
    // ...
    pub last_action: Option<Action>,
    pub last_action_player: Option<u8>, // 新增：记录最近一次动作的玩家
    // ...
}
```

这样可以更精确地判断是否是"紧跟在杠之后"。

## 推荐实现

**推荐方案1**，因为：
1. 不需要修改 `GameState` 结构
2. 使用现有的 `instant_payments` 系统
3. 可以精确追溯到杠钱的来源
4. 符合"呼叫转移"的物理记忆要求

## 测试用例

应该添加测试用例来验证：
1. A 杠了 B 的牌（2分），然后 A 点炮给 C，应该退还 2 分给 C
2. A 杠了 B 和 C 的牌（各2分），然后 A 点炮给 D，应该只退还最近一次杠的钱（2分）
3. A 杠了 B 的牌，然后 B 摸牌、出牌，然后 A 再摸牌、出牌点炮给 C，应该退还 2 分给 C（因为中间有其他玩家的动作，但仍然是"紧跟在杠之后"）

