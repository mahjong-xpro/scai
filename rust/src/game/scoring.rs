use crate::tile::{Hand, Tile};
use crate::tile::win_check::{WinResult, WinType};

/// 碰/杠（明牌组）
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Meld {
    /// 碰（刻子）
    Triplet { tile: Tile },
    /// 杠（明杠/暗杠）
    Kong { tile: Tile, is_concealed: bool },
}

/// 根（Gen）统计器
pub struct RootCounter;

impl RootCounter {
    /// 统计根的数量
    /// 
    /// # 参数
    /// 
    /// - `hand`: 手牌
    /// - `melds`: 已碰/杠的牌组
    /// 
    /// # 返回
    /// 
    /// 根的总数量（0-4）
    /// 
    /// # 实现逻辑
    /// 
    /// 使用统一的计数器数组统计所有可见牌（手牌 + 碰/杠），计数为 4 的张数即为根的总数。
    /// 这样可以避免重复计算，确保逻辑正确性。
    /// 
    /// 根的定义：只要手牌中有 4 张相同的牌（无论是否开杠），就是 1 个根。
    /// 注意：不能将"杠"等同于"根"，因为：
    /// - 如果手牌中有 4 张相同的牌（未开杠），计算 1 个根
    /// - 如果 4 张相同的牌被开杠了（变成 `Meld::Kong`），也应该计算 1 个根
    /// - 同一个 4 张相同的牌，不能既在手牌中计算，又在 `melds` 中计算
    #[inline]
    pub fn count_roots(hand: &Hand, melds: &[Meld]) -> u8 {
        // 建立计数器数组：27 种牌（3 种花色 × 9 种牌）
        // 索引计算：suit_index * 9 + (rank - 1)
        // - 万子：0-8 (0*9 + rank-1)
        // - 筒子：9-17 (1*9 + rank-1)
        // - 条子：18-26 (2*9 + rank-1)
        let mut tile_counts = [0u8; 27];
        
        // 辅助函数：将 Tile 转换为索引（0-26）
        #[inline]
        fn tile_to_index(tile: &Tile) -> Option<usize> {
            let suit_idx = match tile.suit() {
                crate::tile::Suit::Wan => 0,
                crate::tile::Suit::Tong => 1,
                crate::tile::Suit::Tiao => 2,
            };
            let rank = tile.rank();
            if rank < 1 || rank > 9 {
                return None;
            }
            Some(suit_idx * 9 + (rank - 1) as usize)
        }
        
        // 统计手牌中的牌
        for (tile, &count) in hand.tiles_map() {
            if let Some(idx) = tile_to_index(tile) {
                if idx < 27 {
                    tile_counts[idx] += count;
                }
            }
        }
        
        // 统计已碰/杠的牌
        for meld in melds {
            match meld {
                Meld::Triplet { .. } => {
                    // 碰：3 张相同的牌（不是根）
                    // 注意：碰不是根，只有 4 张相同的牌才是根
                }
                Meld::Kong { tile, .. } => {
                    // 杠：4 张相同的牌（是根）
                    if let Some(idx) = tile_to_index(tile) {
                        if idx < 27 {
                            tile_counts[idx] += 4;
                        }
                    }
                }
            }
        }
        
        // 统计计数为 4 的张数（即为根的总数）
        let mut root_count = 0u8;
        for &count in &tile_counts {
            if count == 4 {
                root_count += 1;
            }
        }
        
        // 确保不超过 4 个根
        root_count.min(4)
    }
}

/// 基础番数计算器
pub struct BaseFansCalculator;

