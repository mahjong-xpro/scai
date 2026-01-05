use crate::tile::{Tile, Suit};

/// 位掩码工具
/// 
/// 使用位运算快速检测牌的组合（顺子、刻子、对子）
/// 
/// 对于每种花色，使用 u32 的低 27 位（3*9）来表示 1-9 的牌
/// 每 3 位表示一张牌的数量（0-4，但实际只需要 0-3，因为每种牌最多 4 张）
/// 
/// 更简单的方案：使用 u16 的 9 位表示每种牌的存在性（至少一张）
/// 然后用另一个 u16 表示数量（但这样需要两个值）
/// 
/// 最优方案：使用 u32 的 27 位，每 3 位表示一张牌的数量
/// 位布局：[rank1(3位)][rank2(3位)]...[rank9(3位)]
/// 
/// 但为了简化，我们先使用存在性掩码（u16），然后单独查询数量

/// 花色位掩码
/// 
/// 使用 u16 的低 9 位表示 1-9 的牌是否存在（至少一张）
/// 位 0-8 分别对应 1-9
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SuitMask {
    /// 存在性掩码：第 i 位为 1 表示 rank i+1 的牌存在
    presence: u16,
    /// 数量数组：rank i+1 的牌的数量（0-4）
    counts: [u8; 9],
}

impl SuitMask {
    /// 创建空的花色掩码
    pub fn new() -> Self {
        Self {
            presence: 0,
            counts: [0; 9],
        }
    }

    /// 从手牌数据创建花色掩码
    pub fn from_hand_data(counts: [u8; 9]) -> Self {
        let mut presence = 0u16;
        for (i, &count) in counts.iter().enumerate() {
            if count > 0 {
                presence |= 1 << i;
            }
        }
        Self { presence, counts }
    }

    /// 添加一张牌
    pub fn add_tile(&mut self, rank: u8) -> bool {
        if rank < 1 || rank > 9 {
            return false;
        }
        let idx = (rank - 1) as usize;
        if self.counts[idx] >= 4 {
            return false;
        }
        self.counts[idx] += 1;
        self.presence |= 1 << idx;
        true
    }

    /// 移除一张牌
    pub fn remove_tile(&mut self, rank: u8) -> bool {
        if rank < 1 || rank > 9 {
            return false;
        }
        let idx = (rank - 1) as usize;
        if self.counts[idx] == 0 {
            return false;
        }
        self.counts[idx] -= 1;
        if self.counts[idx] == 0 {
            self.presence &= !(1 << idx);
        }
        true
    }

    /// 获取某张牌的数量
    pub fn count(&self, rank: u8) -> u8 {
        if rank < 1 || rank > 9 {
            return 0;
        }
        self.counts[(rank - 1) as usize]
    }

    /// 检查是否存在某张牌
    pub fn has_tile(&self, rank: u8) -> bool {
        if rank < 1 || rank > 9 {
            return false;
        }
        (self.presence & (1 << (rank - 1))) != 0
    }

    /// 检测顺子（连续三张牌）
    /// 
    /// 返回所有可能的顺子起始位置（rank 1-7）
    /// 
    /// # 算法
    /// 
    /// 使用位掩码快速检测：对于 rank i，检查 i, i+1, i+2 是否都存在
    /// 使用位运算：`(presence >> i) & 0b111 == 0b111`
    pub fn detect_sequences(&self) -> Vec<u8> {
        let mut sequences = Vec::new();
        // 检查 rank 1-7 是否可以组成顺子
        for start in 1..=7 {
            let mask = 0b111 << (start - 1);
            if (self.presence & mask) == mask {
                // 检查每张牌是否至少有一张
                if self.count(start) > 0 
                    && self.count(start + 1) > 0 
                    && self.count(start + 2) > 0 {
                    sequences.push(start);
                }
            }
        }
        sequences
    }

