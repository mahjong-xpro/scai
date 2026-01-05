use crate::tile::{Hand, Tile, Suit};
use crate::game::rules;
use crate::game::state::GameState;
use crate::game::pong::PongHandler;
use crate::game::kong::KongHandler;

/// 动作掩码
/// 
/// 用于控制哪些动作是合法的
#[derive(Debug, Clone)]
pub struct ActionMask {
    /// 可以胡的牌
    pub can_win: Vec<Tile>,
    /// 可以碰的牌
    pub can_pong: Vec<Tile>,
    /// 可以杠的牌
    pub can_gang: Vec<Tile>,
    /// 可以出的牌
    pub can_discard: Vec<Tile>,
}

impl ActionMask {
    /// 创建新的动作掩码
    pub fn new() -> Self {
        Self {
            can_win: Vec::new(),
            can_pong: Vec::new(),
            can_gang: Vec::new(),
            can_discard: Vec::new(),
        }
    }

    /// 检查是否可以胡牌
    /// 
    /// # 参数
    /// 
    /// - `hand`: 手牌
    /// - `tile`: 要胡的牌
    /// - `state`: 游戏状态
    /// - `declared_suit`: 定缺的花色
    /// - `fans`: 当前番数
    /// - `is_self_draw`: 是否自摸（自摸不受过胡限制）
    /// - `player_id`: 玩家 ID（可选，如果不提供则使用 state.current_player）
    /// 
    /// # 返回
    /// 
    /// `true` 表示可以胡，`false` 表示不能胡
    pub fn can_win(
        &self,
        hand: &Hand,
        tile: &Tile,
        state: &GameState,
        declared_suit: Option<Suit>,
        fans: u32,
        is_self_draw: bool,
    ) -> bool {
        self.can_win_with_player_id(hand, tile, state, declared_suit, fans, is_self_draw, None)
    }
    
    /// 检查是否可以胡牌（带 player_id 参数）
    /// 
    /// # 参数
    /// 
    /// - `hand`: 手牌
    /// - `tile`: 要胡的牌
    /// - `state`: 游戏状态
    /// - `declared_suit`: 定缺的花色
    /// - `fans`: 当前番数
    /// - `is_self_draw`: 是否自摸（自摸不受过胡限制）
    /// - `player_id`: 玩家 ID（可选，如果不提供则使用 state.current_player）
    /// 
    /// # 返回
    /// 
    /// `true` 表示可以胡，`false` 表示不能胡
    pub fn can_win_with_player_id(
        &self,
        hand: &Hand,
        tile: &Tile,
        state: &GameState,
        declared_suit: Option<Suit>,
        fans: u32,
        is_self_draw: bool,
        player_id_opt: Option<u8>,
    ) -> bool {
        // 检查缺一门
        if !rules::check_missing_suit(hand, declared_suit) {
            return false;
        }

        // 检查过胡锁定（使用新的 Player.passed_hu_fan 机制）
        let player_id = player_id_opt.unwrap_or(state.current_player) as usize;
        if player_id < state.players.len() {
            let player = &state.players[player_id];
            if !rules::check_passed_win_restriction(
                fans,
                player.passed_hu_fan,
                is_self_draw,
            ) {
                return false;
            }
        }

        // 兼容旧版：检查过胡限制（基于 PassedWin 记录）
        if player_id < state.passed_wins.len() {
            if !rules::can_win_after_pass(
                tile,
                fans,
                &state.passed_wins[player_id],
                state.turn,
            ) {
                return false;
            }
        }

        true
    }

    /// 检查是否可以吃牌（四川麻将禁止吃牌）
    pub fn can_chi(&self) -> bool {
        false // 四川麻将严禁"吃"
    }

