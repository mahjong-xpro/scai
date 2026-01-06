use pyo3::prelude::*;
use numpy::{PyArray1, PyArray3};
use crate::tile::{Tile, Suit};
use crate::engine::action_mask::ActionMask;
use crate::python::game_state::PyGameState;
use crate::python::action_mask::PyActionMask;
use crate::game::constants::{NUM_FEATURE_PLANES, NUM_PLAYERS_FEATURE, RANKS_PER_SUIT};

/// 将游戏状态转换为 4D Tensor（在 Rust 侧完成，减少内存拷贝）
/// 
/// 特征图设计：64×4×9
/// - 64 个特征平面
/// - 4 个玩家
/// - 9 种牌（每种花色 1-9）
/// 
/// 核心特征平面（前 14 个）：
/// - Plane 0-3: 自身手牌（One-hot 表示 1-4 张）
/// - Plane 4-10: 三个对手的弃牌（带顺序感，每个对手约 2-3 个平面，向后兼容）
/// - Plane 11: 场上剩余牌堆计数
/// - Plane 12: 定缺掩码
/// - Plane 13: 每张牌在场上已出现的张数（0-4，归一化到 [0, 1]）- **墙内残余牌感**
/// - Plane 30: 每张牌的剩余未见牌张数（0-4，归一化到 [0, 1]）- **残牌感知（关键特征）**
/// 
/// 弃牌序列特征（关键特征，用于识别"做牌"意图）：
/// - Plane 14-17: 玩家0的弃牌序列（最近4次，最旧的在前，最新的在后）
/// - Plane 18-21: 玩家1的弃牌序列（最近4次）
/// - Plane 22-25: 玩家2的弃牌序列（最近4次）
/// - Plane 26-29: 玩家3的弃牌序列（最近4次）
/// 
/// 说明：这是 AI 识别"做牌"意图的关键特征。例如：
/// - 先打 9 万再打 1 万 → 可能在做清一色（先打边张，保留中张）
/// - 先打 5 万，再打 5 万 → 可能在做七对（打掉多余的中张）
/// - 先打 1 万，再打 9 万 → 可能在做全带幺（保留中张，打掉边张）
/// 
/// Oracle 特征平面（仅训练时使用）：
/// - Plane 31-42: 对手暗牌（手牌）- 仅在 use_oracle=true 时填充
/// - Plane 63: 牌堆余牌分布汇总 - 仅在 use_oracle=true 时填充
/// 
/// # 参数
/// 
/// - `state`: 游戏状态
/// - `player_id`: 当前玩家视角（0-3）
/// - `remaining_tiles`: 剩余牌数（可选，用于 Plane 11，默认 0）
/// - `use_oracle`: 是否使用 Oracle 特征（上帝视角，仅训练时使用，默认 false）
/// - `wall_tile_distribution`: 牌堆余牌分布（可选，108 个浮点数，每张牌的剩余数量 0-4）
/// - `py`: Python 解释器
/// 
/// # 返回
/// 
/// NumPy 数组，形状为 (64, 4, 9)
#[pyfunction]
pub fn state_to_tensor(
    state: &PyGameState,
    player_id: u8,
    remaining_tiles: Option<usize>,
    use_oracle: Option<bool>,
    wall_tile_distribution: Option<Vec<f32>>,
    py: Python,
) -> PyResult<Py<PyArray3<f32>>> {
    use crate::game::constants::NUM_PLAYERS;
    
    if player_id >= NUM_PLAYERS {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid player ID",
        ));
    }

    // 创建 4D 数组 (NUM_FEATURE_PLANES, NUM_PLAYERS_FEATURE, RANKS_PER_SUIT)
    let shape = [NUM_FEATURE_PLANES, NUM_PLAYERS_FEATURE, RANKS_PER_SUIT];
    let array = PyArray3::<f32>::zeros(py, shape, false);
    
    unsafe {
        let mut data = array.as_array_mut();
        let game_state = state.inner();
        
        // ========== 核心特征平面（前 13 个）==========
        
        // Plane 0-3: 自身手牌（One-hot 表示 1-4 张）
        // 每个平面表示手牌中该牌的数量（1-4 张）
        for count in 1..=4 {
            let player = &game_state.players[player_id as usize];
            for (tile, &tile_count) in player.hand.tiles_map() {
                if tile_count == count {
                    let (suit_idx, rank_idx) = tile_to_indices(tile);
                    data[[(count - 1) as usize, suit_idx, rank_idx]] = 1.0;
                }
            }
        }
        
        // Plane 4-10: 三个对手的弃牌（带顺序感，保留向后兼容）
        // 分配：对手 1 用 Plane 4-5，对手 2 用 Plane 6-7，对手 3 用 Plane 8-9，Plane 10 用于最近弃牌
        let mut opponent_idx = 0;
        let mut opponent_planes = [4, 6, 8]; // 每个对手的起始平面
        
        // 按顺序处理三个对手
        for other_player_id in 0..4 {
            if other_player_id == player_id {
                continue;
            }
            
            // 获取该对手的弃牌（从弃牌历史中筛选）
            let opponent_discards: Vec<_> = game_state.discard_history
                .iter()
                .filter(|record| record.player_id == other_player_id)
                .collect();
            
            // 使用该对手的平面记录弃牌（最近弃牌优先）
            let start_plane = opponent_planes[opponent_idx];
            for (i, discard_record) in opponent_discards.iter().rev().take(2).enumerate() {
                if start_plane + i < 10 {
                    let (suit_idx, rank_idx) = tile_to_indices(&discard_record.tile);
                    data[[start_plane + i, suit_idx, rank_idx]] = 1.0;
                }
            }
            
            opponent_idx += 1;
        }
        
        // Plane 10: 最近一次弃牌（全局视角，带顺序感）
        // 记录最近一次弃牌，标记在 [10, suit_idx, rank_idx] 位置
        if let Some(last_discard) = game_state.discard_history.last() {
            let (suit_idx, rank_idx) = tile_to_indices(&last_discard.tile);
            // 标记最近弃牌的位置（全局视角，不区分玩家）
            data[[10, suit_idx, rank_idx]] = 1.0;
        }
        
        // Plane 14-29: 每个玩家的弃牌序列（完整顺序，关键特征）
        // 分配：每个玩家 4 个平面，记录最近 4 次弃牌
        // - Plane 14-17: 玩家0的弃牌序列（最旧的在前，最新的在后）
        // - Plane 18-21: 玩家1的弃牌序列
        // - Plane 22-25: 玩家2的弃牌序列
        // - Plane 26-29: 玩家3的弃牌序列
        // 
        // 这是 AI 识别"做牌"意图的关键特征
        // 例如：先打 9 万再打 1 万 → 可能在做清一色
        for p_id in 0..NUM_PLAYERS as usize {
            // 获取该玩家的弃牌（从弃牌历史中筛选，保持原始顺序）
            let player_discards: Vec<_> = game_state.discard_history
                .iter()
                .filter(|record| record.player_id as usize == p_id)
                .collect();
            
            // 为该玩家分配 4 个平面（Plane 14 + p_id * 4 到 Plane 17 + p_id * 4）
            let base_plane = 14 + p_id * 4;
            
            // 记录最近 4 次弃牌（最旧的在前，最新的在后）
            // 例如：如果玩家弃了 [1万, 2万, 3万, 4万, 5万]（按时间顺序）
            // 则记录 [2万, 3万, 4万, 5万]（最近4次，最旧的2万在第一个平面）
            let recent_discards: Vec<_> = player_discards
                .iter()
                .rev() // 反转，最新的在前
                .take(4) // 取最近4次
                .rev() // 再反转回来，最旧的在前
                .collect();
            
            for (i, discard_record) in recent_discards.iter().enumerate() {
                if base_plane + i < 64 {
                    let (suit_idx, rank_idx) = tile_to_indices(&discard_record.tile);
                    // 记录弃牌，同时记录时间信息（归一化到 [0, 1]）
                    // 时间越近，值越大（帮助 AI 理解时间顺序）
                    let time_weight = 1.0 - (i as f32 / 4.0); // 最新的为 1.0，最旧的为 0.75
                    data[[base_plane + i, suit_idx, rank_idx]] = time_weight;
                }
            }
        }
        
        // Plane 11: 场上剩余牌堆计数
        // 将剩余牌数归一化到 [0, 1] 范围（假设最多 108 张）
        let remaining = remaining_tiles.unwrap_or(0);
        let normalized_count = (remaining as f32 / 108.0).min(1.0);
        for suit in 0..3 {
            for rank in 0..9 {
                data[[11, suit, rank]] = normalized_count;
            }
        }
        
        // Plane 12: 定缺掩码
        // 标记每个玩家的定缺花色
        for p_id in 0..NUM_PLAYERS as usize {
            if let Some(declared) = game_state.players[p_id].declared_suit {
                let suit_idx = declared as usize;
                // 在该玩家的定缺花色位置标记
                for rank in 0..9 {
                    data[[12, p_id, rank]] = 1.0;
                }
            }
        }
        
        // Plane 13: 每张牌在场上已出现的张数（0-4，归一化到 [0, 1]）
        // 这是"墙内残余牌感"的关键特征，用于AI学会"算牌"
        // 统计所有可见的牌：手牌 + 碰/杠 + 弃牌
        let mut tile_visibility = [0u8; 27]; // 27 种牌（3 种花色 × 9 种牌），每种最多 4 张
        
        // 统计所有玩家的手牌
        for player in &game_state.players {
            for (tile, &count) in player.hand.tiles_map() {
                let (suit_idx, rank_idx) = tile_to_indices(tile);
                let tile_idx = suit_idx * 9 + rank_idx;
                if tile_idx < 27 {
                    tile_visibility[tile_idx] += count;
                }
            }
        }
        
        // 统计已碰/杠的牌
        for player in &game_state.players {
            for meld in &player.melds {
                let (tile, count) = match meld {
                    crate::game::scoring::Meld::Triplet { tile } => (*tile, 3),
                    crate::game::scoring::Meld::Kong { tile, .. } => (*tile, 4),
                };
                let (suit_idx, rank_idx) = tile_to_indices(&tile);
                let tile_idx = suit_idx * 9 + rank_idx;
                if tile_idx < 27 {
                    tile_visibility[tile_idx] += count;
                }
            }
        }
        
        // 统计弃牌历史
        for discard_record in &game_state.discard_history {
            let (suit_idx, rank_idx) = tile_to_indices(&discard_record.tile);
            let tile_idx = suit_idx * 9 + rank_idx;
            if tile_idx < 27 {
                tile_visibility[tile_idx] += 1;
            }
        }
        
        // 填充到 Plane 13（归一化到 [0, 1] 范围，除以 4）
        for suit in 0..3 {
            for rank in 0..9 {
                let tile_idx = suit * 9 + rank;
                let count = tile_visibility[tile_idx];
                // 归一化到 [0, 1] 范围（除以 4）
                let normalized = (count as f32 / 4.0).min(1.0);
                data[[13, suit, rank]] = normalized;
            }
        }
        
        // Plane 30: 每张牌的剩余未见牌张数（0-4，归一化到 [0, 1]）
        // 计算公式：Remaining(Tile) = 4 - Self(Tile) - Discarded(Tile) - Melded(Tile)
        // 这是"残牌感知"的关键特征，用于AI学会"算牌"和"绝张"判断
        // 
        // 重要性：
        // - 如果剩余 = 0，该牌已经绝张，打出去绝对安全（不会点炮）
        // - 如果剩余 = 1，需要谨慎（可能是对手听牌）
        // - 如果剩余 = 2-4，可以正常考虑
        // 
        // 顶级高手会算"绝张"。如果特征里没有这个，AI 永远学不会
        // "这张牌场上已经现了 3 张，我手里有 1 张，所以我打出去绝对不会有点炮风险"
        // 这种高级防御策略。
        for suit in 0..3 {
            for rank in 0..9 {
                let tile_idx = suit * 9 + rank;
                let appeared_count = tile_visibility[tile_idx];
                // 计算剩余未见牌张数：4 - 已出现的张数
                let remaining_count = 4u8.saturating_sub(appeared_count);
                
                // 归一化到 [0, 1] 范围（除以 4）
                let normalized = (remaining_count as f32 / 4.0).min(1.0);
                data[[30, suit, rank]] = normalized;
            }
        }
        
        // ========== 扩展特征平面（14-29, 31-63）==========
        // 注意：Plane 14-29 用于弃牌序列（每个玩家4个平面）
        // Plane 30 已用于剩余未见牌张数
        
        let use_oracle = use_oracle.unwrap_or(false);
        let mut plane_idx = 14; // 从 14 开始，因为 Plane 13 用于牌池可见性
        
        // 平面 14-25: 其他三个玩家的手牌（每个玩家 4 层）
        // 注意：这是 Oracle 特征，仅在训练时使用（use_oracle=true）
        if use_oracle {
            for other_player_id in 0..NUM_PLAYERS {
                if other_player_id == player_id {
                    continue;
                }
                for count in 1..=4 {
                    let player = &game_state.players[other_player_id as usize];
                    for (tile, &tile_count) in player.hand.tiles_map() {
                        if tile_count == count {
                            let (suit_idx, rank_idx) = tile_to_indices(tile);
                            if plane_idx < 26 {
                                data[[plane_idx, suit_idx, rank_idx]] = 1.0;
                            }
                        }
                    }
                    plane_idx += 1;
                }
            }
        }
        // 如果不在 Oracle 模式，Plane 14-25 保持为 0（不显示对手暗牌）
        
        // 确保 plane_idx 正确设置
        if !use_oracle {
            plane_idx = 26;  // 跳过对手手牌平面
        } else {
            plane_idx = 26;  // 对手手牌平面已填充
        }
        
        // 平面 25-28: 已碰/杠的牌（所有玩家）
        for p_id in 0..NUM_PLAYERS as usize {
            for meld in &game_state.players[p_id].melds {
                let tile = match meld {
                    crate::game::scoring::Meld::Triplet { tile } => *tile,
                    crate::game::scoring::Meld::Kong { tile, .. } => *tile,
                };
                let (suit_idx, rank_idx) = tile_to_indices(&tile);
                if plane_idx < 64 {
                    data[[plane_idx, suit_idx, rank_idx]] = 1.0;
                }
            }
            plane_idx += 1;
        }
        
        // 平面 47-50: 玩家状态（是否离场）
        for p_id in 0..NUM_PLAYERS as usize {
            if game_state.players[p_id].is_out {
                for suit in 0..3 {
                    for rank in 0..9 {
                        if plane_idx < 64 {
                            data[[plane_idx, suit, rank]] = 1.0;
                        }
                    }
                }
            }
            plane_idx += 1;
        }
        
        // 平面 51-54: 听牌状态
        for p_id in 0..NUM_PLAYERS as usize {
            if game_state.players[p_id].is_ready {
                for suit in 0..3 {
                    for rank in 0..9 {
                        if plane_idx < 64 {
                            data[[plane_idx, suit, rank]] = 1.0;
                        }
                    }
                }
            }
            plane_idx += 1;
        }
        
        // 平面 55-58: 回合信息
        let turn_planes = [
            (game_state.turn % 4) as usize,
            ((game_state.turn / 4) % 4) as usize,
            ((game_state.turn / 16) % 4) as usize,
            ((game_state.turn / 64) % 4) as usize,
        ];
        for (i, &plane) in turn_planes.iter().enumerate() {
            if 55 + i < 64 {
                for suit in 0..3 {
                    for rank in 0..9 {
                        if plane > 0 {
                            data[[55 + i, suit, rank]] = plane as f32 / 4.0;
                        }
                    }
                }
            }
        }
        plane_idx = 59;
        
        // 平面 59-62: 当前玩家信息
        for p_id in 0..NUM_PLAYERS as usize {
            if p_id == game_state.current_player as usize {
                for suit in 0..3 {
                    for rank in 0..9 {
                        if plane_idx < 64 {
                            data[[plane_idx, suit, rank]] = 1.0;
                        }
                    }
                }
            }
            plane_idx += 1;
        }
        
        // 平面 62: 最后一张牌标记
        if game_state.is_last_tile {
            for suit in 0..3 {
                for rank in 0..9 {
                    if 62 < 64 {
                        data[[62, suit, rank]] = 1.0;
                    }
                }
            }
        }
        
        // 平面 63: Oracle 特征 - 牌堆余牌分布汇总（仅训练时使用，简化版本）
        // 注意：由于平面空间有限，这里只记录一个汇总值
        // 完整的牌堆余牌分布需要更多平面，可以在需要时扩展
        if use_oracle {
            if let Some(wall_dist) = wall_tile_distribution {
                // wall_dist 应该是 108 个浮点数，对应 108 种牌
                // 每个值表示该牌在牌堆中剩余的数量（0-4）
                use crate::game::constants::TOTAL_TILES;
                if wall_dist.len() == TOTAL_TILES {
                    // 计算平均剩余牌数（归一化到 [0, 1]）
                    let avg_remaining: f32 = wall_dist.iter().sum::<f32>() / (TOTAL_TILES as f32 * 4.0);
                    for suit in 0..3 {
                        for rank in 0..9 {
                            if 63 < 64 {
                                data[[63, suit, rank]] = avg_remaining;
                            }
                        }
                    }
                }
            }
        }
        // 如果不在 Oracle 模式，Plane 63 保持为 0（不显示牌堆余牌分布）
        
        // 平面 56-63: 保留用于未来扩展
    }
    
    Ok(array.into())
}

