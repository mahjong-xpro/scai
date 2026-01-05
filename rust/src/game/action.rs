use crate::tile::Tile;

use crate::tile::Suit;

/// 动作类型
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action {
    /// 摸牌
    Draw,
    /// 出牌
    Discard { tile: Tile },
    /// 碰（刻子）
    Pong { tile: Tile },
    /// 杠
    Gang { tile: Tile, is_concealed: bool },
    /// 胡牌
    Win,
    /// 过（放弃）
    Pass,
    /// 定缺（三花色必缺一）
    DeclareSuit { suit: Suit },
}