    /// 生成动作掩码
    /// 
    /// 根据当前游戏状态生成所有可用的动作
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 玩家 ID
    /// - `state`: 游戏状态
    /// - `discarded_tile`: 别人打出的牌（如果是响应别人的出牌）
    /// 
    /// # 返回
    /// 
    /// ActionMask 实例
    pub fn generate(
        player_id: u8,
        state: &GameState,
        discarded_tile: Option<Tile>,
    ) -> Self {
        let mut mask = ActionMask::new();
        
        if player_id >= 4 {
            return mask;
        }
        
        let player = &state.players[player_id as usize];
        
        // 检查定缺色状态：如果还有定缺门的牌，必须严格限制动作
        let has_declared_suit_tiles = player.has_declared_suit_tiles();
        let declared_suit = player.declared_suit;
        
        // 如果是响应别人的出牌
        if let Some(tile) = discarded_tile {
            // 检查是否可以胡牌
            if let Some(declared) = declared_suit {
                // 如果还有定缺门的牌，不能胡非定缺色的牌
                if has_declared_suit_tiles && tile.suit() != declared {
                    // 严格屏蔽：定缺色未打完时，不能胡非定缺色的牌
                } else {
                    // 检查是否能胡
                    use crate::tile::win_check::WinChecker;
                    let mut test_hand = player.hand.clone();
                    test_hand.add_tile(tile);
                    let mut checker = WinChecker::new();
                    let melds_count = player.melds.len() as u8;
                    let result = checker.check_win_with_melds(&test_hand, melds_count);
                    if result.is_win && mask.can_win(&player.hand, &tile, state, Some(declared), 1, false) {
                        mask.can_win.push(tile);
                    }
                }
            } else {
                // 未定缺的情况（理论上不应该发生）
                use crate::tile::win_check::WinChecker;
                let mut test_hand = player.hand.clone();
                test_hand.add_tile(tile);
                let mut checker = WinChecker::new();
                let melds_count = player.melds.len() as u8;
                let result = checker.check_win_with_melds(&test_hand, melds_count);
                if result.is_win && mask.can_win(&player.hand, &tile, state, None, 1, false) {
                    mask.can_win.push(tile);
                }
            }
            
            // 检查是否可以碰牌
            // 严格检查：如果还有定缺门的牌，不能碰非定缺色的牌
            if let Some(pongable) = PongHandler::get_pongable_tile(player, &tile) {
                if has_declared_suit_tiles {
                    // 如果还有定缺门的牌，只能碰定缺色的牌
                    if let Some(declared) = declared_suit {
                        if tile.suit() == declared {
                            mask.can_pong.push(pongable);
                        }
                    }
                } else {
                    // 定缺门已打完，可以碰任何牌
                    mask.can_pong.push(pongable);
                }
            }
            
            // 检查是否可以直杠
            // 严格检查：如果还有定缺门的牌，不能杠非定缺色的牌
            if KongHandler::can_direct_kong(player, &tile).is_some() {
                if has_declared_suit_tiles {
                    // 如果还有定缺门的牌，只能杠定缺色的牌
                    if let Some(declared) = declared_suit {
                        if tile.suit() == declared {
                            mask.can_gang.push(tile);
                        }
                    }
                } else {
                    // 定缺门已打完，可以杠任何牌
                    mask.can_gang.push(tile);
                }
            }
        } else {
            // 自己的回合，检查可以出的牌
            // 严格检查：如果还有定缺门的牌，只能出定缺色的牌
            for (tile, _) in player.hand.tiles_map() {
                if has_declared_suit_tiles {
                    // 如果还有定缺门的牌，只能出定缺色的牌
                    if let Some(declared) = declared_suit {
                        if tile.suit() == declared {
                            mask.can_discard.push(*tile);
                        }
                    }
                } else {
                    // 定缺门已打完，可以出任何牌
                    mask.can_discard.push(*tile);
                }
            }
            
            // 检查是否可以加杠或暗杠
            // 严格检查：如果还有定缺门的牌，不能杠非定缺色的牌
            for (tile, _) in player.hand.tiles_map() {
                if has_declared_suit_tiles {
                    // 如果还有定缺门的牌，只能杠定缺色的牌
                    if let Some(declared) = declared_suit {
                        if tile.suit() != declared {
                            continue; // 跳过非定缺色的牌
                        }
                    }
                }
                
                // 检查加杠
                if KongHandler::can_add_kong(player, tile).is_some() {
                    mask.can_gang.push(*tile);
                }
                // 检查暗杠
                if KongHandler::can_concealed_kong(player, tile).is_some() {
                    mask.can_gang.push(*tile);
                }
            }
        }
        
        mask
    }