/// 将动作掩码转换为 NumPy 数组
/// 
/// # 参数
/// 
/// - `mask`: 动作掩码
/// - `is_own_turn`: 是否是自己回合
/// - `discarded_tile`: 别人打出的牌（可选）
/// - `py`: Python 解释器
/// 
/// # 返回
/// 
/// NumPy 数组，形状为 (434,)，包含布尔值
#[pyfunction]
pub fn action_mask_to_array(
    mask: &PyActionMask,
    is_own_turn: bool,
    discarded_tile: Option<u8>,
    py: Python,
) -> PyResult<Py<PyArray1<bool>>> {
    let tile = discarded_tile.and_then(|idx| ActionMask::index_to_tile(idx as usize));
    let bool_mask = mask.inner().to_bool_array(is_own_turn, tile);
    
    // 创建 NumPy 数组（1D 数组，使用 PyArray1）
    use numpy::PyArray1;
    let array = PyArray1::from_vec(py, bool_mask.to_vec());
    
    Ok(array.into())
}

/// 辅助函数：将牌转换为索引
fn tile_to_indices(tile: &Tile) -> (usize, usize) {
    let suit_idx = match tile.suit() {
        Suit::Wan => 0,
        Suit::Tong => 1,
        Suit::Tiao => 2,
    };
    let rank_idx = (tile.rank() - 1) as usize;
    (suit_idx, rank_idx)
}