impl BaseFansCalculator {
    /// 计算基础番数
    /// 
    /// # 参数
    /// 
    /// - `win_type`: 胡牌类型
    /// 
    /// # 返回
    /// 
    /// 基础番数
    #[inline]
    pub fn base_fans(win_type: WinType) -> u32 {
        match win_type {
            WinType::Normal => 1,                    // 2^0 = 1
            WinType::AllTriplets => 2,               // 2^1 = 2
            WinType::SevenPairs => 4,                // 2^2 = 4
            WinType::PureSuit => 4,                  // 2^2 = 4
            WinType::AllTerminals => 4,              // 2^2 = 4
            WinType::GoldenHook => 4,                // 2^2 = 4
            WinType::PureAllTriplets => 8,           // 2^(2+1) = 8
            WinType::PureSevenPairs => 16,           // 2^(2+2) = 16
            WinType::PureGoldenHook => 16,           // 2^(2+2) = 16
            WinType::PureDragonSevenPairs => 32,     // 2^(2+3) = 32
            WinType::DragonSevenPairs => {
                // 龙七对需要根据根数动态计算，这里返回基础值
                // 实际计算应该在 Settlement 中处理
                4 // 七对的基础值
            },
        }
    }

    /// 计算龙七对的基础番数（根据根数）
    /// 
    /// # 参数
    /// 
    /// - `roots`: 根的数量
    /// 
    /// # 返回
    /// 
    /// 龙七对的基础番数
    pub fn dragon_seven_pairs_fans(roots: u8) -> u32 {
        // 七对基础值 4 × 2^根数
        // 双龙七对（2 根）：4 × 2^2 = 16
        // 三龙七对（3 根）：4 × 2^3 = 32
        let base = 4u32;
        base * 2_u32.pow(roots as u32)
    }
}

/// 动作触发标志
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct ActionFlags {
    /// 是否自摸
    pub is_zi_mo: bool,
    /// 是否杠上开花
    pub is_gang_kai: bool,
    /// 是否杠上炮
    pub is_gang_pao: bool,
    /// 是否抢杠胡
    pub is_qiang_gang: bool,
    /// 是否海底捞月
    pub is_hai_di: bool,
}

impl ActionFlags {
    /// 创建空的 ActionFlags
    pub fn new() -> Self {
        Self::default()
    }

    /// 统计动作加成数量
    #[inline]
    pub fn count(&self) -> u8 {
        let mut count = 0u8;
        if self.is_zi_mo { count += 1; }
        if self.is_gang_kai { count += 1; }
        if self.is_gang_pao { count += 1; }
        if self.is_qiang_gang { count += 1; }
        if self.is_hai_di { count += 1; }
        count
    }
}

/// 结算结构体
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Settlement {
    /// 基础番
    pub base_pattern: u32,
    /// 根的数量
    pub roots: u8,
    /// 动作加成数量
    pub action_bonus: u8,
}

impl Settlement {
    /// 创建新的结算
    /// 
    /// # 参数
    /// 
    /// - `base_pattern`: 基础番
    /// - `roots`: 根的数量（0-4）
    /// - `action_bonus`: 动作加成数量（0-5）
    pub fn new(base_pattern: u32, roots: u8, action_bonus: u8) -> Self {
        Self {
            base_pattern,
            roots: roots.min(4),
            action_bonus: action_bonus.min(5),
        }
    }

    /// 计算总番数
    /// 
    /// # 公式
    /// 
    /// 总番数 = 基础番型 × 2^根数 × 2^动作加成数
    /// 
    /// # 返回
    /// 
    /// 总番数，如果溢出则返回 None
    #[inline]
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

