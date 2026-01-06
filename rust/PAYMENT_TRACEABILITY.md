# 结算系统追溯性实现 (Payment Traceability)

## 问题描述

血战到底的结算不是一次性的，而是具有回溯性质的。当玩家杠牌时，需要记录每笔交易的来源，以便在以下情况下能够追溯：

1. **杠上炮退税**：如果玩家 A 杠了 B 的牌，随后 A 点炮给 C，A 必须把刚从 B 那里收到的杠钱转给 C。
2. **查大叫退税**：流局时，没听牌的人必须把本局收到的所有杠钱退还，需要准确找到原始支付者。
3. **查花猪退税**：如果杠牌者被查出花猪，也需要退税给原始支付者。

## 实现方案

### 1. 即时支付记录 (InstantPayment)

创建了 `InstantPayment` 结构体，记录每笔即时交易的详细信息：

```rust
pub struct InstantPayment {
    pub from_player: u8,      // 支付者 ID
    pub to_player: u8,        // 接收者 ID
    pub amount: i32,          // 金额（正数）
    pub reason: PaymentReason, // 原因（暗杠、明杠、退税等）
    pub turn: u32,            // 交易回合数
    pub related_tile: Option<Tile>, // 关联的牌（如果有）
}
```

### 2. 支付原因枚举 (PaymentReason)

定义了各种支付原因：

- `ConcealedKong`: 暗杠
- `DirectKong`: 明杠（直杠）
- `AddKong`: 加杠
- `NotReady`: 查大叫（未听牌赔付）
- `FlowerPig`: 查花猪（未打完缺门赔付）
- `GangPaoRefund`: 杠上炮退税
- `NotReadyRefund`: 查大叫退税
- `FlowerPigRefund`: 查花猪退税

### 3. 支付记录管理器 (PaymentTracker)

提供了以下工具方法：

- `from_settlement()`: 从结算结果创建即时支付记录
- `get_kong_payments_received()`: 查找指定玩家收到的所有杠钱支付记录
- `get_kong_payments_paid()`: 查找指定玩家支付的所有杠钱记录
- `calculate_total_kong_earnings()`: 计算指定玩家收到的总杠钱
- `get_latest_kong_payers()`: 获取指定玩家最近一次杠钱的支付者列表

### 4. 游戏状态扩展

在 `GameState` 中添加了 `instant_payments: Vec<InstantPayment>` 字段，用于存储所有即时支付记录。

## 使用场景

### 场景1: 杠牌时记录支付

```rust
// 在 handle_gang 中
let settlement = GangSettlement::calculate_gang_payment(player_id, is_concealed, &players);

// 记录即时支付
let payment_reason = if is_concealed {
    PaymentReason::ConcealedKong
} else {
    PaymentReason::DirectKong
};
let instant_payments = PaymentTracker::from_settlement(
    &settlement,
    payment_reason,
    self.state.turn,
    Some(tile),
);
self.state.instant_payments.extend(instant_payments);
```

### 场景2: 杠上炮退税

```rust
// 在 handle_win_internal 中
// 使用追溯系统找到最近一次杠钱的支付者
let latest_payers = PaymentTracker::get_latest_kong_payers(
    &self.state.instant_payments,
    discarder_id,
);

// 计算需要退还的总金额
let refund_amount: i32 = latest_payers.iter().map(|(_, amount)| *amount).sum();

// 创建杠上炮退税记录
let refund_payment = InstantPayment::new(
    discarder_id,
    player_id,
    refund_amount,
    PaymentReason::GangPaoRefund,
    self.state.turn,
    Some(tile),
);
self.state.instant_payments.push(refund_payment);
```

### 场景3: 查大叫退税

```rust
// 在 final_settlement 中
// 获取该玩家收到的所有杠钱支付记录
let kong_payments = PaymentTracker::get_kong_payments_received(
    &self.state.instant_payments,
    player.id,
);

// 按支付者分组，计算每个支付者应该收到多少退款
let mut payer_refunds: HashMap<u8, i32> = HashMap::new();
for payment in kong_payments {
    *payer_refunds.entry(payment.from_player).or_insert(0) += payment.amount;
}

// 创建退税记录
for (&payer_id, &amount) in &payer_refunds {
    let refund_payment = InstantPayment::new(
        player.id,
        payer_id,
        amount,
        PaymentReason::NotReadyRefund,
        self.state.turn,
        None,
    );
    self.state.instant_payments.push(refund_payment);
}
```

## 优势

1. **完整追溯**：每笔交易都有完整的记录，包括支付者、接收者、金额、原因和回合数。
2. **准确退税**：能够准确找到原始支付者，确保退税的正确性。
3. **审计友好**：所有交易记录都保存在 `instant_payments` 中，便于审计和调试。
4. **扩展性强**：可以轻松添加新的支付原因和追溯逻辑。

## 测试建议

1. **杠上炮退税测试**：
   - 玩家 A 杠了玩家 B 的牌，收到 3 分
   - 玩家 A 点炮给玩家 C
   - 验证：玩家 A 的杠钱转给玩家 C，且 `instant_payments` 中有正确的退税记录

2. **查大叫退税测试**：
   - 玩家 A 杠了玩家 B、C、D 的牌，分别收到 1 分、1 分、1 分
   - 流局时玩家 A 未听牌
   - 验证：玩家 A 退还 3 分，分别给玩家 B、C、D 各 1 分

3. **查花猪退税测试**：
   - 玩家 A 杠了玩家 B 的牌，收到 1 分
   - 流局时玩家 A 被查出花猪
   - 验证：玩家 A 退还 1 分给玩家 B

## 文件结构

- `rust/src/game/payment.rs`: 支付记录和追溯系统实现
- `rust/src/game/state.rs`: 在 `GameState` 中添加 `instant_payments` 字段
- `rust/src/game/game_engine.rs`: 在杠牌、胡牌、流局结算时使用追溯系统

