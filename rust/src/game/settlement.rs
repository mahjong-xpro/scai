use crate::game::player::Player;
use std::collections::HashMap;

/// 结算结果
#[derive(Debug, Clone)]
pub struct SettlementResult {
    /// 玩家 ID -> 结算金额（正数表示收入，负数表示支出）
    pub payments: HashMap<u8, i32>,
    /// 结算说明
    pub description: String,
}

/// 刮风下雨结算器
pub struct GangSettlement;

impl GangSettlement {
    /// 计算杠钱结算（即时结算）
    /// 
    /// # 参数
    /// 
    /// - `gang_player_id`: 杠牌玩家 ID
    /// - `is_concealed`: 是否暗杠
    /// - `players`: 所有玩家
    /// 
    /// # 返回
    /// 
    /// 结算结果
    pub fn calculate_gang_payment(
        gang_player_id: u8,
        is_concealed: bool,
        players: &[Player; 4],
    ) -> SettlementResult {
        let mut payments = HashMap::new();
        
        // 暗杠：每人给 2 分
        // 明杠：点杠者给 1 分，其他人给 1 分
        let base_amount = if is_concealed { 2 } else { 1 };
        
        for player in players {
            if player.id != gang_player_id && !player.is_out {
                payments.insert(player.id, -base_amount);
            }
        }
        
        // 杠牌者收入
        let total_income: i32 = payments.values().sum::<i32>().abs();
        payments.insert(gang_player_id, total_income);
        
        let description = if is_concealed {
            format!("玩家 {} 暗杠，每人给 2 分", gang_player_id)
        } else {
            format!("玩家 {} 明杠，每人给 1 分", gang_player_id)
        };
        
        SettlementResult {
            payments,
            description,
        }
    }

    /// 杠上炮退税（呼叫转移）
    /// 
    /// # 参数
    /// 
    /// - `gang_player_id`: 杠牌玩家 ID
    /// - `win_player_id`: 胡牌玩家 ID
    /// - `gang_earnings`: 杠牌时收到的钱
    /// 
    /// # 返回
    /// 
    /// 结算结果
    pub fn calculate_gang_pao_refund(
        gang_player_id: u8,
        win_player_id: u8,
        gang_earnings: i32,
    ) -> SettlementResult {
        let mut payments = HashMap::new();
        
        // 杠牌者退还杠钱给胡牌者
        payments.insert(gang_player_id, -gang_earnings);
        payments.insert(win_player_id, gang_earnings);
        
        SettlementResult {
            payments,
            description: format!(
                "玩家 {} 杠上炮，退还 {} 分给玩家 {}",
                gang_player_id, gang_earnings, win_player_id
            ),
        }
    }
}

/// 局末结算器
pub struct FinalSettlement;

impl FinalSettlement {
    /// 查花猪（未打完缺门赔付）
    /// 
    /// # 参数
    /// 
    /// - `players`: 所有玩家
    /// - `max_fans`: 全场最大番数
    /// 
    /// # 返回
    /// 
    /// 结算结果
    pub fn check_flower_pig(
        players: &[Player; 4],
        max_fans: u32,
    ) -> SettlementResult {
        let mut payments = HashMap::new();
        let mut flower_pigs = Vec::new();
        
        // 找出花猪（还有定缺门牌的玩家）
        for player in players {
            if !player.is_out && player.has_declared_suit_tiles() {
                flower_pigs.push(player.id);
            }
        }
        
        if flower_pigs.is_empty() {
            return SettlementResult {
                payments: HashMap::new(),
                description: "无花猪".to_string(),
            };
        }
        
        // 花猪赔给所有非花猪玩家（按最大番数）
        let penalty_per_player = max_fans as i32;
        
        for player in players {
            if !player.is_out && !flower_pigs.contains(&player.id) {
                // 非花猪玩家收入
                let income = penalty_per_player * flower_pigs.len() as i32;
                payments.insert(player.id, income);
            } else if flower_pigs.contains(&player.id) {
                // 花猪玩家支出
                let num_non_pigs = players.iter()
                    .filter(|p| !p.is_out && !flower_pigs.contains(&p.id))
                    .count();
                let expense = -(penalty_per_player * num_non_pigs as i32);
                payments.insert(player.id, expense);
            }
        }
        
        SettlementResult {
            payments,
            description: format!(
                "查花猪：玩家 {:?} 未打完缺门，每人赔 {} 番",
                flower_pigs, max_fans
            ),
        }
    }

    /// 查大叫（未听牌赔付）
    /// 
    /// # 参数
    /// 
    /// - `players`: 所有玩家
    /// - `ready_players_max_fans`: 听牌玩家的最高番数
    /// 
    /// # 返回
    /// 
    /// 结算结果
    pub fn check_not_ready(
        players: &[Player; 4],
        ready_players_max_fans: u32,
    ) -> SettlementResult {
        let mut payments = HashMap::new();
        let mut not_ready_players = Vec::new();
        let mut ready_players = Vec::new();
        
        // 分类玩家
        for player in players {
            if !player.is_out {
                if player.is_ready {
                    ready_players.push(player.id);
                } else {
                    not_ready_players.push(player.id);
                }
            }
        }
        
        if not_ready_players.is_empty() {
            return SettlementResult {
                payments: HashMap::new(),
                description: "所有人已听牌".to_string(),
            };
        }
        
        // 未听牌玩家赔给听牌玩家（按听牌者最高番数）
        let penalty = ready_players_max_fans as i32;
        
        for &not_ready_id in &not_ready_players {
            // 未听牌玩家支出
            let expense = -(penalty * ready_players.len() as i32);
            payments.insert(not_ready_id, expense);
        }
        
        for &ready_id in &ready_players {
            // 听牌玩家收入
            let income = penalty * not_ready_players.len() as i32;
            *payments.entry(ready_id).or_insert(0) += income;
        }
        
        SettlementResult {
            payments,
            description: format!(
                "查大叫：玩家 {:?} 未听牌，每人赔 {} 番给听牌玩家 {:?}",
                not_ready_players, ready_players_max_fans, ready_players
            ),
        }
    }

    /// 退税（退还杠钱）
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 需要退税的玩家 ID
    /// - `refund_amount`: 退还金额
    /// - `original_payers`: 原始支付者列表
    /// 
    /// # 返回
    /// 
    /// 结算结果
    pub fn refund_gang_money(
        player_id: u8,
        refund_amount: i32,
        original_payers: &[u8],
    ) -> SettlementResult {
        let mut payments = HashMap::new();
        
        // 退还者支出
        payments.insert(player_id, -refund_amount);
        
        // 原始支付者收入（平均分配）
        let per_player_refund = refund_amount / original_payers.len() as i32;
        for &payer_id in original_payers {
            *payments.entry(payer_id).or_insert(0) += per_player_refund;
        }
        
        SettlementResult {
            payments,
            description: format!(
                "退税：玩家 {} 退还 {} 分给玩家 {:?}",
                player_id, refund_amount, original_payers
            ),
        }
    }
}