    /// 检测刻子（三张相同牌）
    /// 
    /// 返回所有可能的刻子（rank 1-9）
    pub fn detect_triplets(&self) -> Vec<u8> {
        let mut triplets = Vec::new();
        for rank in 1..=9 {
            if self.count(rank) >= 3 {
                triplets.push(rank);
            }
        }
        triplets
    }

    /// 检测对子（两张相同牌）
    /// 
    /// 返回所有可能的对子（rank 1-9）
    pub fn detect_pairs(&self) -> Vec<u8> {
        let mut pairs = Vec::new();
        for rank in 1..=9 {
            if self.count(rank) >= 2 {
                pairs.push(rank);
            }
        }
        pairs
    }

    /// 快速检测是否存在顺子（不返回具体位置）
    pub fn has_sequence(&self) -> bool {
        // 使用位运算快速检测：检查是否存在连续的三个 1
        for start in 0..=6 {
            let mask = 0b111 << start;
            if (self.presence & mask) == mask {
                // 进一步检查数量
                let rank1 = start + 1;
                if self.count(rank1) > 0 
                    && self.count(rank1 + 1) > 0 
                    && self.count(rank1 + 2) > 0 {
                    return true;
                }
            }
        }
        false
    }

    /// 快速检测是否存在刻子
    pub fn has_triplet(&self) -> bool {
        self.presence != 0 && self.detect_triplets().len() > 0
    }

    /// 快速检测是否存在对子
    pub fn has_pair(&self) -> bool {
        self.presence != 0 && self.detect_pairs().len() > 0
    }

    /// 获取存在性掩码（用于调试）
    pub fn presence_mask(&self) -> u16 {
        self.presence
    }
}

impl Default for SuitMask {
    fn default() -> Self {
        Self::new()
    }
}

/// 手牌位掩码
/// 
/// 包含三种花色的掩码
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct HandMask {
    wan: SuitMask,
    tong: SuitMask,
    tiao: SuitMask,
}

impl HandMask {
    /// 从 Hand 创建位掩码
    pub fn from_hand(hand: &crate::tile::Hand) -> Self {
        let mut mask = Self::new();
        
        // 统计每种花色的牌
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            let mut counts = [0u8; 9];
            for rank in 1..=9 {
                let tile = match suit {
                    Suit::Wan => Tile::Wan(rank),
                    Suit::Tong => Tile::Tong(rank),
                    Suit::Tiao => Tile::Tiao(rank),
                };
                counts[(rank - 1) as usize] = hand.tile_count(tile);
            }
            
            let suit_mask = SuitMask::from_hand_data(counts);
            match suit {
                Suit::Wan => mask.wan = suit_mask,
                Suit::Tong => mask.tong = suit_mask,
                Suit::Tiao => mask.tiao = suit_mask,
            }
        }
        
        mask
    }

    /// 创建空的手牌掩码
    pub fn new() -> Self {
        Self {
            wan: SuitMask::new(),
            tong: SuitMask::new(),
            tiao: SuitMask::new(),
        }
    }

    /// 获取指定花色的掩码
    pub fn suit_mask(&self, suit: Suit) -> &SuitMask {
        match suit {
            Suit::Wan => &self.wan,
            Suit::Tong => &self.tong,
            Suit::Tiao => &self.tiao,
        }
    }

    /// 检测所有顺子（按花色分组）
    pub fn detect_all_sequences(&self) -> Vec<(Suit, u8)> {
        let mut result = Vec::new();
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            let sequences = self.suit_mask(suit).detect_sequences();
            for start in sequences {
                result.push((suit, start));
            }
        }
        result
    }

    /// 检测所有刻子（按花色分组）
    pub fn detect_all_triplets(&self) -> Vec<(Suit, u8)> {
        let mut result = Vec::new();
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            let triplets = self.suit_mask(suit).detect_triplets();
            for rank in triplets {
                result.push((suit, rank));
            }
        }
        result
    }

    /// 检测所有对子（按花色分组）
    pub fn detect_all_pairs(&self) -> Vec<(Suit, u8)> {
        let mut result = Vec::new();
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            let pairs = self.suit_mask(suit).detect_pairs();
            for rank in pairs {
                result.push((suit, rank));
            }
        }
        result
    }
}

