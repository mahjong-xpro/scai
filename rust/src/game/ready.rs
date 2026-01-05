use crate::tile::{Hand, Tile};
use crate::game::scoring::Meld;
use crate::tile::win_check::WinChecker;

/// 听牌判定器
pub struct ReadyChecker;

impl ReadyChecker {
    /// 检查玩家是否听牌
    /// 
    /// 听牌定义：手牌差一张就能胡牌
    /// 
    /// # 参数
    /// 
    /// - `hand`: 手牌
    /// - `melds`: 已碰/杠的牌组
    /// 
    /// # 返回
    /// 
    /// 如果可以听牌，返回所有可以听的牌（Vec<Tile>），否则返回空向量
    pub fn check_ready(hand: &Hand, melds: &[Meld]) -> Vec<Tile> {
        let mut ready_tiles = Vec::new();
        let mut checker = WinChecker::new();
        
        // 尝试添加每种可能的牌，检查是否能胡
        // 遍历所有可能的牌（万、筒、条，1-9）
        for suit in [crate::tile::Suit::Wan, crate::tile::Suit::Tong, crate::tile::Suit::Tiao] {
            for rank in 1..=9 {
                let test_tile = match suit {
                    crate::tile::Suit::Wan => Tile::Wan(rank),
                    crate::tile::Suit::Tong => Tile::Tong(rank),
                    crate::tile::Suit::Tiao => Tile::Tiao(rank),
                };
                
                // 检查手牌中是否已经有 4 张（不能再添加）
                let current_count = hand.tiles_map()
                    .get(&test_tile)
                    .copied()
                    .unwrap_or(0);
                if current_count >= 4 {
                    continue;
                }
                
                // 创建测试手牌（添加这张牌）
                let mut test_hand = hand.clone();
                test_hand.add_tile(test_tile);
                
                // 检查是否能胡牌
                let melds_count = melds.len() as u8;
                let result = checker.check_win_with_melds(&test_hand, melds_count);
                
                if result.is_win {
                    ready_tiles.push(test_tile);
                }
            }
        }
        
        ready_tiles
    }

    /// 检查是否听牌（简化版本，只返回 bool）
    /// 
    /// # 参数
    /// 
    /// - `hand`: 手牌
    /// - `melds`: 已碰/杠的牌组
    /// 
    /// # 返回
    /// 
    /// 是否听牌
    pub fn is_ready(hand: &Hand, melds: &[Meld]) -> bool {
        !ReadyChecker::check_ready(hand, melds).is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_ready() {
        let mut hand = Hand::new();
        // 13 张牌，差一张就能胡
        // 对子：1万-1万
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        // 顺子1：2万-3万-4万
        hand.add_tile(Tile::Wan(2));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Wan(4));
        // 顺子2：5万-6万-7万
        hand.add_tile(Tile::Wan(5));
        hand.add_tile(Tile::Wan(6));
        hand.add_tile(Tile::Wan(7));
        // 顺子3：1筒-2筒-3筒
        hand.add_tile(Tile::Tong(1));
        hand.add_tile(Tile::Tong(2));
        hand.add_tile(Tile::Tong(3));
        // 顺子4：5筒-6筒（差一张 7 筒）
        hand.add_tile(Tile::Tong(5));
        hand.add_tile(Tile::Tong(6));
        
        let melds = vec![];
        assert!(ReadyChecker::is_ready(&hand, &melds));
        
        // 检查可以听的牌
        let ready_tiles = ReadyChecker::check_ready(&hand, &melds);
        assert!(ready_tiles.contains(&Tile::Tong(7)));
    }

    #[test]
    fn test_not_ready() {
        let mut hand = Hand::new();
        // 随机牌，不构成听牌
        for rank in 1..=13 {
            hand.add_tile(Tile::Wan(rank.min(9)));
        }
        
        let melds = vec![];
        assert!(!ReadyChecker::is_ready(&hand, &melds));
    }
}