    /// 从 WinResult 和游戏状态计算结算
    /// 
    /// # 参数
    /// 
    /// - `win_result`: 胡牌结果
    /// - `roots`: 根的数量
    /// - `actions`: 动作触发标志
    /// 
    /// # 返回
    /// 
    /// Settlement 实例
    /// 
    /// # 注意
    /// 
    /// 对于龙七对，基础番数已经包含了根数倍率，所以 roots 参数应该设为 0
    pub fn calculate(win_result: &WinResult, roots: u8, actions: &ActionFlags) -> Self {
        // 获取基础番数
        let base_pattern;
        let effective_roots;
        
        // 如果是龙七对，基础番数已经包含了根数倍率
        if win_result.win_type == WinType::DragonSevenPairs {
            base_pattern = BaseFansCalculator::dragon_seven_pairs_fans(roots);
            effective_roots = 0; // 根数倍率已经包含在基础番数中
        } else {
            base_pattern = BaseFansCalculator::base_fans(win_result.win_type);
            effective_roots = roots;
        }
        
        // 统计动作加成数量
        let action_bonus = actions.count();
        
        Self::new(base_pattern, effective_roots, action_bonus)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tile::win_check::WinResult;
    use smallvec::SmallVec;

    #[test]
    fn test_count_roots_hand_only() {
        let mut hand = Hand::new();
        // 4 张 1 万（1 个根）
        for _ in 0..4 {
            hand.add_tile(Tile::Wan(1));
        }
        // 其他牌
        for rank in 2..=5 {
            hand.add_tile(Tile::Wan(rank));
        }

        let roots = RootCounter::count_roots(&hand, &[]);
        assert_eq!(roots, 1);
    }

    #[test]
    fn test_count_roots_with_melds() {
        let hand = Hand::new();
        let melds = vec![
            Meld::Kong { tile: Tile::Wan(1), is_concealed: true },
            Meld::Kong { tile: Tile::Tong(5), is_concealed: false },
        ];

        let roots = RootCounter::count_roots(&hand, &melds);
        assert_eq!(roots, 2);
    }

    #[test]
    fn test_base_fans() {
        assert_eq!(BaseFansCalculator::base_fans(WinType::Normal), 1);
        assert_eq!(BaseFansCalculator::base_fans(WinType::AllTriplets), 2);
        assert_eq!(BaseFansCalculator::base_fans(WinType::SevenPairs), 4);
        assert_eq!(BaseFansCalculator::base_fans(WinType::PureSuit), 4);
        assert_eq!(BaseFansCalculator::base_fans(WinType::PureAllTriplets), 8);
        assert_eq!(BaseFansCalculator::base_fans(WinType::PureSevenPairs), 16);
        assert_eq!(BaseFansCalculator::base_fans(WinType::PureDragonSevenPairs), 32);
    }

    #[test]
    fn test_dragon_seven_pairs_fans() {
        assert_eq!(BaseFansCalculator::dragon_seven_pairs_fans(2), 16);
        assert_eq!(BaseFansCalculator::dragon_seven_pairs_fans(3), 32);
    }

    #[test]
    fn test_action_flags_count() {
        let mut flags = ActionFlags::new();
        assert_eq!(flags.count(), 0);

        flags.is_zi_mo = true;
        assert_eq!(flags.count(), 1);

        flags.is_gang_kai = true;
        assert_eq!(flags.count(), 2);

        flags.is_hai_di = true;
        assert_eq!(flags.count(), 3);
    }

    #[test]
    fn test_settlement_total_fans() {
        // 基础番 4，无根，无动作
        let settlement = Settlement::new(4, 0, 0);
        assert_eq!(settlement.total_fans(), Some(4));

        // 基础番 4，1 个根，无动作
        let settlement = Settlement::new(4, 1, 0);
        assert_eq!(settlement.total_fans(), Some(8));

        // 基础番 4，1 个根，1 个动作
        let settlement = Settlement::new(4, 1, 1);
        assert_eq!(settlement.total_fans(), Some(16));

        // 基础番 16，2 个根，1 个动作（清七对 + 双根 + 自摸）
        let settlement = Settlement::new(16, 2, 1);
        assert_eq!(settlement.total_fans(), Some(128));
    }

    #[test]
    fn test_settlement_calculate() {
        let win_result = WinResult {
            is_win: true,
            win_type: WinType::PureSevenPairs,
            pair: None,
            groups: SmallVec::new(),
        };

        let mut actions = ActionFlags::new();
        actions.is_zi_mo = true;

        let settlement = Settlement::calculate(&win_result, 1, &actions);
        // 清七对 16 + 1 根 ×2 + 自摸 ×2 = 16 × 2 × 2 = 64
        assert_eq!(settlement.total_fans(), Some(64));
    }
}

