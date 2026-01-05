use crate::tile::{Tile, Suit};
use crate::game::action::Action;
use crate::game::scoring::ActionFlags;
use crate::game::player::Player;
use std::collections::HashMap;
use rand::rngs::StdRng;
use rand::SeedableRng;
use rand::seq::SliceRandom;

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

    /// 确定性填充未知牌（Determinization）
    /// 
    /// 用于 ISMCTS（信息集蒙特卡洛树搜索），根据已知的可见牌，随机分配剩下的牌到对手手中。
    /// 
    /// # 参数
    /// 
    /// - `viewer_id`: 观察者玩家 ID（当前玩家视角，只有该玩家的手牌是已知的）
    /// - `remaining_wall_count`: 牌墙剩余牌数（用于计算未知牌数）
    /// - `seed`: 随机数种子（用于确定性随机分配）
    /// 
    /// # 算法
    /// 
    /// 1. 统计所有已知的牌：
    ///    - 观察者的手牌
    ///    - 所有玩家的明牌（碰/杠的牌组）
    ///    - 所有玩家的弃牌
    /// 2. 计算剩余未知的牌：108 - 已知牌数 - 牌墙剩余牌数
    /// 3. 使用 seed 生成确定性随机数
    /// 4. 将剩余牌随机分配给对手（不包括观察者）
    /// 
    /// # 注意
    /// 
    /// - 此方法会修改对手的手牌，用于 AI 模拟推演
    /// - 使用相同的 seed 会产生相同的分配结果（确定性）
    /// - 对手的手牌数量会根据已碰/杠的牌组自动调整
    pub fn fill_unknown_cards(&mut self, viewer_id: u8, remaining_wall_count: usize, seed: u64) {
        if viewer_id >= 4 {
            return;
        }

        // 1. 统计所有已知的牌
        let mut known_tiles: HashMap<Tile, u8> = HashMap::new();

        // 观察者的手牌（已知）
        for (tile, &count) in self.players[viewer_id as usize].hand.tiles_map() {
            *known_tiles.entry(*tile).or_insert(0) += count;
        }

        // 所有玩家的明牌（碰/杠的牌组，已知）
        for player in &self.players {
            for meld in &player.melds {
                match meld {
                    crate::game::scoring::Meld::Triplet { tile } => {
                        // 碰：3 张牌
                        *known_tiles.entry(*tile).or_insert(0) += 3;
                    }
                    crate::game::scoring::Meld::Kong { tile, .. } => {
                        // 杠：4 张牌
                        *known_tiles.entry(*tile).or_insert(0) += 4;
                    }
                }
            }
        }

        // 所有玩家的弃牌（已知）
        for discard_record in &self.discard_history {
            *known_tiles.entry(discard_record.tile).or_insert(0) += 1;
        }

        // 对手当前已有的手牌（如果已经被部分填充，也需要计入已知牌）
        for (i, player) in self.players.iter().enumerate() {
            if i != viewer_id as usize && !player.is_out {
                for (tile, &count) in player.hand.tiles_map() {
                    *known_tiles.entry(*tile).or_insert(0) += count;
                }
            }
        }

        // 2. 计算剩余未知的牌
        // 总共 108 张牌，减去已知的牌，再减去牌墙剩余牌数，就是需要分配给对手的牌
        let total_known: usize = known_tiles.values().sum::<u8>() as usize;
        let unknown_count = 108usize
            .saturating_sub(total_known)
            .saturating_sub(remaining_wall_count);

        if unknown_count == 0 {
            return; // 没有未知牌需要分配
        }

        // 3. 生成所有可能的牌，并减去已知的牌
        let mut available_tiles = Vec::new();
        for suit in [Suit::Wan, Suit::Tong, Suit::Tiao] {
            for rank in Tile::MIN_RANK..=Tile::MAX_RANK {
                let tile = match suit {
                    Suit::Wan => Tile::Wan(rank),
                    Suit::Tong => Tile::Tong(rank),
                    Suit::Tiao => Tile::Tiao(rank),
                };
                let known_count = known_tiles.get(&tile).copied().unwrap_or(0);
                // 每种牌有 4 张，减去已知的数量，就是可用的数量
                let available_count = 4usize.saturating_sub(known_count as usize);
                for _ in 0..available_count {
                    available_tiles.push(tile);
                }
            }
        }

        // 确保可用牌数不超过未知牌数（可能因为计算误差）
        if available_tiles.len() > unknown_count {
            available_tiles.truncate(unknown_count);
        }

        // 4. 使用 seed 生成确定性随机数
        let mut rng = StdRng::seed_from_u64(seed);
        available_tiles.shuffle(&mut rng);

        // 5. 计算每个对手应该有多少张手牌
        // 初始 13 张，每碰一次减 3 张，每杠一次减 4 张
        let mut opponent_hand_sizes = [0usize; 4];
        for (i, player) in self.players.iter().enumerate() {
            if i == viewer_id as usize {
                continue; // 跳过观察者
            }
            if player.is_out {
                continue; // 跳过已离场的玩家
            }
            
            // 初始 13 张
            let mut hand_size = 13;
            // 减去碰/杠的牌
            for meld in &player.melds {
                match meld {
                    crate::game::scoring::Meld::Triplet { .. } => {
                        hand_size -= 3; // 碰：3 张牌
                    }
                    crate::game::scoring::Meld::Kong { .. } => {
                        hand_size -= 4; // 杠：4 张牌
                    }
                }
            }
            opponent_hand_sizes[i] = hand_size;
        }

        // 6. 将剩余牌随机分配给对手
        let mut tile_index = 0;
        for (i, &needed) in opponent_hand_sizes.iter().enumerate() {
            if i == viewer_id as usize {
                continue; // 跳过观察者
            }
            if self.players[i].is_out {
                continue; // 跳过已离场的玩家
            }

            // 分配需要的牌
            for _ in 0..needed {
                if tile_index >= available_tiles.len() {
                    break; // 没有更多牌可分配
                }
                let tile = available_tiles[tile_index];
                // 检查是否可以添加（防止超过 4 张）
                if self.players[i].hand.tile_count(tile) < 4 {
                    self.players[i].hand.add_tile(tile);
                }
                tile_index += 1;
            }
        }
    }
}

impl Default for GameState {
    fn default() -> Self {
        Self::new()
    }
}

