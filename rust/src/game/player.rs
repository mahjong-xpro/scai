use crate::tile::{Hand, Tile, Suit};
use crate::game::scoring::Meld;

/// 玩家状态
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Player {
    /// 玩家 ID
    pub id: u8,
    /// 手牌
    pub hand: Hand,
    /// 已碰/杠的牌组
    pub melds: Vec<Meld>,
    /// 定缺的花色（None 表示未定缺）
    pub declared_suit: Option<Suit>,
    /// 是否已离场（胡牌或流局）
    pub is_out: bool,
    /// 是否听牌
    pub is_ready: bool,
    /// 累计杠钱收入（用于退税）
    pub gang_earnings: i32,
    /// 过胡锁定：记录放弃的点炮番数（None 表示未过胡）
    /// 
    /// 规则：如果玩家放弃了当前点炮，在下一次摸牌前，不能胡同一张牌或番数 <= 该记录值的点炮牌
    /// 注意：自摸不受此限制
    pub passed_hu_fan: Option<u32>,
    /// 过胡锁定的牌（None 表示未过胡）
    /// 
    /// 规则：如果玩家放弃了某张牌的点炮，在下一次摸牌前，不能胡同一张牌
    pub passed_hu_tile: Option<Tile>,
}

impl Player {
    /// 创建新玩家
    pub fn new(id: u8) -> Self {
        Self {
            id,
            hand: Hand::new(),
            melds: Vec::new(),
            declared_suit: None,
            is_out: false,
            is_ready: false,
            gang_earnings: 0,
            passed_hu_fan: None,
            passed_hu_tile: None,
        }
    }

    /// 定缺（三花色必缺一）
    /// 
    /// # 参数
    /// 
    /// - `suit`: 要定缺的花色（万、筒、条之一）
    /// 
    /// # 返回
    /// 
    /// 是否成功定缺
    pub fn declare_suit(&mut self, suit: Suit) -> bool {
        // 血战到底只有万、筒、条三种花色，都可以定缺
        self.declared_suit = Some(suit);
        true
    }

    /// 检查是否还有定缺门的牌
    pub fn has_declared_suit_tiles(&self) -> bool {
        if let Some(declared) = self.declared_suit {
            for (tile, _) in self.hand.tiles_map() {
                if tile.suit() == declared {
                    return true;
                }
            }
        }
        false
    }

    /// 标记玩家离场
    pub fn mark_out(&mut self) {
        self.is_out = true;
    }

    /// 标记听牌
    pub fn mark_ready(&mut self) {
        self.is_ready = true;
    }

    /// 添加杠钱收入
    pub fn add_gang_earnings(&mut self, amount: i32) {
        self.gang_earnings += amount;
    }

    /// 退还杠钱（退税）
    pub fn refund_gang_earnings(&mut self) -> i32 {
        let refund = self.gang_earnings;
        self.gang_earnings = 0;
        refund
    }

    /// 检查是否听牌
    /// 
    /// 使用 ReadyChecker 检查听牌状态
    pub fn check_ready(&mut self) {
        use crate::game::ready::ReadyChecker;
        self.is_ready = ReadyChecker::is_ready(&self.hand, &self.melds);
    }

    /// 获取所有可以听的牌
    /// 
    /// # 返回
    /// 
    /// 所有可以听的牌列表
    pub fn get_ready_tiles(&self) -> Vec<Tile> {
        use crate::game::ready::ReadyChecker;
        ReadyChecker::check_ready(&self.hand, &self.melds)
    }

    /// 获取所有可听牌（别名，用于更清晰的语义）
    /// 
    /// 这是 `get_ready_tiles()` 的别名，用于"查大叫"场景，语义更明确
    /// 
    /// # 返回
    /// 
    /// 所有可以听的牌列表
    pub fn get_shouting_tiles(&self) -> Vec<Tile> {
        self.get_ready_tiles()
    }

