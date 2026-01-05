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
}