    /// 将动作掩码转换为布尔数组
    /// 
    /// 动作空间定义：
    /// - 索引 0-107: 出牌动作（对应 108 种牌）
    /// - 索引 108-215: 碰牌动作（对应 108 种牌）
    /// - 索引 216-323: 杠牌动作（对应 108 种牌）
    /// - 索引 324-431: 胡牌动作（对应 108 种牌）
    /// - 索引 432: 摸牌动作
    /// - 索引 433: 过（放弃）动作
    /// 
    /// 总共 434 个动作
    /// 
    /// # 参数
    /// 
    /// - `is_own_turn`: 是否是自己回合（True = 可以出牌/摸牌/过，False = 只能响应）
    /// - `discarded_tile`: 别人打出的牌（如果是响应别人的出牌）
    /// 
    /// # 返回
    /// 
    /// 434 个布尔值的数组，`true` 表示该动作合法，`false` 表示非法
    pub fn to_bool_array(&self, is_own_turn: bool, discarded_tile: Option<Tile>) -> [bool; 434] {
        let mut mask = [false; 434];
        
        if is_own_turn {
            // 自己的回合：可以出牌、摸牌、过、加杠、暗杠
            
            // 出牌动作（索引 0-107）
            for tile in &self.can_discard {
                if let Some(idx) = Self::tile_to_index(*tile) {
                    if idx < 108 {
                        mask[idx] = true;
                    }
                }
            }
            
            // 杠牌动作（索引 216-323）- 加杠和暗杠
            for tile in &self.can_gang {
                if let Some(idx) = Self::tile_to_index(*tile) {
                    let kong_idx = idx + 216;
                    if kong_idx < 324 {
                        mask[kong_idx] = true;
                    }
                }
            }
            
            // 摸牌动作（索引 432）
            mask[432] = true;
            
            // 过动作（索引 433）- 自己的回合也可以过（虽然不常见）
            mask[433] = true;
        } else {
            // 响应别人的出牌：可以胡、碰、直杠、过
            
            if let Some(tile) = discarded_tile {
                // 胡牌动作（索引 324-431）
                if self.can_win.contains(&tile) {
                    if let Some(idx) = Self::tile_to_index(tile) {
                        let win_idx = idx + 324;
                        if win_idx < 432 {
                            mask[win_idx] = true;
                        }
                    }
                }
                
                // 碰牌动作（索引 108-215）
                if self.can_pong.contains(&tile) {
                    if let Some(idx) = Self::tile_to_index(tile) {
                        let pong_idx = idx + 108;
                        if pong_idx < 216 {
                            mask[pong_idx] = true;
                        }
                    }
                }
                
                // 杠牌动作（索引 216-323）- 直杠
                if self.can_gang.contains(&tile) {
                    if let Some(idx) = Self::tile_to_index(tile) {
                        let kong_idx = idx + 216;
                        if kong_idx < 324 {
                            mask[kong_idx] = true;
                        }
                    }
                }
            }
            
            // 过动作（索引 433）- 响应时可以过
            mask[433] = true;
        }
        
        mask
    }

    /// 从布尔数组验证动作是否合法
    /// 
    /// # 参数
    /// 
    /// - `action_mask`: 434 个布尔值的数组
    /// - `action_index`: 动作索引（0-433）
    /// 
    /// # 返回
    /// 
    /// `true` 表示动作合法，`false` 表示非法
    pub fn is_action_legal(action_mask: &[bool; 434], action_index: usize) -> bool {
        if action_index >= 434 {
            return false;
        }
        action_mask[action_index]
    }

