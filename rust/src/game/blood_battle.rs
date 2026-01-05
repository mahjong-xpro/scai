use crate::tile::Suit;
use crate::game::state::GameState;

/// 血战到底规则实现
pub struct BloodBattleRules;

impl BloodBattleRules {
    /// 初始定缺（三花色必缺一）
    /// 
    /// 每个玩家必须选择一种花色（万、筒、条）作为定缺门
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 玩家 ID
    /// - `suit`: 要定缺的花色
    /// - `state`: 游戏状态
    /// 
    /// # 返回
    /// 
    /// 是否成功定缺
    pub fn declare_suit(
        player_id: u8,
        suit: Suit,
        state: &mut GameState,
    ) -> bool {
        if player_id >= 4 {
            return false;
        }
        
        state.player_mut(player_id).declare_suit(suit)
    }

    /// 检查所有玩家是否都已定缺
    pub fn all_players_declared(state: &GameState) -> bool {
        state.players.iter().all(|p| p.declared_suit.is_some())
    }

    /// 处理玩家离场逻辑
    /// 
    /// 一家胡牌后，其余玩家继续，直至牌墙摸完或仅剩一人
    /// 
    /// # 参数
    /// 
    /// - `winning_player_id`: 胡牌玩家 ID
    /// - `state`: 游戏状态
    /// 
    /// # 返回
    /// 
    /// 是否游戏继续（true 表示继续，false 表示结束）
    pub fn handle_player_out(
        winning_player_id: u8,
        state: &mut GameState,
    ) -> bool {
        // 标记玩家离场
        state.mark_player_out(winning_player_id);
        
        // 检查是否游戏结束
        // 游戏结束条件：
        // 1. 只剩一人未离场（out_count >= 3）
        // 2. 牌墙摸完（is_last_tile == true）
        !state.is_game_over()
    }

    /// 获取活跃玩家列表（未离场的玩家）
    pub fn get_active_players(state: &GameState) -> Vec<u8> {
        state.players
            .iter()
            .enumerate()
            .filter(|(_, p)| !p.is_out)
            .map(|(i, _)| i as u8)
            .collect()
    }

    /// 检查是否可以继续游戏
    /// 
    /// 游戏可以继续的条件：
    /// 1. 至少还有 2 个玩家未离场
    /// 2. 牌墙未摸完
    pub fn can_continue(state: &GameState) -> bool {
        let active_count = Self::get_active_players(state).len();
        active_count >= 2 && !state.is_last_tile
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_declare_suit() {
        let mut state = GameState::new();
        
        // 玩家 0 定缺万子
        assert!(BloodBattleRules::declare_suit(0, Suit::Wan, &mut state));
        assert_eq!(state.players[0].declared_suit, Some(Suit::Wan));
        
        // 玩家 1 定缺筒子
        assert!(BloodBattleRules::declare_suit(1, Suit::Tong, &mut state));
        assert_eq!(state.players[1].declared_suit, Some(Suit::Tong));
    }

    #[test]
    fn test_all_players_declared() {
        let mut state = GameState::new();
        
        // 初始状态：未全部定缺
        assert!(!BloodBattleRules::all_players_declared(&state));
        
        // 所有玩家定缺
        for i in 0..4 {
            let suit = match i {
                0 => Suit::Wan,
                1 => Suit::Tong,
                2 => Suit::Tiao,
                _ => Suit::Wan,
            };
            BloodBattleRules::declare_suit(i, suit, &mut state);
        }
        
        assert!(BloodBattleRules::all_players_declared(&state));
    }

    #[test]
    fn test_handle_player_out() {
        let mut state = GameState::new();
        
        // 玩家 0 胡牌
        let can_continue = BloodBattleRules::handle_player_out(0, &mut state);
        
        assert!(state.players[0].is_out);
        assert_eq!(state.out_count, 1);
        assert!(can_continue); // 还有 3 个玩家，可以继续
        
        // 玩家 1 胡牌
        let can_continue = BloodBattleRules::handle_player_out(1, &mut state);
        assert_eq!(state.out_count, 2);
        assert!(can_continue); // 还有 2 个玩家，可以继续
        
        // 玩家 2 胡牌
        let can_continue = BloodBattleRules::handle_player_out(2, &mut state);
        assert_eq!(state.out_count, 3);
        assert!(!can_continue); // 只剩 1 个玩家，游戏结束
    }

    #[test]
    fn test_get_active_players() {
        let mut state = GameState::new();
        
        // 初始状态：所有玩家都活跃
        let active = BloodBattleRules::get_active_players(&state);
        assert_eq!(active.len(), 4);
        
        // 玩家 0 离场
        state.mark_player_out(0);
        let active = BloodBattleRules::get_active_players(&state);
        assert_eq!(active.len(), 3);
        assert!(!active.contains(&0));
    }

    #[test]
    fn test_can_continue() {
        let mut state = GameState::new();
        
        // 初始状态：可以继续
        assert!(BloodBattleRules::can_continue(&state));
        
        // 玩家 0 离场
        state.mark_player_out(0);
        assert!(BloodBattleRules::can_continue(&state)); // 还有 3 个玩家
        
        // 玩家 1 离场
        state.mark_player_out(1);
        assert!(BloodBattleRules::can_continue(&state)); // 还有 2 个玩家
        
        // 玩家 2 离场
        state.mark_player_out(2);
        assert!(!BloodBattleRules::can_continue(&state)); // 只剩 1 个玩家
    }
}

