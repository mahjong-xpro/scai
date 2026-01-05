use pyo3::prelude::*;
use numpy::{PyArray1, PyArray3};
use crate::tile::{Tile, Suit};
use crate::engine::action_mask::ActionMask;
use crate::python::game_state::PyGameState;
use crate::python::action_mask::PyActionMask;

/// 将游戏状态转换为 4D Tensor（在 Rust 侧完成，减少内存拷贝）
/// 
/// 特征图设计：64×4×9
/// - 64 个特征平面
/// - 4 个玩家
/// - 9 种牌（每种花色 1-9）
/// 
/// 核心特征平面（前 13 个）：
/// - Plane 0-3: 自身手牌（One-hot 表示 1-4 张）
/// - Plane 4-10: 三个对手的弃牌（带顺序感，每个对手约 2-3 个平面）
/// - Plane 11: 场上剩余牌堆计数
/// - Plane 12: 定缺掩码
/// 
/// Oracle 特征平面（仅训练时使用）：
/// - Plane 13-24: 对手暗牌（手牌）- 仅在 use_oracle=true 时填充
/// - Plane 46-55: 牌堆余牌分布 - 仅在 use_oracle=true 时填充
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
    if player_id >= 4 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid player ID",
        ));
    }

    // 创建 4D 数组 (64, 4, 9)
    let shape = [64, 4, 9];
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
        
        // Plane 4-10: 三个对手的弃牌（带顺序感）
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
        for p_id in 0..4 {
            if let Some(declared) = game_state.players[p_id].declared_suit {
                let suit_idx = declared as usize;
                // 在该玩家的定缺花色位置标记
                for rank in 0..9 {
                    data[[12, p_id, rank]] = 1.0;
                }
            }
        }
        
        // ========== 扩展特征平面（13-63）==========
        
        let use_oracle = use_oracle.unwrap_or(false);
        let mut plane_idx = 13;
        
        // 平面 13-24: 其他三个玩家的手牌（每个玩家 4 层）
        // 注意：这是 Oracle 特征，仅在训练时使用（use_oracle=true）
        if use_oracle {
            for other_player_id in 0..4 {
                if other_player_id == player_id {
                    continue;
                }
                for count in 1..=4 {
                    let player = &game_state.players[other_player_id as usize];
                    for (tile, &tile_count) in player.hand.tiles_map() {
                        if tile_count == count {
                            let (suit_idx, rank_idx) = tile_to_indices(tile);
                            if plane_idx < 25 {
                                data[[plane_idx, suit_idx, rank_idx]] = 1.0;
                            }
                        }
                    }
                    plane_idx += 1;
                }
            }
        }
        // 如果不在 Oracle 模式，Plane 13-24 保持为 0（不显示对手暗牌）
        
        // 确保 plane_idx 正确设置
        if !use_oracle {
            plane_idx = 25;  // 跳过对手手牌平面
        } else {
            plane_idx = 25;  // 对手手牌平面已填充
        }
        
        // 平面 25-28: 已碰/杠的牌（4 个玩家）
        for p_id in 0..4 {
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
        
        // 平面 29-32: 玩家状态（是否离场）
        for p_id in 0..4 {
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
        
        // 平面 33-36: 听牌状态
        for p_id in 0..4 {
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
        
        // 平面 37-40: 回合信息
        let turn_planes = [
            (game_state.turn % 4) as usize,
            ((game_state.turn / 4) % 4) as usize,
            ((game_state.turn / 16) % 4) as usize,
            ((game_state.turn / 64) % 4) as usize,
        ];
        for (i, &plane) in turn_planes.iter().enumerate() {
            if 37 + i < 64 {
                for suit in 0..3 {
                    for rank in 0..9 {
                        if plane > 0 {
                            data[[37 + i, suit, rank]] = plane as f32 / 4.0;
                        }
                    }
                }
            }
        }
        plane_idx = 41;
        
        // 平面 41-44: 当前玩家信息
        for p_id in 0..4 {
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
        
        // 平面 45: 最后一张牌标记
        if game_state.is_last_tile {
            for suit in 0..3 {
                for rank in 0..9 {
                    if 45 < 64 {
                        data[[45, suit, rank]] = 1.0;
                    }
                }
            }
        }
        
        // 平面 46-55: Oracle 特征 - 牌堆余牌分布（仅训练时使用）
        // 显示每张牌在牌堆中剩余的数量（0-4）
        if use_oracle {
            if let Some(wall_dist) = wall_tile_distribution {
                // wall_dist 应该是 108 个浮点数，对应 108 种牌
                // 每个值表示该牌在牌堆中剩余的数量（0-4）
                if wall_dist.len() == 108 {
                    let mut dist_idx = 0;
                    for suit in 0..3 {
                        for rank in 0..9 {
                            let count = wall_dist[dist_idx];
                            // 归一化到 [0, 1] 范围（除以 4）
                            let normalized = (count / 4.0).min(1.0);
                            
                            // 使用 Plane 46-50 记录牌堆余牌分布
                            // Plane 46: 0 张剩余
                            // Plane 47: 1 张剩余
                            // Plane 48: 2 张剩余
                            // Plane 49: 3 张剩余
                            // Plane 50: 4 张剩余
                            let plane_base = 46;
                            let count_int = count as u32;
                            
                            if count_int == 0 && plane_base < 64 {
                                data[[plane_base, suit, rank]] = 1.0;
                            } else if count_int == 1 && plane_base + 1 < 64 {
                                data[[plane_base + 1, suit, rank]] = 1.0;
                            } else if count_int == 2 && plane_base + 2 < 64 {
                                data[[plane_base + 2, suit, rank]] = 1.0;
                            } else if count_int == 3 && plane_base + 3 < 64 {
                                data[[plane_base + 3, suit, rank]] = 1.0;
                            } else if count_int >= 4 && plane_base + 4 < 64 {
                                data[[plane_base + 4, suit, rank]] = 1.0;
                            }
                            
                            // 同时记录归一化的数量值（用于更精确的信息）
                            if plane_base + 5 < 64 {
                                data[[plane_base + 5, suit, rank]] = normalized;
                            }
                            
                            dist_idx += 1;
                        }
                    }
                }
            }
        }
        // 如果不在 Oracle 模式，Plane 46-55 保持为 0（不显示牌堆余牌分布）
        
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

