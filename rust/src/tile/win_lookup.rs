use super::{Hand, Tile, Suit};
use std::collections::HashSet;

/// 手牌编码
/// 
/// 使用紧凑编码表示手牌状态，用于查表法
/// 编码方式：每个花色用 9 个数字（0-4）表示每张牌的数量
/// 总共 3 个花色 × 9 个数字 = 27 个数字，每个数字 0-4（3 位）
/// 总大小：27 × 3 = 81 位，可以用 u128 表示
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct HandCode(u128);

impl HandCode {
    /// 从手牌创建编码
    pub fn from_hand(hand: &Hand) -> Self {
        let mut code = 0u128;
        let mut bit_pos = 0;
        
        // 按花色和数字顺序编码
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            for rank in 1..=9 {
                let tile = match suit {
                    Suit::Wan => Tile::Wan(rank),
                    Suit::Tong => Tile::Tong(rank),
                    Suit::Tiao => Tile::Tiao(rank),
                };
                let count = hand.tile_count(tile) as u128;
                // 每个数量用 3 位存储（0-4）
                code |= count << bit_pos;
                bit_pos += 3;
            }
        }
        
        Self(code)
    }
    
    /// 获取指定牌的数量
    fn get_count(&self, suit: Suit, rank: u8) -> u8 {
        let suit_offset = match suit {
            Suit::Wan => 0,
            Suit::Tong => 9,
            Suit::Tiao => 18,
        };
        let bit_pos = (suit_offset + (rank - 1)) * 3;
        ((self.0 >> bit_pos) & 0b111) as u8
    }
    
    /// 设置指定牌的数量
    fn set_count(&mut self, suit: Suit, rank: u8, count: u8) {
        let suit_offset = match suit {
            Suit::Wan => 0,
            Suit::Tong => 9,
            Suit::Tiao => 18,
        };
        let bit_pos = (suit_offset + (rank - 1)) * 3;
        // 清除旧值
        self.0 &= !(0b111 << bit_pos);
        // 设置新值
        self.0 |= (count as u128) << bit_pos;
    }
    
    /// 获取总牌数
    fn total_count(&self) -> usize {
        let mut count = 0;
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            for rank in 1..=9 {
                count += self.get_count(suit, rank) as usize;
            }
        }
        count
    }
}

/// 胡牌查表
/// 
/// 预计算所有可能的胡牌组合，使用 O(1) 查询
pub struct WinLookupTable {
    /// 14 张牌的胡牌组合（完整手牌）
    win_14: HashSet<HandCode>,
    /// 11 张牌的胡牌组合（去掉一个刻子）
    win_11: HashSet<HandCode>,
    /// 8 张牌的胡牌组合（去掉两个刻子）
    win_8: HashSet<HandCode>,
    /// 5 张牌的胡牌组合（去掉三个刻子）
    win_5: HashSet<HandCode>,
    /// 2 张牌的胡牌组合（对子）
    win_2: HashSet<HandCode>,
}

impl WinLookupTable {
    /// 创建并预计算查表
    pub fn new() -> Self {
        let mut table = Self {
            win_14: HashSet::new(),
            win_11: HashSet::new(),
            win_8: HashSet::new(),
            win_5: HashSet::new(),
            win_2: HashSet::new(),
        };
        
        table.precompute();
        table
    }
    
    /// 预计算所有胡牌组合
    /// 
    /// 使用迭代扩展方法，从对子开始逐步扩展到 5/8/11/14 张牌
    /// 这种方法避免了递归带来的性能问题
    fn precompute(&mut self) {
        // 预计算 2 张牌（对子）
        self.precompute_pairs();
        
        // 迭代扩展：从 2 张 -> 5 张 -> 8 张 -> 11 张 -> 14 张
        self.expand_from_pairs();
    }
    
    /// 从对子开始迭代扩展
    fn expand_from_pairs(&mut self) {
        // 从对子扩展到 5 张牌
        let source_2: Vec<HandCode> = self.win_2.iter().copied().collect();
        Self::expand_table(&source_2, 5, &mut self.win_5);
        
        // 从 5 张牌扩展到 8 张牌
        let source_5: Vec<HandCode> = self.win_5.iter().copied().collect();
        Self::expand_table(&source_5, 8, &mut self.win_8);
        
        // 从 8 张牌扩展到 11 张牌
        let source_8: Vec<HandCode> = self.win_8.iter().copied().collect();
        Self::expand_table(&source_8, 11, &mut self.win_11);
        
        // 从 11 张牌扩展到 14 张牌
        let source_11: Vec<HandCode> = self.win_11.iter().copied().collect();
        Self::expand_table(&source_11, 14, &mut self.win_14);
    }
    
