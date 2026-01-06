use crate::tile::Tile;
use crate::game::player::Player;
use crate::game::scoring::Meld;

/// 杠类型
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KongType {
    /// 直杠（别人打出的牌，你杠）
    Direct,
    /// 加杠/补杠（你已经碰了三张，摸到第四张补杠）
    Added,
    /// 暗杠（手牌中有四张相同的牌，自己杠）
    Concealed,
}

/// 杠操作器
pub struct KongHandler;

impl KongHandler {
    /// 检查是否可以加杠（补杠）
    /// 
    /// 加杠条件：
    /// 1. 玩家已经碰了三张相同的牌（Meld::Triplet）
    /// 2. 手牌中有第四张相同的牌
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家
    /// - `tile`: 要加杠的牌
    /// 
    /// # 返回
    /// 
    /// 如果可以加杠，返回 Some(KongType::Added)，否则返回 None
    pub fn can_add_kong(player: &Player, tile: &Tile) -> Option<KongType> {
        // 检查是否有对应的碰（Triplet）
        let has_triplet = player.melds.iter().any(|meld| {
            matches!(meld, Meld::Triplet { tile: t } if t == tile)
        });
        
        if !has_triplet {
            return None;
        }
        
        // 检查手牌中是否有这张牌
        let tile_count = player.hand.tiles_map()
            .get(tile)
            .copied()
            .unwrap_or(0);
        
        if tile_count > 0 {
            Some(KongType::Added)
        } else {
            None
        }
    }

    /// 检查是否可以直杠
    /// 
    /// 直杠条件：
    /// 1. 手牌中有三张相同的牌
    /// 2. 别人打出了第四张相同的牌
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家
    /// - `tile`: 别人打出的牌
    /// 
    /// # 返回
    /// 
    /// 如果可以直杠，返回 Some(KongType::Direct)，否则返回 None
    pub fn can_direct_kong(player: &Player, tile: &Tile) -> Option<KongType> {
        let tile_count = player.hand.tiles_map()
            .get(tile)
            .copied()
            .unwrap_or(0);
        
        if tile_count >= 3 {
            Some(KongType::Direct)
        } else {
            None
        }
    }

    /// 检查是否可以暗杠
    /// 
    /// 暗杠条件：
    /// 1. 手牌中有四张相同的牌
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家
    /// - `tile`: 要暗杠的牌
    /// 
    /// # 返回
    /// 
    /// 如果可以暗杠，返回 Some(KongType::Concealed)，否则返回 None
    pub fn can_concealed_kong(player: &Player, tile: &Tile) -> Option<KongType> {
        let tile_count = player.hand.tiles_map()
            .get(tile)
            .copied()
            .unwrap_or(0);
        
        if tile_count == 4 {
            Some(KongType::Concealed)
        } else {
            None
        }
    }

    /// 执行加杠（补杠）
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家（可变引用）
    /// - `tile`: 要加杠的牌
    /// 
    /// # 返回
    /// 
    /// 是否成功加杠
    pub fn add_kong(player: &mut Player, tile: Tile) -> bool {
        // 检查是否可以加杠
        if KongHandler::can_add_kong(player, &tile).is_none() {
            return false;
        }
        
        // 从手牌中移除这张牌（使用包装方法，自动清除过胡锁定）
        if !player.remove_tile_from_hand(tile) {
            return false;
        }
        
        // 将碰（Triplet）转换为杠（Kong）
        for meld in &mut player.melds {
            if let Meld::Triplet { tile: t } = *meld {
                if t == tile {
                    *meld = Meld::Kong { tile, is_concealed: false }; // 加杠是明杠
                    return true;
                }
            }
        }
        
        false
    }

    /// 执行直杠
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家（可变引用）
    /// - `tile`: 别人打出的牌
    /// 
    /// # 返回
    /// 
    /// 是否成功直杠
    pub fn direct_kong(player: &mut Player, tile: Tile) -> bool {
        // 检查是否可以直杠
        if KongHandler::can_direct_kong(player, &tile).is_none() {
            return false;
        }
        
        // 从手牌中移除三张相同的牌（使用包装方法，自动清除过胡锁定）
        for _ in 0..3 {
            if !player.remove_tile_from_hand(tile) {
                return false;
            }
        }
        
        // 添加明杠
        player.melds.push(Meld::Kong { tile, is_concealed: false });
        true
    }

    /// 执行暗杠
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家（可变引用）
    /// - `tile`: 要暗杠的牌
    /// 
    /// # 返回
    /// 
    /// 是否成功暗杠
    pub fn concealed_kong(player: &mut Player, tile: Tile) -> bool {
        // 检查是否可以暗杠
        if KongHandler::can_concealed_kong(player, &tile).is_none() {
            return false;
        }
        
        // 从手牌中移除四张相同的牌（使用包装方法，自动清除过胡锁定）
        for _ in 0..4 {
            if !player.remove_tile_from_hand(tile) {
                return false;
            }
        }
        
        // 添加暗杠
        player.melds.push(Meld::Kong { tile, is_concealed: true });
        true
    }

