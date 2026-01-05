use crate::game::action::Action;
use crate::game::state::GameState;
use crate::tile::{Tile, Suit};
use crate::engine::action_mask::ActionMask;
use crate::game::ready::ReadyChecker;
use crate::tile::win_check::WinChecker;
use crate::game::scoring::BaseFansCalculator;
use rand::Rng;

/// 智能动作回调示例
/// 
/// 这个模块提供了几个示例动作回调函数，展示如何根据游戏状态智能选择动作
pub mod examples {
    use super::*;

    /// 随机动作回调（用于测试）
    /// 
    /// 随机选择动作，主要用于测试游戏流程
    pub fn random_action_callback(state: &GameState, player_id: u8) -> Action {
        let player = &state.players[player_id as usize];
        
        // 如果未定缺，随机选择一个花色定缺
        if player.declared_suit.is_none() {
            let suits = [Suit::Wan, Suit::Tong, Suit::Tiao];
            let suit = suits[rand::thread_rng().gen_range(0..3)];
            return Action::DeclareSuit { suit };
        }
        
        // 随机选择动作
        let mut rng = rand::thread_rng();
        let action_type = rng.gen_range(0..6);
        
        match action_type {
            0 => Action::Draw,
            1 => {
                // 随机出一张牌
                if let Some((tile, _)) = player.hand.tiles_map().iter().next() {
                    Action::Discard { tile: *tile }
                } else {
                    Action::Pass
                }
            }
            2 => Action::Win,
            3 => Action::Pass,
            _ => Action::Draw,
        }
    }

    /// 简单策略动作回调
    /// 
    /// 使用简单策略选择动作：
    /// - 优先胡牌（如果可以）
    /// - 优先听牌
    /// - 优先出定缺门的牌
    /// - 否则随机出牌
    pub fn simple_strategy_callback(state: &GameState, player_id: u8) -> Action {
        let player = &state.players[player_id as usize];
        
        // 如果未定缺，选择手牌中最少的花色作为定缺
        if player.declared_suit.is_none() {
            let mut suit_counts = [0u8; 3];
            for (tile, &count) in player.hand.tiles_map() {
                match tile.suit() {
                    Suit::Wan => suit_counts[0] += count,
                    Suit::Tong => suit_counts[1] += count,
                    Suit::Tiao => suit_counts[2] += count,
                }
            }
            
            let min_suit_idx = suit_counts.iter()
                .enumerate()
                .min_by_key(|(_, &count)| count)
                .map(|(idx, _)| idx)
                .unwrap_or(0);
            
            let suit = match min_suit_idx {
                0 => Suit::Wan,
                1 => Suit::Tong,
                _ => Suit::Tiao,
            };
            
            return Action::DeclareSuit { suit };
        }
        
        // 检查是否可以胡牌
        let mut checker = WinChecker::new();
        let melds_count = player.melds.len() as u8;
        let win_result = checker.check_win_with_melds(&player.hand, melds_count);
        
        if win_result.is_win {
            // 检查缺一门和过胡限制
            let base_fans = BaseFansCalculator::base_fans(win_result.win_type);
            let mask = ActionMask::new();
            
            // 简化处理：如果可以胡就胡（自摸）
            if mask.can_win(&player.hand, &Tile::Wan(1), state, player.declared_suit, base_fans, true) {
                return Action::Win;
            }
        }
        
        // 检查是否可以听牌（简化处理）
        if !player.is_ready {
            let ready_tiles = ReadyChecker::check_ready(&player.hand, &player.melds);
            if !ready_tiles.is_empty() {
                // 可以听牌，优先出定缺门的牌
                if let Some(tile) = find_declared_suit_tile(player, player.declared_suit) {
                    return Action::Discard { tile };
                }
            }
        }
        
        // 优先出定缺门的牌
        if let Some(tile) = find_declared_suit_tile(player, player.declared_suit) {
            return Action::Discard { tile };
        }
        
        // 否则随机出一张牌
        if let Some((tile, _)) = player.hand.tiles_map().iter().next() {
            Action::Discard { tile: *tile }
        } else {
            Action::Pass
        }
    }

    /// 查找定缺门的牌
    fn find_declared_suit_tile(player: &crate::game::player::Player, declared_suit: Option<Suit>) -> Option<Tile> {
        if let Some(suit) = declared_suit {
            for (tile, _) in player.hand.tiles_map() {
                if tile.suit() == suit {
                    return Some(*tile);
                }
            }
        }
        None
    }
}

/// 动作回调 trait
/// 
/// 定义动作回调的标准接口
pub trait ActionCallback {
    /// 根据游戏状态返回玩家动作
    /// 
    /// # 参数
    /// 
    /// - `state`: 当前游戏状态
    /// - `player_id`: 玩家 ID
    /// 
    /// # 返回
    /// 
    /// 玩家选择的动作
    fn get_action(&mut self, state: &GameState, player_id: u8) -> Action;
}

/// 函数式动作回调适配器
/// 
/// 将函数转换为 ActionCallback trait
pub struct FnActionCallback<F> {
    callback: F,
}

impl<F> FnActionCallback<F>
where
    F: FnMut(&GameState, u8) -> Action,
{
    pub fn new(callback: F) -> Self {
        Self { callback }
    }
}

impl<F> ActionCallback for FnActionCallback<F>
where
    F: FnMut(&GameState, u8) -> Action,
{
    fn get_action(&mut self, state: &GameState, player_id: u8) -> Action {
        (self.callback)(state, player_id)
    }
}