    /// 扩展表：从源表扩展到目标表
    /// 
    /// # 参数
    /// 
    /// - `source`: 源表（较小牌数的胡牌组合，已复制为 Vec 避免借用冲突）
    /// - `target_tiles`: 目标牌数
    /// - `target`: 目标表（较大牌数的胡牌组合）
    fn expand_table(source: &[HandCode], target_tiles: usize, target: &mut HashSet<HandCode>) {
        for &base_code in source.iter() {
            // 尝试添加刻子
            for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
                for rank in 1..=9 {
                    let count = base_code.get_count(suit, rank);
                    if count == 0 { // 只有该牌为 0 时才能添加刻子
                        let mut new_code = base_code;
                        new_code.set_count(suit, rank, 3);
                        if new_code.total_count() == target_tiles {
                            target.insert(new_code);
                        }
                    }
                }
            }
            
            // 尝试添加顺子
            for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
                for start in 1..=7 {
                    let count1 = base_code.get_count(suit, start);
                    let count2 = base_code.get_count(suit, start + 1);
                    let count3 = base_code.get_count(suit, start + 2);
                    
                    // 检查是否可以添加顺子（每张牌最多 4 张）
                    if count1 < 4 && count2 < 4 && count3 < 4 {
                        let mut new_code = base_code;
                        new_code.set_count(suit, start, count1 + 1);
                        new_code.set_count(suit, start + 1, count2 + 1);
                        new_code.set_count(suit, start + 2, count3 + 1);
                        if new_code.total_count() == target_tiles {
                            target.insert(new_code);
                        }
                    }
                }
            }
        }
    }
    
    /// 预计算对子（2 张牌）
    fn precompute_pairs(&mut self) {
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            for rank in 1..=9 {
                let mut code = HandCode(0);
                code.set_count(suit, rank, 2);
                self.win_2.insert(code);
            }
        }
    }
    
    
    /// 检查手牌是否胡牌（O(1) 查询）
    pub fn is_win(&self, hand: &Hand) -> bool {
        let code = HandCode::from_hand(hand);
        let count = code.total_count();
        
        match count {
            2 => self.win_2.contains(&code),
            5 => self.win_5.contains(&code),
            8 => self.win_8.contains(&code),
            11 => self.win_11.contains(&code),
            14 => self.win_14.contains(&code),
            _ => false,
        }
    }
    
    /// 获取查表大小（用于统计）
    pub fn size(&self) -> (usize, usize, usize, usize, usize) {
        (
            self.win_2.len(),
            self.win_5.len(),
            self.win_8.len(),
            self.win_11.len(),
            self.win_14.len(),
        )
    }
}

use std::sync::OnceLock;

/// 全局查表（懒加载，线程安全）
static WIN_LOOKUP_TABLE: OnceLock<WinLookupTable> = OnceLock::new();

/// 获取全局查表（线程安全）
pub fn get_lookup_table() -> &'static WinLookupTable {
    WIN_LOOKUP_TABLE.get_or_init(|| WinLookupTable::new())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_hand_code() {
        let mut hand = Hand::new();
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(2));
        hand.add_tile(Tile::Wan(3));
        
        let code = HandCode::from_hand(&hand);
        assert_eq!(code.get_count(Suit::Wan, 1), 2);
        assert_eq!(code.get_count(Suit::Wan, 2), 1);
        assert_eq!(code.get_count(Suit::Wan, 3), 1);
        assert_eq!(code.total_count(), 4);
    }
    
    #[test]
    fn test_lookup_table_pairs() {
        let table = WinLookupTable::new();
        let size = table.size();
        println!("Lookup table sizes: 2={}, 5={}, 8={}, 11={}, 14={}", 
                 size.0, size.1, size.2, size.3, size.4);
        
        // 测试对子
        let mut hand = Hand::new();
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        assert!(table.is_win(&hand));
    }
    
    #[test]
    fn test_lookup_table_14_tiles() {
        let table = WinLookupTable::new();
        
        // 测试基本胡牌型：1个对子 + 4个顺子
        let mut hand = Hand::new();
        // 对子
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        // 顺子 1
        hand.add_tile(Tile::Wan(2));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Wan(4));
        // 顺子 2
        hand.add_tile(Tile::Tong(1));
        hand.add_tile(Tile::Tong(2));
        hand.add_tile(Tile::Tong(3));
        // 顺子 3
        hand.add_tile(Tile::Tong(4));
        hand.add_tile(Tile::Tong(5));
        hand.add_tile(Tile::Tong(6));
        // 顺子 4
        hand.add_tile(Tile::Tiao(1));
        hand.add_tile(Tile::Tiao(2));
        hand.add_tile(Tile::Tiao(3));
        
        assert_eq!(hand.total_count(), 14);
        assert!(table.is_win(&hand));
    }
}