    /// 检查是否可以抢杠胡
    /// 
    /// 抢杠胡条件：
    /// 1. 其他玩家正在加杠（补杠）
    /// 2. 你手牌中缺这张牌就可以胡牌
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家
    /// - `tile`: 被加杠的牌
    /// - `melds`: 已碰/杠的牌组
    /// 
    /// # 返回
    /// 
    /// 是否可以抢杠胡
    pub fn can_rob_kong(player: &Player, tile: &Tile, melds: &[Meld]) -> bool {
        use crate::tile::win_check::WinChecker;
        
        // 创建测试手牌（添加被加杠的牌）
        let mut test_hand = player.hand.clone();
        
        // 检查是否可以添加这张牌（不能超过 4 张）
        let current_count = test_hand.tiles_map()
            .get(tile)
            .copied()
            .unwrap_or(0);
        if current_count >= 4 {
            return false;
        }
        
        test_hand.add_tile(*tile);
        
        // 检查是否能胡牌
        let mut checker = WinChecker::new();
        let melds_count = melds.len() as u8;
        let result = checker.check_win_with_melds(&test_hand, melds_count);
        
        result.is_win
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_can_add_kong() {
        let mut player = Player::new(0);
        
        // 先碰三张 1 万
        player.melds.push(Meld::Triplet { tile: Tile::Wan(1) });
        
        // 手牌中有 1 张 1 万
        player.hand.add_tile(Tile::Wan(1));
        
        // 可以加杠
        assert!(KongHandler::can_add_kong(&player, &Tile::Wan(1)).is_some());
        
        // 手牌中没有 1 万，不能加杠
        player.hand.remove_tile(Tile::Wan(1));
        assert!(KongHandler::can_add_kong(&player, &Tile::Wan(1)).is_none());
    }

    #[test]
    fn test_add_kong() {
        let mut player = Player::new(0);
        
        // 先碰三张 1 万
        player.melds.push(Meld::Triplet { tile: Tile::Wan(1) });
        
        // 手牌中有 1 张 1 万
        player.hand.add_tile(Tile::Wan(1));
        
        // 执行加杠
        assert!(KongHandler::add_kong(&mut player, Tile::Wan(1)));
        
        // 检查：碰已转换为杠
        assert!(player.melds.iter().any(|m| {
            matches!(m, Meld::Kong { tile: Tile::Wan(1), is_concealed: false })
        }));
        
        // 检查：手牌中的牌已移除
        assert_eq!(player.hand.tiles_map().get(&Tile::Wan(1)), None);
    }

    #[test]
    fn test_can_direct_kong() {
        let mut player = Player::new(0);
        
        // 手牌中有三张 1 万
        for _ in 0..3 {
            player.hand.add_tile(Tile::Wan(1));
        }
        
        // 可以直杠
        assert!(KongHandler::can_direct_kong(&player, &Tile::Wan(1)).is_some());
        
        // 只有两张，不能直杠
        player.hand.remove_tile(Tile::Wan(1));
        assert!(KongHandler::can_direct_kong(&player, &Tile::Wan(1)).is_none());
    }

    #[test]
    fn test_direct_kong() {
        let mut player = Player::new(0);
        
        // 手牌中有三张 1 万
        for _ in 0..3 {
            player.hand.add_tile(Tile::Wan(1));
        }
        
        // 执行直杠
        assert!(KongHandler::direct_kong(&mut player, Tile::Wan(1)));
        
        // 检查：已添加明杠
        assert!(player.melds.iter().any(|m| {
            matches!(m, Meld::Kong { tile: Tile::Wan(1), is_concealed: false })
        }));
        
        // 检查：手牌中的三张牌已移除
        assert_eq!(player.hand.tiles_map().get(&Tile::Wan(1)), None);
    }

    #[test]
    fn test_can_concealed_kong() {
        let mut player = Player::new(0);
        
        // 手牌中有四张 1 万
        for _ in 0..4 {
            player.hand.add_tile(Tile::Wan(1));
        }
        
        // 可以暗杠
        assert!(KongHandler::can_concealed_kong(&player, &Tile::Wan(1)).is_some());
        
        // 只有三张，不能暗杠
        player.hand.remove_tile(Tile::Wan(1));
        assert!(KongHandler::can_concealed_kong(&player, &Tile::Wan(1)).is_none());
    }

    #[test]
    fn test_concealed_kong() {
        let mut player = Player::new(0);
        
        // 手牌中有四张 1 万
        for _ in 0..4 {
            player.hand.add_tile(Tile::Wan(1));
        }
        
        // 执行暗杠
        assert!(KongHandler::concealed_kong(&mut player, Tile::Wan(1)));
        
        // 检查：已添加暗杠
        assert!(player.melds.iter().any(|m| {
            matches!(m, Meld::Kong { tile: Tile::Wan(1), is_concealed: true })
        }));
        
        // 检查：手牌中的四张牌已移除
        assert_eq!(player.hand.tiles_map().get(&Tile::Wan(1)), None);
    }
}