    /// 获取所有可能的牌（用于索引映射）
    fn all_tiles() -> Vec<Tile> {
        let mut tiles = Vec::with_capacity(108);
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            for rank in 1..=9 {
                let tile = match suit {
                    Suit::Wan => Tile::Wan(rank),
                    Suit::Tong => Tile::Tong(rank),
                    Suit::Tiao => Tile::Tiao(rank),
                };
                tiles.push(tile);
            }
        }
        tiles
    }

    /// 将牌映射到索引（0-107）
    /// 
    /// # 参数
    /// 
    /// - `tile`: 牌
    /// 
    /// # 返回
    /// 
    /// 索引（0-107），如果牌无效则返回 None
    pub fn tile_to_index(tile: Tile) -> Option<usize> {
        let suit_idx = match tile.suit() {
            Suit::Wan => 0,
            Suit::Tong => 1,
            Suit::Tiao => 2,
        };
        let rank = tile.rank();
        if rank < 1 || rank > 9 {
            return None;
        }
        Some(suit_idx * 9 + (rank - 1) as usize)
    }

    /// 从索引获取牌
    /// 
    /// # 参数
    /// 
    /// - `index`: 索引（0-107）
    /// 
    /// # 返回
    /// 
    /// 对应的牌，如果索引无效则返回 None
    pub fn index_to_tile(index: usize) -> Option<Tile> {
        if index >= 108 {
            return None;
        }
        let suit_idx = index / 9;
        let rank = ((index % 9) + 1) as u8;
        
        match suit_idx {
            0 => Some(Tile::Wan(rank)),
            1 => Some(Tile::Tong(rank)),
            2 => Some(Tile::Tiao(rank)),
            _ => None,
        }
    }

    /// 验证动作是否合法（严格检查）
    /// 
    /// 这个方法确保 AI 不能执行任何非法操作
    /// 
    /// # 参数
    /// 
    /// - `action_index`: 动作索引
    /// - `player_id`: 玩家 ID
    /// - `state`: 游戏状态
    /// - `is_own_turn`: 是否是自己回合
    /// - `discarded_tile`: 别人打出的牌（如果是响应别人的出牌）
    /// 
    /// # 返回
    /// 
    /// `true` 表示动作合法，`false` 表示非法
    pub fn validate_action(
        action_index: usize,
        player_id: u8,
        state: &GameState,
        is_own_turn: bool,
        discarded_tile: Option<Tile>,
    ) -> bool {
        if player_id >= 4 {
            return false;
        }
        
        let player = &state.players[player_id as usize];
        
        // 如果玩家已离场，只能执行过动作
        if player.is_out {
            return action_index == 433; // 只能过
        }
        
        // 生成动作掩码
        let mask = ActionMask::generate(player_id, state, discarded_tile);
        let bool_mask = mask.to_bool_array(is_own_turn, discarded_tile);
        
        // 检查动作是否在掩码中
        if !Self::is_action_legal(&bool_mask, action_index) {
            return false;
        }
        
        // 额外验证：根据动作类型进行更严格的检查
        if action_index < 108 {
            // 出牌动作
            if !is_own_turn {
                return false; // 不是自己回合不能出牌
            }
            if let Some(tile) = Self::index_to_tile(action_index) {
                // 检查是否还有定缺门的牌
                if let Some(declared) = player.declared_suit {
                    if player.has_declared_suit_tiles() && tile.suit() != declared {
                        // 如果还有定缺门的牌，不能出其他牌
                        return false;
                    }
                }
                // 检查手牌中是否有这张牌
                return player.hand.tiles_map().contains_key(&tile);
            }
        } else if action_index < 216 {
            // 碰牌动作
            if is_own_turn {
                return false; // 自己回合不能碰牌
            }
            if let Some(tile) = Self::index_to_tile(action_index - 108) {
                // 严格检查：如果还有定缺门的牌，不能碰非定缺色的牌
                if player.has_declared_suit_tiles() {
                    if let Some(declared) = player.declared_suit {
                        if tile.suit() != declared {
                            return false; // 定缺色未打完，不能碰非定缺色的牌
                        }
                    }
                }
                return PongHandler::can_pong(player, &tile);
            }
        } else if action_index < 324 {
            // 杠牌动作
            if let Some(tile) = Self::index_to_tile(action_index - 216) {
                // 严格检查：如果还有定缺门的牌，不能杠非定缺色的牌
                if player.has_declared_suit_tiles() {
                    if let Some(declared) = player.declared_suit {
                        if tile.suit() != declared {
                            return false; // 定缺色未打完，不能杠非定缺色的牌
                        }
                    }
                }
                
                if is_own_turn {
                    // 加杠或暗杠
                    return KongHandler::can_add_kong(player, &tile).is_some()
                        || KongHandler::can_concealed_kong(player, &tile).is_some();
                } else {
                    // 直杠
                    return KongHandler::can_direct_kong(player, &tile).is_some();
                }
            }
        } else if action_index < 432 {
            // 胡牌动作
            // 严格检查：如果还有定缺门的牌，不能胡非定缺色的牌
            if let Some(win_tile) = Self::index_to_tile(action_index - 324) {
                if player.has_declared_suit_tiles() {
                    if let Some(declared) = player.declared_suit {
                        if win_tile.suit() != declared {
                            return false; // 定缺色未打完，不能胡非定缺色的牌
                        }
                    }
                }
            }
            
            if is_own_turn {
                // 自摸（需要检查手牌）
                use crate::tile::win_check::WinChecker;
                let mut checker = WinChecker::new();
                let melds_count = player.melds.len() as u8;
                let result = checker.check_win_with_melds(&player.hand, melds_count);
                if !result.is_win {
                    return false;
                }
                // 检查缺一门
                if !rules::check_missing_suit(&player.hand, player.declared_suit) {
                    return false;
                }
            } else {
                // 点炮胡
                if let Some(tile) = discarded_tile {
                    if let Some(win_tile) = Self::index_to_tile(action_index - 324) {
                        if win_tile != tile {
                            return false;
                        }
                        // 严格检查：如果还有定缺门的牌，不能胡非定缺色的牌
                        if player.has_declared_suit_tiles() {
                            if let Some(declared) = player.declared_suit {
                                if tile.suit() != declared {
                                    return false; // 定缺色未打完，不能胡非定缺色的牌
                                }
                            }
                        }
                        // 检查是否可以胡这张牌
                        use crate::tile::win_check::WinChecker;
                        let mut test_hand = player.hand.clone();
                        test_hand.add_tile(tile);
                        let mut checker = WinChecker::new();
                        let melds_count = player.melds.len() as u8;
                        let result = checker.check_win_with_melds(&test_hand, melds_count);
                        if !result.is_win {
                            return false;
                        }
                        // 检查缺一门
                        if !rules::check_missing_suit(&player.hand, player.declared_suit) {
                            return false;
                        }
                        // 检查过胡限制
                        let player_id_usize = player_id as usize;
                        if player_id_usize < state.passed_wins.len() {
                            // 需要计算番数，这里简化处理
                            // 使用新的过胡锁定检查
                            let player = &state.players[player_id_usize];
                            if !rules::check_passed_win_restriction(1, player.passed_hu_fan, false) {
                                return false;
                            }
                        }
                    }
                }
            }
        } else if action_index == 432 {
            // 摸牌动作
            return is_own_turn; // 只有自己回合才能摸牌
        } else if action_index == 433 {
            // 过动作
            return true; // 总是可以过
        }
        
        false
    }
}

