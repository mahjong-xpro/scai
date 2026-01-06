use crate::tile::{Hand, Tile};
use crate::game::scoring::Meld;

/// 向听数计算器
/// 
/// 向听数（Shanten Number）：表示当前手牌距离听牌还需要多少步
/// - 0: 已听牌
/// - 1: 一向听（差1张牌听牌）
/// - 2: 二向听（差2张牌听牌）
/// - 3+: 三向听及以上
pub struct ShantenCalculator;

impl ShantenCalculator {
    /// 计算向听数
    /// 
    /// # 参数
    /// 
    /// - `hand`: 手牌
    /// - `melds`: 已碰/杠的牌组
    /// 
    /// # 返回
    /// 
    /// 向听数（0 表示已听牌，数值越大表示距离听牌越远）
    /// 
    /// # 算法说明
    /// 
    /// 使用动态规划或贪心算法计算向听数：
    /// 1. 如果已听牌，返回 0
    /// 2. 否则，尝试所有可能的摸牌/打牌组合，找到最短路径
    /// 3. 简化实现：计算手牌中"不完整"的组合数量
    pub fn calculate_shanten(hand: &Hand, melds: &[Meld]) -> u8 {
        use crate::game::ready::ReadyChecker;
        
        // 如果已听牌，向听数为 0
        if ReadyChecker::is_ready(hand, melds) {
            return 0;
        }
        
        // 计算手牌中不完整的组合数量
        // 简化算法：统计需要补充的牌数
        let mut shanten = Self::_calculate_shanten_simple(hand, melds);
        
        // 限制最大向听数（通常不超过 8）
        shanten.min(8)
    }
    
    /// 简化版向听数计算
    /// 
    /// 基于手牌结构估算向听数：
    /// - 统计手牌中的对子、刻子、顺子数量
    /// - 计算需要补充的组合数
    fn _calculate_shanten_simple(hand: &Hand, melds: &[Meld]) -> u8 {
        let hand_size = hand.total_count();
        let melds_count = melds.len() as u8;
        
        // 标准手牌：13张手牌 + 4个组合（3个顺子/刻子 + 1个对子）
        // 如果已有 melds，需要的组合数减少
        let needed_combinations = 4 - melds_count;
        
        // 估算需要的牌数
        // 每个组合需要3张牌（顺子或刻子），对子需要2张
        // 如果手牌中已经有部分组合，需要的牌数会减少
        let mut incomplete_combinations = 0;
        let mut pairs = 0;
        
        // 统计手牌中的对子和刻子
        let tiles_map = hand.tiles_map();
        for (_, &count) in tiles_map.iter() {
            if count >= 2 {
                pairs += 1;
            }
            if count >= 3 {
                incomplete_combinations += 1; // 刻子
            }
        }
        
        // 估算顺子数量（简化：假设相邻的牌可以组成顺子）
        // 这里使用更简单的估算：手牌中不同牌型的数量
        let unique_tiles = tiles_map.len();
        
        // 计算向听数
        // 基本公式：需要的组合数 - 已有的组合数
        let mut shanten = needed_combinations.saturating_sub(melds_count as u8);
        
        // 如果手牌中已经有对子，可以减少向听数
        if pairs > 0 {
            shanten = shanten.saturating_sub(1);
        }
        
        // 如果手牌中已经有刻子，可以减少向听数
        if incomplete_combinations > 0 {
            shanten = shanten.saturating_sub(incomplete_combinations.min(3));
        }
        
        // 根据手牌大小调整
        // 如果手牌很少，向听数应该更大
        if hand_size < 10 {
            shanten += (10 - hand_size) / 2;
        }
        
        shanten
    }
    
    /// 计算向听数（更精确的算法）
    /// 
    /// 使用递归搜索所有可能的组合，找到最短路径
    /// 这是一个更精确但更慢的算法
    pub fn calculate_shanten_precise(hand: &Hand, melds: &[Meld]) -> u8 {
        use crate::game::ready::ReadyChecker;
        
        // 如果已听牌，向听数为 0
        if ReadyChecker::is_ready(hand, melds) {
            return 0;
        }
        
        // 使用递归搜索（限制深度以提高性能）
        Self::_search_shanten(hand, melds, 0, 8)
    }
    
    /// 递归搜索向听数
    fn _search_shanten(hand: &Hand, melds: &[Meld], depth: u8, max_depth: u8) -> u8 {
        use crate::game::ready::ReadyChecker;
        
        if depth >= max_depth {
            return max_depth;
        }
        
        // 如果已听牌，返回当前深度
        if ReadyChecker::is_ready(hand, melds) {
            return depth;
        }
        
        // 尝试所有可能的摸牌
        let mut min_shanten = max_depth;
        
        for suit in [crate::tile::Suit::Wan, crate::tile::Suit::Tong, crate::tile::Suit::Tiao] {
            for rank in 1..=9 {
                let test_tile = match suit {
                    crate::tile::Suit::Wan => Tile::Wan(rank),
                    crate::tile::Suit::Tong => Tile::Tong(rank),
                    crate::tile::Suit::Tiao => Tile::Tiao(rank),
                };
                
                // 检查是否可以添加这张牌
                let current_count = hand.tiles_map()
                    .get(&test_tile)
                    .copied()
                    .unwrap_or(0);
                if current_count >= 4 {
                    continue;
                }
                
                // 创建测试手牌
                let mut test_hand = hand.clone();
                test_hand.add_tile(test_tile);
                
                // 递归搜索
                let shanten = Self::_search_shanten(&test_hand, melds, depth + 1, max_depth);
                min_shanten = min_shanten.min(shanten);
            }
        }
        
        min_shanten
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shanten_ready() {
        let mut hand = Hand::new();
        // 听牌手牌：13张，差1张就能胡
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(2));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Wan(4));
        hand.add_tile(Tile::Wan(5));
        hand.add_tile(Tile::Wan(6));
        hand.add_tile(Tile::Wan(7));
        hand.add_tile(Tile::Tong(1));
        hand.add_tile(Tile::Tong(2));
        hand.add_tile(Tile::Tong(3));
        hand.add_tile(Tile::Tong(5));
        hand.add_tile(Tile::Tong(6));
        
        let melds = vec![];
        let shanten = ShantenCalculator::calculate_shanten(&hand, &melds);
        assert_eq!(shanten, 0, "听牌手牌的向听数应该为 0");
    }

    #[test]
    fn test_shanten_one_away() {
        let mut hand = Hand::new();
        // 一向听：差1张牌听牌
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(2));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Wan(4));
        hand.add_tile(Tile::Wan(5));
        hand.add_tile(Tile::Wan(6));
        hand.add_tile(Tile::Tong(1));
        hand.add_tile(Tile::Tong(2));
        hand.add_tile(Tile::Tong(3));
        hand.add_tile(Tile::Tong(5));
        hand.add_tile(Tile::Tong(6));
        
        let melds = vec![];
        let shanten = ShantenCalculator::calculate_shanten(&hand, &melds);
        assert!(shanten <= 1, "一向听手牌的向听数应该 <= 1");
    }
}

