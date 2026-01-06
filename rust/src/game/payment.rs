/// 即时支付记录
/// 
/// 记录每笔即时交易的详细信息，用于追溯和退税。
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstantPayment {
    /// 支付者 ID
    pub from_player: u8,
    /// 接收者 ID
    pub to_player: u8,
    /// 金额（正数）
    pub amount: i32,
    /// 原因（如 "暗杠"、"明杠"、"查大叫"等）
    pub reason: PaymentReason,
    /// 交易回合数
    pub turn: u32,
    /// 关联的牌（如果有，如杠的牌）
    pub related_tile: Option<crate::tile::Tile>,
}

/// 支付原因
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PaymentReason {
    /// 暗杠
    ConcealedKong,
    /// 明杠（直杠）
    DirectKong,
    /// 加杠
    AddKong,
    /// 查大叫（未听牌赔付）
    NotReady,
    /// 查花猪（未打完缺门赔付）
    FlowerPig,
    /// 杠上炮退税
    GangPaoRefund,
    /// 查大叫退税
    NotReadyRefund,
    /// 查花猪退税
    FlowerPigRefund,
}

impl InstantPayment {
    /// 创建新的即时支付记录
    pub fn new(
        from_player: u8,
        to_player: u8,
        amount: i32,
        reason: PaymentReason,
        turn: u32,
        related_tile: Option<crate::tile::Tile>,
    ) -> Self {
        Self {
            from_player,
            to_player,
            amount,
            reason,
            turn,
            related_tile,
        }
    }
    
    /// 检查是否是杠相关的支付
    pub fn is_kong_payment(&self) -> bool {
        matches!(
            self.reason,
            PaymentReason::ConcealedKong
                | PaymentReason::DirectKong
                | PaymentReason::AddKong
        )
    }
}

/// 支付记录管理器
pub struct PaymentTracker;

impl PaymentTracker {
    /// 从结算结果创建即时支付记录
    /// 
    /// # 参数
    /// 
    /// - `settlement`: 结算结果
    /// - `reason`: 支付原因
    /// - `turn`: 交易回合数
    /// - `related_tile`: 关联的牌（可选）
    /// 
    /// # 返回
    /// 
    /// 即时支付记录列表
    pub fn from_settlement(
        settlement: &crate::game::settlement::SettlementResult,
        reason: PaymentReason,
        turn: u32,
        related_tile: Option<crate::tile::Tile>,
    ) -> Vec<InstantPayment> {
        let mut payments = Vec::new();
        
        // 找出所有支付者和接收者
        let mut payers = Vec::new();
        let mut receivers = Vec::new();
        
        for (&player_id, &amount) in &settlement.payments {
            if amount < 0 {
                // 支付者（负数）
                payers.push((player_id, -amount));
            } else if amount > 0 {
                // 接收者（正数）
                receivers.push((player_id, amount));
            }
        }
        
        // 创建支付记录
        // 对于杠牌：每个支付者给接收者支付
        // 对于其他：通常是多个支付者给一个接收者，或一个支付者给多个接收者
        if receivers.len() == 1 {
            // 一个接收者，多个支付者
            let receiver = receivers[0];
            for &(payer_id, payer_amount) in &payers {
                payments.push(InstantPayment::new(
                    payer_id,
                    receiver.0,
                    payer_amount,
                    reason,
                    turn,
                    related_tile,
                ));
            }
        } else if payers.len() == 1 {
            // 一个支付者，多个接收者
            let payer = payers[0];
            for &(receiver_id, receiver_amount) in &receivers {
                payments.push(InstantPayment::new(
                    payer.0,
                    receiver_id,
                    receiver_amount,
                    reason,
                    turn,
                    related_tile,
                ));
            }
        } else {
            // 多对多：按比例分配（这种情况较少见）
            let total_paid: i32 = payers.iter().map(|(_, amount)| *amount).sum();
            let total_received: i32 = receivers.iter().map(|(_, amount)| *amount).sum();
            
            if total_paid == total_received {
                // 简单分配：每个支付者按比例给每个接收者
                for &(payer_id, payer_amount) in &payers {
                    for &(receiver_id, receiver_amount) in &receivers {
                        let proportion = payer_amount as f64 / total_paid as f64;
                        let amount = (receiver_amount as f64 * proportion) as i32;
                        if amount > 0 {
                            payments.push(InstantPayment::new(
                                payer_id,
                                receiver_id,
                                amount,
                                reason,
                                turn,
                                related_tile,
                            ));
                        }
                    }
                }
            }
        }
        
        payments
    }
    
    /// 查找指定玩家收到的所有杠钱支付记录
    /// 
    /// # 参数
    /// 
    /// - `payments`: 所有支付记录
    /// - `player_id`: 玩家 ID
    /// 
    /// # 返回
    /// 
    /// 该玩家收到的所有杠钱支付记录
    pub fn get_kong_payments_received(
        payments: &[InstantPayment],
        player_id: u8,
    ) -> Vec<&InstantPayment> {
        payments
            .iter()
            .filter(|p| p.to_player == player_id && p.is_kong_payment())
            .collect()
    }
    
    /// 查找指定玩家支付的所有杠钱记录
    /// 
    /// # 参数
    /// 
    /// - `payments`: 所有支付记录
    /// - `player_id`: 玩家 ID
    /// 
    /// # 返回
    /// 
    /// 该玩家支付的所有杠钱记录
    pub fn get_kong_payments_paid(
        payments: &[InstantPayment],
        player_id: u8,
    ) -> Vec<&InstantPayment> {
        payments
            .iter()
            .filter(|p| p.from_player == player_id && p.is_kong_payment())
            .collect()
    }
    
    /// 计算指定玩家收到的总杠钱（基于支付记录）
    /// 
    /// # 参数
    /// 
    /// - `payments`: 所有支付记录
    /// - `player_id`: 玩家 ID
    /// 
    /// # 返回
    /// 
    /// 总杠钱收入
    pub fn calculate_total_kong_earnings(
        payments: &[InstantPayment],
        player_id: u8,
    ) -> i32 {
        Self::get_kong_payments_received(payments, player_id)
            .iter()
            .map(|p| p.amount)
            .sum()
    }
    
    /// 获取指定玩家最近一次杠钱的支付者列表
    /// 
    /// # 参数
    /// 
    /// - `payments`: 所有支付记录
    /// - `player_id`: 玩家 ID
    /// 
    /// # 返回
    /// 
    /// 最近一次杠钱的支付者列表（from_player, amount）
    pub fn get_latest_kong_payers(
        payments: &[InstantPayment],
        player_id: u8,
    ) -> Vec<(u8, i32)> {
        // 找到最近一次杠钱支付（按turn排序）
        let mut kong_payments: Vec<&InstantPayment> = Self::get_kong_payments_received(payments, player_id);
        kong_payments.sort_by_key(|p| p.turn);
        
        if let Some(latest) = kong_payments.last() {
            // 找到同一回合的所有支付（可能是多个玩家支付）
            let latest_turn = latest.turn;
            kong_payments
                .iter()
                .filter(|p| p.turn == latest_turn)
                .map(|p| (p.from_player, p.amount))
                .collect()
        } else {
            Vec::new()
        }
    }
}

