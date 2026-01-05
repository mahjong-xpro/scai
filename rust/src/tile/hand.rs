use super::tile::Tile;
use std::collections::HashMap;
use smallvec::SmallVec;

/// 手牌（Hand）
/// 
/// 使用 HashMap 存储每张牌的数量，支持 O(1) 的添加、移除和查询操作
/// 
/// 使用 SmallVec 优化小数组场景（手牌通常只有少量不同的牌类型）
#[repr(C)]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Hand {
    /// 牌的数量映射：Tile -> 数量（1-4）
    /// 使用 SmallVec 优化：手牌通常只有 5-10 种不同的牌，使用栈分配
    tiles: HashMap<Tile, u8>,
    /// 总牌数（用于快速查询）
    total_count: usize,
}

impl Hand {
    /// 创建空手牌
    pub fn new() -> Self {
        Self {
            tiles: HashMap::new(),
            total_count: 0,
        }
    }

    /// 添加一张牌
    /// 
    /// 时间复杂度：O(1)
    /// 
    /// # Returns
    /// 
    /// - `true`：成功添加
    /// - `false`：该牌已有 4 张（理论上不应该发生）
    pub fn add_tile(&mut self, tile: Tile) -> bool {
        let count = self.tiles.entry(tile).or_insert(0);
        if *count >= 4 {
            return false; // 每种牌最多 4 张
        }
        *count += 1;
        self.total_count += 1;
        true
    }

    /// 移除一张牌
    /// 
    /// 时间复杂度：O(1)
    /// 
    /// # Returns
    /// 
    /// - `true`：成功移除
    /// - `false`：手牌中没有该牌
    pub fn remove_tile(&mut self, tile: Tile) -> bool {
        match self.tiles.get_mut(&tile) {
            Some(count) if *count > 0 => {
                *count -= 1;
                self.total_count -= 1;
                if *count == 0 {
                    self.tiles.remove(&tile);
                }
                true
            }
            _ => false,
        }
    }

    /// 检查是否有某张牌
    /// 
    /// 时间复杂度：O(1)
    pub fn has_tile(&self, tile: Tile) -> bool {
        self.tile_count(tile) > 0
    }

    /// 查询某张牌的数量
    /// 
    /// 时间复杂度：O(1)
    pub fn tile_count(&self, tile: Tile) -> u8 {
        self.tiles.get(&tile).copied().unwrap_or(0)
    }

    /// 获取总牌数
    pub fn total_count(&self) -> usize {
        self.total_count
    }

    /// 转换为排序后的牌向量（用于显示和调试）
    /// 
    /// 排序规则：先按花色（万、筒、条），再按数字（1-9）
    pub fn to_sorted_vec(&self) -> Vec<Tile> {
        let mut result = Vec::with_capacity(self.total_count);
        
        // 按花色和数字排序
        for suit in [super::tile::Suit::Wan, super::tile::Suit::Tong, super::tile::Suit::Tiao] {
            for rank in Tile::MIN_RANK..=Tile::MAX_RANK {
                let tile = match suit {
                    super::tile::Suit::Wan => Tile::Wan(rank),
                    super::tile::Suit::Tong => Tile::Tong(rank),
                    super::tile::Suit::Tiao => Tile::Tiao(rank),
                };
                let count = self.tile_count(tile);
                for _ in 0..count {
                    result.push(tile);
                }
            }
        }
        
        result
    }

    /// 检查手牌是否为空
    pub fn is_empty(&self) -> bool {
        self.total_count == 0
    }

    /// 清空手牌
    pub fn clear(&mut self) {
        self.tiles.clear();
        self.total_count = 0;
    }

    /// 获取所有不同的牌类型（不包含数量为 0 的）
    /// 
    /// 使用 SmallVec 优化：手牌通常只有 5-10 种不同的牌类型
    pub fn distinct_tiles(&self) -> SmallVec<[Tile; 10]> {
        let mut result = SmallVec::with_capacity(self.tiles.len());
        for tile in self.tiles.keys() {
            result.push(*tile);
        }
        result
    }

