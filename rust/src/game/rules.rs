use crate::tile::{Hand, Suit};
use crate::game::state::PassedWin;

/// 检查缺一门
/// 
/// # 参数
/// 
/// - `hand`: 手牌
/// - `declared_suit`: 定缺的花色
/// 
/// # 返回
/// 
/// `true` 表示可以胡牌（定缺门已打完），`false` 表示不能胡（还有定缺门的牌）
pub fn check_missing_suit(hand: &Hand, declared_suit: Option<Suit>) -> bool {
    if let Some(suit) = declared_suit {
        // 检查手牌中是否还有定缺门的牌
        for (tile, _) in hand.tiles_map() {
            if tile.suit() == suit {
                return false; // 还有定缺门的牌，不能胡
            }
        }
    }
    true // 定缺门已打完，可以胡
}

/// 检查过胡限制
/// 
/// # 参数
/// 
/// - `tile`: 要胡的牌
/// - `fans`: 当前番数
/// - `passed_wins`: 放弃的胡牌记录
/// - `current_turn`: 当前回合数
/// 
/// # 返回
/// 
/// `true` 表示可以胡，`false` 表示不能胡（过胡限制）
pub fn can_win_after_pass(
    tile: &crate::tile::Tile,
    fans: u32,
    passed_wins: &[PassedWin],
    current_turn: u32,
) -> bool {
    for passed in passed_wins {
        // 检查是否在同一张牌
        if passed.tile == *tile {
            // 检查是否在当前回合之前放弃的
            if passed.turn < current_turn {
                // 检查当前番数是否 <= 放弃时的番数
                if fans <= passed.fans {
                    return false; // 不能胡（过胡限制）
                }
            }
        }
    }
    true // 可以胡
}

