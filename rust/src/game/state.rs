use crate::tile::Tile;
use crate::game::action::Action;
use crate::game::scoring::ActionFlags;
use crate::game::player::Player;

/// 杠牌记录
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GangRecord {
    /// 杠牌玩家 ID
    pub player_id: u8,
    /// 杠的牌
    pub tile: Tile,
    /// 是否暗杠
    pub is_concealed: bool,
    /// 杠牌回合数
    pub turn: u32,
}

/// 放弃的胡牌记录
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PassedWin {
    /// 放弃的牌
    pub tile: Tile,
    /// 放弃时的番数
    pub fans: u32,
    /// 放弃的回合数
    pub turn: u32,
}

/// 弃牌记录
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiscardRecord {
    /// 弃牌玩家 ID
    pub player_id: u8,
    /// 弃的牌
    pub tile: Tile,
    /// 弃牌回合数
    pub turn: u32,
}

/// 游戏状态
#[derive(Debug, Clone)]
pub struct GameState {
    /// 玩家（4 个玩家）
    pub players: [Player; 4],
    /// 上一个动作
    pub last_action: Option<Action>,
    /// 是否最后一张牌
    pub is_last_tile: bool,
    /// 杠牌历史记录
    pub gang_history: Vec<GangRecord>,
    /// 动作触发标志（当前玩家）
    pub action_flags: ActionFlags,
    /// 放弃的胡牌记录（4 个玩家）
    pub passed_wins: [Vec<PassedWin>; 4],
    /// 当前回合数
    pub turn: u32,
    /// 当前玩家 ID
    pub current_player: u8,
    /// 已离场玩家数量
    pub out_count: u8,
    /// 弃牌历史记录（按顺序记录所有弃牌）
    pub discard_history: Vec<DiscardRecord>,
}

impl GameState {
    /// 创建新的游戏状态
    pub fn new() -> Self {
        Self {
            players: [
                Player::new(0),
                Player::new(1),
                Player::new(2),
                Player::new(3),
            ],
            last_action: None,
            is_last_tile: false,
            gang_history: Vec::new(),
            action_flags: ActionFlags::new(),
            passed_wins: [Vec::new(), Vec::new(), Vec::new(), Vec::new()],
            turn: 0,
            current_player: 0,
            out_count: 0,
            discard_history: Vec::new(),
        }
    }

    /// 获取当前玩家
    pub fn current_player_mut(&mut self) -> &mut Player {
        &mut self.players[self.current_player as usize]
    }

    /// 获取当前玩家（不可变引用）
    pub fn current_player_ref(&self) -> &Player {
        &self.players[self.current_player as usize]
    }

    /// 获取玩家（可变引用）
    pub fn player_mut(&mut self, player_id: u8) -> &mut Player {
        &mut self.players[player_id as usize]
    }

    /// 获取玩家（不可变引用）
    pub fn player_ref(&self, player_id: u8) -> &Player {
        &self.players[player_id as usize]
    }

    /// 标记玩家离场（胡牌）
    pub fn mark_player_out(&mut self, player_id: u8) {
        if !self.players[player_id as usize].is_out {
            self.players[player_id as usize].mark_out();
            self.out_count += 1;
        }
    }

    /// 检查游戏是否结束
    /// 
    /// 游戏结束条件：
    /// 1. 牌墙摸完（is_last_tile == true）
    /// 2. 只剩一人未离场（out_count >= 3）
    pub fn is_game_over(&self) -> bool {
        self.is_last_tile || self.out_count >= 3
    }

    /// 获取下一个未离场的玩家
    pub fn next_active_player(&self) -> Option<u8> {
        let mut next = (self.current_player + 1) % 4;
        let mut attempts = 0;
        
        while self.players[next as usize].is_out && attempts < 4 {
            next = (next + 1) % 4;
            attempts += 1;
        }
        
        if !self.players[next as usize].is_out {
            Some(next)
        } else {
            None
        }
    }

    /// 检查自摸
    pub fn check_zi_mo(&mut self) {
        if let Some(Action::Draw) = self.last_action {
            self.action_flags.is_zi_mo = true;
        }
    }

    /// 检查杠上开花
    /// 
    /// # 参数
    /// 
    /// - `is_winning`: 是否要胡牌
    pub fn check_gang_kai(&mut self, is_winning: bool) {
        if is_winning {
            if let Some(Action::Gang { .. }) = self.last_action {
                self.action_flags.is_gang_kai = true;
            }
        }
    }

    /// 检查杠上炮
    /// 
    /// # 参数
    /// 
    /// - `discarded_tile`: 打出的牌
    /// - `is_winning`: 是否被别人胡
    pub fn check_gang_pao(&mut self, _discarded_tile: &Tile, is_winning: bool) {
        if is_winning {
            if let Some(Action::Gang { .. }) = self.last_action {
                self.action_flags.is_gang_pao = true;
            }
        }
    }

    /// 检查抢杠胡
    /// 
    /// # 参数
    /// 
    /// - `gang_tile`: 被抢杠的牌
    /// - `is_winning`: 是否要胡牌
    pub fn check_qiang_gang(&mut self, _gang_tile: &Tile, is_winning: bool) {
        if is_winning {
            // 检查是否在加杠时被胡
            // 这个需要更详细的游戏状态来判断
            self.action_flags.is_qiang_gang = true;
        }
    }

    /// 检查海底捞月
    pub fn check_hai_di(&mut self) {
        if self.is_last_tile {
            self.action_flags.is_hai_di = true;
        }
    }
}

impl Default for GameState {
    fn default() -> Self {
        Self::new()
    }
}

