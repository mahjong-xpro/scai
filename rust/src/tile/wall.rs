use super::tile::{Tile, Suit};
use rand::seq::SliceRandom;
use rand::thread_rng;

/// 牌墙（Wall）
/// 
/// 存储所有 108 张牌，支持洗牌和抽牌操作
/// 
/// 使用 Box<[Tile]> 替代 Vec<Tile> 以减少堆分配
#[repr(C)]
#[derive(Debug, Clone)]
pub struct Wall {
    /// 牌堆（从后往前抽取）
    /// 使用 Box<[Tile]> 减少堆分配，大小固定为 108
    tiles: Box<[Tile]>,
    /// 已抽取的牌数
    drawn_count: usize,
}

impl Wall {
    /// 创建一副完整的牌墙（108 张）
    pub fn new() -> Self {
        let mut tiles = Vec::with_capacity(Tile::TOTAL_COUNT);
        
        // 生成所有牌：每种花色 1-9，每种 4 张
        for suit in Suit::all() {
            for rank in Tile::MIN_RANK..=Tile::MAX_RANK {
                for _ in 0..4 {
                    // 创建 4 张相同的牌
                    let tile = match suit {
                        Suit::Wan => Tile::Wan(rank),
                        Suit::Tong => Tile::Tong(rank),
                        Suit::Tiao => Tile::Tiao(rank),
                    };
                    tiles.push(tile);
                }
            }
        }
        
        // 转换为 Box<[Tile]> 以减少堆分配
        Self {
            tiles: tiles.into_boxed_slice(),
            drawn_count: 0,
        }
    }

    /// 洗牌
    /// 
    /// 使用 Fisher-Yates 洗牌算法，时间复杂度 O(n)
    /// 
    /// 注意：需要将 Box<[Tile]> 转换为 Vec 进行洗牌，然后转回 Box<[Tile]>
    pub fn shuffle(&mut self) {
        let mut rng = thread_rng();
        // 转换为 Vec 进行洗牌
        let mut tiles_vec: Vec<Tile> = self.tiles.to_vec();
        tiles_vec.shuffle(&mut rng);
        // 转回 Box<[Tile]>
        self.tiles = tiles_vec.into_boxed_slice();
        self.drawn_count = 0;
    }

    /// 抽取一张牌（从牌堆末尾）
    /// 
    /// 时间复杂度：O(1)
    /// 
    /// # Returns
    /// 
    /// - `Some(Tile)`：成功抽取一张牌
    /// - `None`：牌堆已空
    pub fn draw(&mut self) -> Option<Tile> {
        if self.drawn_count >= self.tiles.len() {
            return None;
        }
        // 从末尾抽取（模拟从牌堆底部抽牌）
        let index = self.tiles.len() - 1 - self.drawn_count;
        self.drawn_count += 1;
        Some(self.tiles[index])
    }

    /// 查询剩余牌数
    /// 
    /// 时间复杂度：O(1)
    pub fn remaining_count(&self) -> usize {
        self.tiles.len().saturating_sub(self.drawn_count)
    }

    /// 检查牌堆是否为空
    pub fn is_empty(&self) -> bool {
        self.remaining_count() == 0
    }

    /// 重置牌墙（重新生成所有牌，不洗牌）
    pub fn reset(&mut self) {
        *self = Self::new();
    }

    /// 重置并洗牌
    pub fn reset_and_shuffle(&mut self) {
        self.reset();
        self.shuffle();
    }

    /// 获取已抽取的牌数
    pub fn drawn_count(&self) -> usize {
        self.drawn_count
    }

    /// 获取总牌数（应该是 108）
    pub fn total_count(&self) -> usize {
        self.tiles.len()
    }
}

impl Default for Wall {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_wall_creation() {
        let wall = Wall::new();
        assert_eq!(wall.total_count(), Tile::TOTAL_COUNT);
        assert_eq!(wall.remaining_count(), Tile::TOTAL_COUNT);
        assert!(!wall.is_empty());
    }

    #[test]
    fn test_wall_draw() {
        let mut wall = Wall::new();
        let initial_count = wall.remaining_count();
        
        // 抽取一张牌
        let tile = wall.draw();
        assert!(tile.is_some());
        assert_eq!(wall.remaining_count(), initial_count - 1);
        assert_eq!(wall.drawn_count(), 1);
    }

    #[test]
    fn test_wall_draw_all() {
        let mut wall = Wall::new();
        
        // 抽取所有牌
        let mut count = 0;
        while let Some(_) = wall.draw() {
            count += 1;
        }
        
        assert_eq!(count, Tile::TOTAL_COUNT);
        assert_eq!(wall.remaining_count(), 0);
        assert!(wall.is_empty());
        
        // 再次抽取应该返回 None
        assert!(wall.draw().is_none());
    }

    #[test]
    fn test_wall_shuffle() {
        let mut wall1 = Wall::new();
        let mut wall2 = Wall::new();
        
        // 洗牌后，两张牌的顺序应该不同（概率很高）
        wall1.shuffle();
        wall2.shuffle();
        
        // 抽取前几张，检查顺序是否不同
        let tile1_1 = wall1.draw();
        let tile1_2 = wall1.draw();
        let tile2_1 = wall2.draw();
        let tile2_2 = wall2.draw();
        
        // 由于随机性，可能相同，但连续两张都相同的概率很低
        // 这里主要测试洗牌不会导致错误
        assert!(tile1_1.is_some());
        assert!(tile1_2.is_some());
        assert!(tile2_1.is_some());
        assert!(tile2_2.is_some());
    }

    #[test]
    fn test_wall_reset() {
        let mut wall = Wall::new();
        
        // 抽取一些牌
        for _ in 0..10 {
            wall.draw();
        }
        
        assert_eq!(wall.remaining_count(), Tile::TOTAL_COUNT - 10);
        
        // 重置
        wall.reset();
        assert_eq!(wall.remaining_count(), Tile::TOTAL_COUNT);
        assert_eq!(wall.drawn_count(), 0);
    }

    #[test]
    fn test_wall_tile_distribution() {
        let wall = Wall::new();
        let mut counts = std::collections::HashMap::new();
        
        // 统计每种牌的数量
        for tile in &wall.tiles {
            *counts.entry((tile.suit(), tile.rank())).or_insert(0) += 1;
        }
        
        // 每种牌应该有 4 张
        for suit in Suit::all() {
            for rank in Tile::MIN_RANK..=Tile::MAX_RANK {
                assert_eq!(counts.get(&(suit, rank)), Some(&4));
            }
        }
    }
}