    /// 计算指定可听牌的最大可能番数
    /// 
    /// 用于"查大叫"结算，计算如果玩家胡这张牌，可能达到的最大番数。
    /// 
    /// # 参数
    /// 
    /// - `ready_tile`: 可听的牌
    /// 
    /// # 返回
    /// 
    /// 最大可能番数（如果该牌不能胡，返回 0）
    /// 
    /// # 注意
    /// 
    /// - 只计算基础番数和根数倍率
    /// - 不考虑动作加成（自摸、杠上开花等），因为流局结算时无法确定
    /// - 龙七对需要特殊处理（基础番数已包含根数倍率）
    pub fn calculate_max_fan_for_this_tile(&self, ready_tile: Tile) -> u32 {
        use crate::game::scoring::{BaseFansCalculator, RootCounter, Settlement};
        use crate::tile::win_check::{WinChecker, WinType};
        
        // 创建测试手牌（添加这张牌）
        let mut test_hand = self.hand.clone();
        test_hand.add_tile(ready_tile);
        
        // 检查是否能胡牌
        let mut checker = WinChecker::new();
        let melds_count = self.melds.len() as u8;
        let win_result = checker.check_win_with_melds(&test_hand, melds_count);
        
        if !win_result.is_win {
            return 0;
        }
        
        // 计算该胡牌类型的番数
        // 注意：在流局结算时，我们无法确定玩家会以什么方式胡牌（自摸/点炮），
        // 也无法确定是否会触发动作加成（杠上开花、海底捞月等）。
        // 因此，我们只计算基础番数和根数，不考虑动作加成。
        // 这是最保守的做法，确保未听牌玩家按听牌者可能达到的最高番数赔付。
        let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
        let roots = RootCounter::count_roots(&test_hand, &self.melds);
        
        // 对于龙七对，需要特殊处理
        if win_result.win_type == WinType::DragonSevenPairs {
            // 龙七对的基础番数已经包含了根数倍率
            BaseFansCalculator::dragon_seven_pairs_fans(roots)
        } else {
            // 其他牌型：基础番 × 2^根数
            Settlement::new(base_fans, roots, 0).total_fans().unwrap_or(0)
        }
    }

    /// 记录过胡（放弃点炮）
    /// 
    /// # 参数
    /// 
    /// - `tile`: 放弃的牌
    /// - `fans`: 放弃的点炮番数
    /// 
    /// 如果当前没有过胡记录，或新的番数更小，则更新记录
    pub fn record_passed_win(&mut self, tile: Tile, fans: u32) {
        match self.passed_hu_fan {
            None => {
                // 第一次过胡，直接记录
                self.passed_hu_fan = Some(fans);
                self.passed_hu_tile = Some(tile);
            }
            Some(existing_fans) => {
                // 如果新的番数更小，更新记录（取更严格的限制）
                if fans < existing_fans {
                    self.passed_hu_fan = Some(fans);
                    self.passed_hu_tile = Some(tile);
                }
            }
        }
    }

    /// 清除过胡锁定（在玩家摸牌后调用）
    /// 
    /// 规则：过胡锁定只在"下一次摸牌前"有效
    pub fn clear_passed_win(&mut self) {
        self.passed_hu_fan = None;
        self.passed_hu_tile = None;
    }

    /// 添加一张牌到手牌（自动清除过胡锁定）
    /// 
    /// 规则：只要手牌发生一次变化，即可清除过胡限制
    /// 
    /// # 参数
    /// 
    /// - `tile`: 要添加的牌
    /// 
    /// # 返回
    /// 
    /// 是否成功添加
    pub fn add_tile_to_hand(&mut self, tile: Tile) -> bool {
        let result = self.hand.add_tile(tile);
        if result {
            // 手牌发生变化，清除过胡锁定
            self.clear_passed_win();
        }
        result
    }

    /// 从手牌移除一张牌（自动清除过胡锁定）
    /// 
    /// 规则：只要手牌发生一次变化，即可清除过胡限制
    /// 
    /// # 参数
    /// 
    /// - `tile`: 要移除的牌
    /// 
    /// # 返回
    /// 
    /// 是否成功移除
    pub fn remove_tile_from_hand(&mut self, tile: Tile) -> bool {
        let result = self.hand.remove_tile(tile);
        if result {
            // 手牌发生变化，清除过胡锁定
            self.clear_passed_win();
        }
        result
    }
}

