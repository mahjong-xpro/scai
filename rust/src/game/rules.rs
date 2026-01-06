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

/// 检查过胡限制（旧版，基于 PassedWin 记录）
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

/// 检查过胡锁定（新版，基于 Player.passed_hu_fan）
/// 
/// # 参数
/// 
/// - `tile`: 当前要胡的牌
/// - `fans`: 当前点炮番数
/// - `passed_hu_fan`: 玩家记录的过胡番数（None 表示未过胡）
/// - `passed_hu_tile`: 玩家记录的过胡牌（None 表示未过胡）
/// - `is_self_draw`: 是否自摸（自摸不受过胡限制）
/// 
/// # 返回
/// 
/// `true` 表示可以胡，`false` 表示不能胡（过胡锁定）
/// 
/// # 规则
/// 
/// 如果玩家放弃了当前点炮，在下一次摸牌前，不能胡同一张牌或番数 <= 该记录值的点炮牌
/// 注意：自摸不受此限制
pub fn check_passed_win_restriction(
    tile: crate::tile::Tile,
    fans: u32,
    passed_hu_fan: Option<u32>,
    passed_hu_tile: Option<crate::tile::Tile>,
    is_self_draw: bool,
) -> bool {
    // 自摸不受过胡限制
    if is_self_draw {
        return true;
    }
    
    // 如果没有过胡记录，可以胡
    let Some(threshold) = passed_hu_fan else {
        return true;
    };
    
    // 检查是否是同一张牌（如果是，不能胡）
    if let Some(passed_tile) = passed_hu_tile {
        if tile == passed_tile {
            return false; // 不能胡同一张牌
        }
    }
    
    // 如果当前番数 <= 过胡记录的番数，不能胡
    if fans <= threshold {
        return false;
    }
    
    true // 可以胡（番数更高）
}

