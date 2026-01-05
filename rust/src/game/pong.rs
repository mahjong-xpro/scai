use crate::tile::Tile;
use crate::game::player::Player;
use crate::game::scoring::Meld;

/// 碰牌操作器
pub struct PongHandler;

impl PongHandler {
    /// 检查是否可以碰牌
    /// 
    /// 碰牌条件：
    /// 1. 手牌中有两张相同的牌
    /// 2. 别人打出了第三张相同的牌
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家
    /// - `tile`: 别人打出的牌
    /// 
    /// # 返回
    /// 
    /// 如果可以碰牌，返回 `true`，否则返回 `false`
    pub fn can_pong(player: &Player, tile: &Tile) -> bool {
        let tile_count = player.hand.tiles_map()
            .get(tile)
            .copied()
            .unwrap_or(0);
        
        // 手牌中至少要有 2 张相同的牌才能碰
        tile_count >= 2
    }

    /// 执行碰牌
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家（可变引用）
    /// - `tile`: 别人打出的牌
    /// 
    /// # 返回
    /// 
    /// 是否成功碰牌
    pub fn pong(player: &mut Player, tile: Tile) -> bool {
        // 检查是否可以碰牌
        if !PongHandler::can_pong(player, &tile) {
            return false;
        }
        
        // 从手牌中移除两张相同的牌
        for _ in 0..2 {
            if !player.hand.remove_tile(tile) {
                return false;
            }
        }
        
        // 添加碰（Triplet）
        player.melds.push(Meld::Triplet { tile });
        true
    }

    /// 获取所有可以碰的牌
    /// 
    /// # 参数
    /// 
    /// - `player`: 玩家
    /// - `discarded_tile`: 别人打出的牌
    /// 
    /// # 返回
    /// 
    /// 如果可以碰，返回 `Some(tile)`，否则返回 `None`
    pub fn get_pongable_tile(player: &Player, discarded_tile: &Tile) -> Option<Tile> {
        if PongHandler::can_pong(player, discarded_tile) {
            Some(*discarded_tile)
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_can_pong() {
        let mut player = Player::new(0);
        
        // 手牌中有两张 1 万
        player.hand.add_tile(Tile::Wan(1));
        player.hand.add_tile(Tile::Wan(1));
        
        // 可以碰
        assert!(PongHandler::can_pong(&player, &Tile::Wan(1)));
        
        // 只有一张，不能碰
        player.hand.remove_tile(Tile::Wan(1));
        assert!(!PongHandler::can_pong(&player, &Tile::Wan(1)));
    }

    #[test]
    fn test_pong() {
        let mut player = Player::new(0);
        
        // 手牌中有两张 1 万
        player.hand.add_tile(Tile::Wan(1));
        player.hand.add_tile(Tile::Wan(1));
        
        // 执行碰牌
        assert!(PongHandler::pong(&mut player, Tile::Wan(1)));
        
        // 检查：已添加碰
        assert!(player.melds.iter().any(|m| {
            matches!(m, Meld::Triplet { tile: Tile::Wan(1) })
        }));
        
        // 检查：手牌中的两张牌已移除
        assert_eq!(player.hand.tiles_map().get(&Tile::Wan(1)), None);
    }

    #[test]
    fn test_get_pongable_tile() {
        let mut player = Player::new(0);
        
        // 手牌中有两张 1 万
        player.hand.add_tile(Tile::Wan(1));
        player.hand.add_tile(Tile::Wan(1));
        
        // 可以碰 1 万
        assert_eq!(
            PongHandler::get_pongable_tile(&player, &Tile::Wan(1)),
            Some(Tile::Wan(1))
        );
        
        // 不能碰 2 万
        assert_eq!(
            PongHandler::get_pongable_tile(&player, &Tile::Wan(2)),
            None
        );
    }
}