    /// 获取所有牌的数量映射（用于高级操作）
    pub fn tiles_map(&self) -> &HashMap<Tile, u8> {
        &self.tiles
    }
}

impl Default for Hand {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hand_creation() {
        let hand = Hand::new();
        assert!(hand.is_empty());
        assert_eq!(hand.total_count(), 0);
    }

    #[test]
    fn test_hand_add_tile() {
        let mut hand = Hand::new();
        let tile = Tile::Wan(1);
        
        assert!(hand.add_tile(tile));
        assert_eq!(hand.total_count(), 1);
        assert_eq!(hand.tile_count(tile), 1);
        assert!(hand.has_tile(tile));
    }

    #[test]
    fn test_hand_add_multiple() {
        let mut hand = Hand::new();
        let tile = Tile::Wan(5);
        
        // 添加 4 张相同的牌
        for _ in 0..4 {
            assert!(hand.add_tile(tile));
        }
        
        assert_eq!(hand.total_count(), 4);
        assert_eq!(hand.tile_count(tile), 4);
        
        // 第 5 张应该失败
        assert!(!hand.add_tile(tile));
        assert_eq!(hand.total_count(), 4);
    }

    #[test]
    fn test_hand_remove_tile() {
        let mut hand = Hand::new();
        let tile = Tile::Tong(3);
        
        // 移除不存在的牌
        assert!(!hand.remove_tile(tile));
        
        // 添加后移除
        hand.add_tile(tile);
        assert!(hand.remove_tile(tile));
        assert_eq!(hand.total_count(), 0);
        assert!(!hand.has_tile(tile));
    }

    #[test]
    fn test_hand_remove_multiple() {
        let mut hand = Hand::new();
        let tile = Tile::Tiao(7);
        
        // 添加 3 张
        for _ in 0..3 {
            hand.add_tile(tile);
        }
        
        // 移除 2 张
        assert!(hand.remove_tile(tile));
        assert!(hand.remove_tile(tile));
        assert_eq!(hand.tile_count(tile), 1);
        assert_eq!(hand.total_count(), 1);
        
        // 再移除最后一张
        assert!(hand.remove_tile(tile));
        assert_eq!(hand.tile_count(tile), 0);
        assert_eq!(hand.total_count(), 0);
        
        // 再次移除应该失败
        assert!(!hand.remove_tile(tile));
    }

    #[test]
    fn test_hand_to_sorted_vec() {
        let mut hand = Hand::new();
        
        // 添加一些牌（乱序）
        hand.add_tile(Tile::Tong(5));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Tiao(1));
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Tong(5));
        
        let sorted = hand.to_sorted_vec();
        
        // 检查排序：万、筒、条，每种内部按数字排序
        assert_eq!(sorted.len(), 5);
        assert_eq!(sorted[0], Tile::Wan(1));
        assert_eq!(sorted[1], Tile::Wan(3));
        assert_eq!(sorted[2], Tile::Tong(5));
        assert_eq!(sorted[3], Tile::Tong(5));
        assert_eq!(sorted[4], Tile::Tiao(1));
    }

    #[test]
    fn test_hand_clear() {
        let mut hand = Hand::new();
        
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Tong(2));
        hand.add_tile(Tile::Tiao(3));
        
        assert_eq!(hand.total_count(), 3);
        
        hand.clear();
        assert!(hand.is_empty());
        assert_eq!(hand.total_count(), 0);
    }

    #[test]
    fn test_hand_distinct_tiles() {
        let mut hand = Hand::new();
        
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Tong(2));
        hand.add_tile(Tile::Tiao(3));
        
        let distinct = hand.distinct_tiles();
        assert_eq!(distinct.len(), 3);
        assert!(distinct.contains(&Tile::Wan(1)));
        assert!(distinct.contains(&Tile::Tong(2)));
        assert!(distinct.contains(&Tile::Tiao(3)));
    }
}

