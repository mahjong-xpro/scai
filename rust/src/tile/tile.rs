/// 麻将牌类型
/// 
/// 血战到底使用 108 张牌：万、筒、条各 36 张（1-9 各 4 张）
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub enum Tile {
    /// 万子（1-9，共 36 张）
    Wan(u8),
    /// 筒子（1-9，共 36 张）
    Tong(u8),
    /// 条子（1-9，共 36 张）
    Tiao(u8),
}

impl Tile {
    /// 总牌数：108 张
    pub const TOTAL_COUNT: usize = 108;
    
    /// 每种花色的牌数：36 张
    pub const SUIT_COUNT: usize = 36;
    
    /// 每种花色的数字范围：1-9
    pub const MIN_RANK: u8 = 1;
    pub const MAX_RANK: u8 = 9;

    /// 创建一张牌，验证输入有效性
    pub fn new(suit: Suit, rank: u8) -> Option<Self> {
        if rank < Self::MIN_RANK || rank > Self::MAX_RANK {
            return None;
        }
        Some(match suit {
            Suit::Wan => Tile::Wan(rank),
            Suit::Tong => Tile::Tong(rank),
            Suit::Tiao => Tile::Tiao(rank),
        })
    }

    /// 获取花色
    pub fn suit(&self) -> Suit {
        match self {
            Tile::Wan(_) => Suit::Wan,
            Tile::Tong(_) => Suit::Tong,
            Tile::Tiao(_) => Suit::Tiao,
        }
    }

    /// 获取数字（1-9）
    pub fn rank(&self) -> u8 {
        match self {
            Tile::Wan(r) | Tile::Tong(r) | Tile::Tiao(r) => *r,
        }
    }

    /// 转换为 u8 索引（0-107）
    /// 
    /// 映射规则：
    /// - 万子：0-35 (0*36 + rank-1 + (copy-1)*9)
    /// - 筒子：36-71 (1*36 + rank-1 + (copy-1)*9)
    /// - 条子：72-107 (2*36 + rank-1 + (copy-1)*9)
    /// 
    /// 简化版本：按花色和数字映射
    /// - 万子：0-35 = (rank-1) * 4 + copy-1
    /// - 筒子：36-71 = 36 + (rank-1) * 4 + copy-1
    /// - 条子：72-107 = 72 + (rank-1) * 4 + copy-1
    /// 
    /// 这里使用简化版本：不考虑具体是哪一张（因为所有相同牌等价）
    /// 实际映射：suit_index * 36 + (rank - 1) * 4 + copy_index
    pub fn to_index(&self) -> u8 {
        let suit_index = self.suit() as u8;
        let rank = self.rank();
        // 简化：假设每张牌有 4 个副本，我们只关心类型
        // 实际使用时，需要区分具体是哪一张
        suit_index * 36 + (rank - 1) * 4
    }

    /// 从 u8 索引创建牌
    /// 
    /// 索引范围：0-107
    pub fn from_index(index: u8) -> Option<Self> {
        if index >= Self::TOTAL_COUNT as u8 {
            return None;
        }
        let suit_index = index / 36;
        let rank_index = (index % 36) / 4;
        let rank = rank_index + 1;
        
        match suit_index {
            0 => Some(Tile::Wan(rank)),
            1 => Some(Tile::Tong(rank)),
            2 => Some(Tile::Tiao(rank)),
            _ => None,
        }
    }

    /// 检查是否为同一类型的牌（不考虑具体副本）
    pub fn same_type(&self, other: &Tile) -> bool {
        self.suit() == other.suit() && self.rank() == other.rank()
    }

    /// 检查是否可以组成顺子（连续三张）
    pub fn can_form_sequence(&self, other1: &Tile, other2: &Tile) -> bool {
        if self.suit() != other1.suit() || self.suit() != other2.suit() {
            return false;
        }
        let mut ranks = [self.rank(), other1.rank(), other2.rank()];
        ranks.sort();
        ranks[0] + 1 == ranks[1] && ranks[1] + 1 == ranks[2]
    }
}

/// 花色枚举
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub enum Suit {
    Wan = 0,
    Tong = 1,
    Tiao = 2,
}

impl Suit {
    /// 所有花色
    pub fn all() -> [Suit; 3] {
        [Suit::Wan, Suit::Tong, Suit::Tiao]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tile_creation() {
        let tile = Tile::new(Suit::Wan, 1).unwrap();
        assert_eq!(tile.suit(), Suit::Wan);
        assert_eq!(tile.rank(), 1);

        let tile = Tile::new(Suit::Tong, 9).unwrap();
        assert_eq!(tile.suit(), Suit::Tong);
        assert_eq!(tile.rank(), 9);

        // 无效的 rank
        assert!(Tile::new(Suit::Wan, 0).is_none());
        assert!(Tile::new(Suit::Wan, 10).is_none());
    }

    #[test]
    fn test_tile_index_conversion() {
        // 测试万子
        let tile = Tile::Wan(1);
        let index = tile.to_index();
        let restored = Tile::from_index(index).unwrap();
        assert_eq!(tile.suit(), restored.suit());
        assert_eq!(tile.rank(), restored.rank());

        // 测试筒子
        let tile = Tile::Tong(5);
        let index = tile.to_index();
        let restored = Tile::from_index(index).unwrap();
        assert_eq!(tile.suit(), restored.suit());
        assert_eq!(tile.rank(), restored.rank());

        // 测试条子
        let tile = Tile::Tiao(9);
        let index = tile.to_index();
        let restored = Tile::from_index(index).unwrap();
        assert_eq!(tile.suit(), restored.suit());
        assert_eq!(tile.rank(), restored.rank());
    }

    #[test]
    fn test_same_type() {
        let tile1 = Tile::Wan(5);
        let tile2 = Tile::Wan(5);
        let tile3 = Tile::Wan(6);
        let tile4 = Tile::Tong(5);

        assert!(tile1.same_type(&tile2));
        assert!(!tile1.same_type(&tile3));
        assert!(!tile1.same_type(&tile4));
    }

    #[test]
    fn test_can_form_sequence() {
        let tile1 = Tile::Wan(1);
        let tile2 = Tile::Wan(2);
        let tile3 = Tile::Wan(3);
        assert!(tile1.can_form_sequence(&tile2, &tile3));

        let tile4 = Tile::Wan(5);
        assert!(!tile1.can_form_sequence(&tile2, &tile4));

        let tile5 = Tile::Tong(1);
        assert!(!tile1.can_form_sequence(&tile2, &tile5));
    }
}

