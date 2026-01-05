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
/// # 参数
/// 
/// - `state`: 游戏状态
/// - `player_id`: 当前玩家视角（0-3）
/// - `py`: Python 解释器
/// 
/// # 返回
/// 
/// NumPy 数组，形状为 (64, 4, 9)
#[pyfunction]
pub fn state_to_tensor(
    state: &PyGameState,
    player_id: u8,
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
        
        // 特征平面索引
        let mut plane_idx = 0;
        
        // 平面 0-3: 自己的手牌（4 层，表示数量 1-4）
        for count in 1..=4 {
            let player = &game_state.players[player_id as usize];
            for (tile, &tile_count) in player.hand.tiles_map() {
                if tile_count == count {
                    let (suit_idx, rank_idx) = tile_to_indices(tile);
                    data[[plane_idx, suit_idx, rank_idx]] = 1.0;
                }
            }
            plane_idx += 1;
        }
        
        // 平面 4-7: 其他三个玩家的手牌（每个玩家 4 层）
        for other_player_id in 0..4 {
            if other_player_id == player_id {
                continue;
            }
            for count in 1..=4 {
                let player = &game_state.players[other_player_id as usize];
                for (tile, &tile_count) in player.hand.tiles_map() {
                    if tile_count == count {
                        let (suit_idx, rank_idx) = tile_to_indices(tile);
                        data[[plane_idx, suit_idx, rank_idx]] = 1.0;
                    }
                }
                plane_idx += 1;
            }
        }
        
        // 平面 28-31: 定缺状态（4 个玩家，每个玩家 1 层）
        for p_id in 0..4 {
            if let Some(declared) = game_state.players[p_id].declared_suit {
                let suit_idx = declared as usize;
                // 标记整个花色
                for rank in 0..9 {
                    data[[plane_idx, suit_idx, rank]] = 1.0;
                }
            }
            plane_idx += 1;
        }
        
        // 平面 32-35: 已碰/杠的牌（4 个玩家）
        for p_id in 0..4 {
            for meld in &game_state.players[p_id].melds {
                let tile = match meld {
                    crate::game::scoring::Meld::Triplet { tile } => *tile,
                    crate::game::scoring::Meld::Kong { tile, .. } => *tile,
                };
                let (suit_idx, rank_idx) = tile_to_indices(&tile);
                data[[plane_idx, suit_idx, rank_idx]] = 1.0;
            }
            plane_idx += 1;
        }
        
        // 平面 36-39: 已打出的牌（4 个玩家）
        // 注意：这里需要额外的数据结构来记录已打出的牌
        // 暂时跳过，后续可以扩展
        
        // 平面 40-43: 玩家状态（是否离场、是否听牌等）
        for p_id in 0..4 {
            if game_state.players[p_id].is_out {
                // 标记整个平面
                for suit in 0..3 {
                    for rank in 0..9 {
                        data[[plane_idx, suit, rank]] = 1.0;
                    }
                }
            }
            plane_idx += 1;
        }
        
        // 平面 44-47: 听牌状态
        for p_id in 0..4 {
            if game_state.players[p_id].is_ready {
                // 标记整个平面
                for suit in 0..3 {
                    for rank in 0..9 {
                        data[[plane_idx, suit, rank]] = 1.0;
                    }
                }
            }
            plane_idx += 1;
        }
        
        // 平面 48-51: 回合信息
        // 使用平面编码回合数（简化版本）
        let turn_planes = [
            (game_state.turn % 4) as usize,
            ((game_state.turn / 4) % 4) as usize,
            ((game_state.turn / 16) % 4) as usize,
            ((game_state.turn / 64) % 4) as usize,
        ];
        for (i, &plane) in turn_planes.iter().enumerate() {
            plane_idx = 48 + i;
            for suit in 0..3 {
                for rank in 0..9 {
                    if plane > 0 {
                        data[[plane_idx, suit, rank]] = plane as f32 / 4.0;
                    }
                }
            }
        }
        
        // 平面 52-55: 当前玩家信息
        for p_id in 0..4 {
            if p_id == game_state.current_player as usize {
                // 标记整个平面
                for suit in 0..3 {
                    for rank in 0..9 {
                        data[[plane_idx, suit, rank]] = 1.0;
                    }
                }
            }
            plane_idx += 1;
        }
        
        // 平面 56-59: 最后一张牌标记
        if game_state.is_last_tile {
            for suit in 0..3 {
                for rank in 0..9 {
                    data[[56, suit, rank]] = 1.0;
                }
            }
        }
        
        // 平面 60-63: 保留用于未来扩展
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