impl Default for ActionMask {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::game::state::PassedWin;

    #[test]
    fn test_can_chi() {
        let mask = ActionMask::new();
        assert!(!mask.can_chi()); // 四川麻将禁止吃牌
    }

    #[test]
    fn test_can_win_missing_suit() {
        let mut hand = Hand::new();
        // 添加万子和筒子
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Tong(1));
        
        let state = GameState::new();
        let mask = ActionMask::new();
        
        // 定缺条子，但手牌中没有条子，可以胡
        assert!(mask.can_win(&hand, &Tile::Wan(1), &state, Some(Suit::Tiao), 1, false));
        
        // 定缺万子，但手牌中还有万子，不能胡
        assert!(!mask.can_win(&hand, &Tile::Wan(1), &state, Some(Suit::Wan), 1, false));
    }

    #[test]
    fn test_can_win_after_pass() {
        let hand = Hand::new();
        let mut state = GameState::new();
        state.current_player = 0;
        state.turn = 10;
        
        // 添加放弃的胡牌记录
        state.passed_wins[0].push(PassedWin {
            tile: Tile::Wan(5),
            fans: 4,
            turn: 8,
        });
        
        let mask = ActionMask::new();
        
        // 尝试胡同一张牌，番数更低，不能胡
        assert!(!mask.can_win(&hand, &Tile::Wan(5), &state, None, 2, false));
        
        // 尝试胡同一张牌，番数更高，可以胡
        assert!(mask.can_win(&hand, &Tile::Wan(5), &state, None, 8, false));
        
        // 尝试胡不同的牌，可以胡
        assert!(mask.can_win(&hand, &Tile::Wan(6), &state, None, 2, false));
    }

    #[test]
    fn test_to_bool_array_own_turn() {
        let mut state = GameState::new();
        let player_id: u8 = 0;
        
        // 设置玩家手牌
        state.players[player_id as usize].hand.add_tile(Tile::Wan(1));
        state.players[player_id as usize].hand.add_tile(Tile::Wan(2));
        
        // 生成动作掩码
        let mask = ActionMask::generate(player_id, &state, None);
        let bool_mask = mask.to_bool_array(true, None);
        
        // 检查出牌动作是否合法
        let tile_idx = ActionMask::tile_to_index(Tile::Wan(1)).unwrap();
        assert!(bool_mask[tile_idx]);
        
        // 检查摸牌动作是否合法
        assert!(bool_mask[432]);
        
        // 检查过动作是否合法
        assert!(bool_mask[433]);
    }

    #[test]
    fn test_to_bool_array_response() {
        let mut state = GameState::new();
        let player_id: u8 = 0;
        
        // 设置玩家手牌（有两张 1 万，可以碰）
        state.players[player_id as usize].hand.add_tile(Tile::Wan(1));
        state.players[player_id as usize].hand.add_tile(Tile::Wan(1));
        
        // 生成动作掩码（响应别人出的 1 万）
        let mask = ActionMask::generate(player_id, &state, Some(Tile::Wan(1)));
        let bool_mask = mask.to_bool_array(false, Some(Tile::Wan(1)));
        
        // 检查碰牌动作是否合法
        let pong_idx = ActionMask::tile_to_index(Tile::Wan(1)).unwrap() + 108;
        assert!(bool_mask[pong_idx]);
        
        // 检查过动作是否合法
        assert!(bool_mask[433]);
    }

    #[test]
    fn test_tile_index_conversion() {
        // 测试所有牌的索引转换
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            for rank in 1..=9 {
                let tile = match suit {
                    Suit::Wan => Tile::Wan(rank),
                    Suit::Tong => Tile::Tong(rank),
                    Suit::Tiao => Tile::Tiao(rank),
                };
                
                let idx = ActionMask::tile_to_index(tile).unwrap();
                let converted_tile = ActionMask::index_to_tile(idx).unwrap();
                
                assert_eq!(tile, converted_tile);
            }
        }
    }

    #[test]
    fn test_validate_action_illegal() {
        let state = GameState::new();
        let player_id: u8 = 0;
        
        // 尝试执行非法动作（索引超出范围）
        assert!(!ActionMask::validate_action(500, player_id, &state, true, None));
        
        // 尝试在响应时出牌（非法）
        assert!(!ActionMask::validate_action(0, player_id, &state, false, Some(Tile::Wan(1))));
        
        // 尝试在自己回合碰牌（非法）
        assert!(!ActionMask::validate_action(108, player_id, &state, true, None));
    }

    #[test]
    fn test_validate_action_legal() {
        let mut state = GameState::new();
        let player_id: u8 = 0;
        
        // 设置玩家手牌
        state.players[player_id as usize].hand.add_tile(Tile::Wan(1));
        
        // 验证出牌动作（合法）
        let tile_idx = ActionMask::tile_to_index(Tile::Wan(1)).unwrap();
        assert!(ActionMask::validate_action(tile_idx, player_id, &state, true, None));
        
        // 验证摸牌动作（合法）
        assert!(ActionMask::validate_action(432, player_id, &state, true, None));
        
        // 验证过动作（合法）
        assert!(ActionMask::validate_action(433, player_id, &state, true, None));
    }
}