impl Default for HandMask {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_suit_mask_creation() {
        let mask = SuitMask::new();
        assert_eq!(mask.presence, 0);
        for rank in 1..=9 {
            assert_eq!(mask.count(rank), 0);
        }
    }

    #[test]
    fn test_suit_mask_add_remove() {
        let mut mask = SuitMask::new();
        
        assert!(mask.add_tile(5));
        assert_eq!(mask.count(5), 1);
        assert!(mask.has_tile(5));
        
        assert!(mask.add_tile(5));
        assert_eq!(mask.count(5), 2);
        
        assert!(mask.remove_tile(5));
        assert_eq!(mask.count(5), 1);
        
        assert!(mask.remove_tile(5));
        assert_eq!(mask.count(5), 0);
        assert!(!mask.has_tile(5));
    }

    #[test]
    fn test_detect_sequence() {
        let mut mask = SuitMask::new();
        
        // 添加顺子 1-2-3
        mask.add_tile(1);
        mask.add_tile(2);
        mask.add_tile(3);
        
        let sequences = mask.detect_sequences();
        assert_eq!(sequences, vec![1]);
        
        // 添加顺子 5-6-7
        mask.add_tile(5);
        mask.add_tile(6);
        mask.add_tile(7);
        
        let sequences = mask.detect_sequences();
        assert!(sequences.contains(&1));
        assert!(sequences.contains(&5));
    }

    #[test]
    fn test_detect_sequence_not_continuous() {
        let mut mask = SuitMask::new();
        
        // 添加 1, 3, 5（不连续）
        mask.add_tile(1);
        mask.add_tile(3);
        mask.add_tile(5);
        
        let sequences = mask.detect_sequences();
        assert_eq!(sequences.len(), 0);
    }

    #[test]
    fn test_detect_triplet() {
        let mut mask = SuitMask::new();
        
        // 添加三张 5
        mask.add_tile(5);
        mask.add_tile(5);
        mask.add_tile(5);
        
        let triplets = mask.detect_triplets();
        assert_eq!(triplets, vec![5]);
        
        // 添加四张 3
        mask.add_tile(3);
        mask.add_tile(3);
        mask.add_tile(3);
        mask.add_tile(3);
        
        let triplets = mask.detect_triplets();
        assert!(triplets.contains(&3));
        assert!(triplets.contains(&5));
    }

    #[test]
    fn test_detect_pair() {
        let mut mask = SuitMask::new();
        
        // 添加两张 7
        mask.add_tile(7);
        mask.add_tile(7);
        
        let pairs = mask.detect_pairs();
        assert_eq!(pairs, vec![7]);
        
        // 添加两张 9
        mask.add_tile(9);
        mask.add_tile(9);
        
        let pairs = mask.detect_pairs();
        assert!(pairs.contains(&7));
        assert!(pairs.contains(&9));
    }

    #[test]
    fn test_has_sequence() {
        let mut mask = SuitMask::new();
        assert!(!mask.has_sequence());
        
        mask.add_tile(2);
        mask.add_tile(3);
        mask.add_tile(4);
        assert!(mask.has_sequence());
    }

    #[test]
    fn test_hand_mask_from_hand() {
        use crate::tile::Hand;
        
        let mut hand = Hand::new();
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(2));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Tong(5));
        hand.add_tile(Tile::Tong(5));
        hand.add_tile(Tile::Tiao(9));
        
        let mask = HandMask::from_hand(&hand);
        
        // 检查万子顺子
        let sequences = mask.detect_all_sequences();
        assert!(sequences.contains(&(Suit::Wan, 1)));
        
        // 检查筒子刻子（实际是对子）
        let pairs = mask.detect_all_pairs();
        assert!(pairs.contains(&(Suit::Tong, 5)));
    }
}

