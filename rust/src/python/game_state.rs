use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use crate::game::state::GameState;

/// Python 绑定的游戏状态
#[pyclass]
pub struct PyGameState {
    pub(crate) inner: GameState,
}

#[pymethods]
impl PyGameState {
    /// 创建新的游戏状态
    #[new]
    pub fn new() -> Self {
        Self {
            inner: GameState::new(),
        }
    }

    /// 获取当前玩家 ID
    #[getter]
    fn current_player(&self) -> u8 {
        self.inner.current_player
    }

    /// 设置当前玩家 ID
    #[setter]
    fn set_current_player(&mut self, player_id: u8) {
        self.inner.current_player = player_id;
    }

    /// 获取当前回合数
    #[getter]
    fn turn(&self) -> u32 {
        self.inner.turn
    }

    /// 检查游戏是否结束
    fn is_game_over(&self) -> bool {
        self.inner.is_game_over()
    }


    /// 获取玩家手牌（返回 Python 字典）
    fn get_player_hand(&self, player_id: u8, py: Python) -> PyResult<PyObject> {
        if player_id >= 4 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        let player = &self.inner.players[player_id as usize];
        let hand_dict = PyDict::new(py);
        
        for (tile, &count) in player.hand.tiles_map() {
            let tile_str = format!("{:?}", tile);
            hand_dict.set_item(tile_str, count)?;
        }
        
        Ok(hand_dict.into())
    }

    /// 获取玩家定缺花色
    fn get_player_declared_suit(&self, player_id: u8) -> PyResult<Option<String>> {
        if player_id >= 4 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        let player = &self.inner.players[player_id as usize];
        Ok(player.declared_suit.map(|s| format!("{:?}", s)))
    }

    /// 检查玩家是否已离场
    fn is_player_out(&self, player_id: u8) -> PyResult<bool> {
        if player_id >= 4 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        Ok(self.inner.players[player_id as usize].is_out)
    }

    /// 检查玩家是否听牌
    fn is_player_ready(&self, player_id: u8) -> PyResult<bool> {
        if player_id >= 4 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        Ok(self.inner.players[player_id as usize].is_ready)
    }

    /// 获取玩家已碰/杠的牌组
    fn get_player_melds(&self, player_id: u8, py: Python) -> PyResult<PyObject> {
        if player_id >= 4 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        let player = &self.inner.players[player_id as usize];
        let melds_list = PyList::empty(py);
        
        for meld in &player.melds {
            let meld_str = format!("{:?}", meld);
            melds_list.append(meld_str)?;
        }
        
        Ok(melds_list.into())
    }

    /// 获取已离场玩家数量
    #[getter]
    fn out_count(&self) -> u8 {
        self.inner.out_count
    }

    /// 检查是否是最后一张牌
    #[getter]
    fn is_last_tile(&self) -> bool {
        self.inner.is_last_tile
    }

    /// 将游戏状态转换为扁平化的张量（用于 AI 训练）
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 当前玩家视角（0-3）
    /// - `remaining_tiles`: 剩余牌数（可选，默认 0）
    /// - `py`: Python 解释器
    /// 
    /// # 返回
    /// 
    /// 扁平化的 Vec<f32>，包含：
    /// 1. 4D tensor 扁平化（64 × 4 × 9 = 2304 个浮点数）
    /// 2. 牌池可见性特征（108 个浮点数，每张牌的出现次数 0-4）
    /// 
    /// 总计：2304 + 108 = 2412 个浮点数
    fn to_tensor(&self, player_id: u8, remaining_tiles: Option<usize>, py: Python) -> PyResult<Vec<f32>> {
        use crate::python::tensor::state_to_tensor;
        
        if player_id >= 4 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        // 1. 获取 4D tensor
        let tensor_4d = state_to_tensor(self, player_id, remaining_tiles, py)?;
        
        // 2. 扁平化 4D tensor (64 × 4 × 9 = 2304)
        let mut result = Vec::with_capacity(2412);
        unsafe {
            let array = tensor_4d.as_ref(py);
            let data = array.as_array();
            
            // 按顺序扁平化：plane -> player -> rank
            for plane in 0..64 {
                for player in 0..4 {
                    for rank in 0..9 {
                        result.push(data[[plane, player, rank]]);
                    }
                }
            }
        }
        
        // 3. 添加牌池可见性特征（108 个浮点数）
        let tile_visibility = self.compute_tile_visibility();
        result.extend_from_slice(&tile_visibility);
        
        Ok(result)
    }

    /// 计算牌池可见性（每张牌出现了几张）
    /// 
    /// # 返回
    /// 
    /// 108 个浮点数，每个表示该牌目前出现了几张（0-4）
    fn compute_tile_visibility(&self) -> Vec<f32> {
        use crate::engine::action_mask::ActionMask;
        use crate::game::scoring::Meld;
        
        let mut visibility = vec![0.0f32; 108];
        
        // 统计所有玩家的手牌
        for player in &self.inner.players {
            for (tile, &count) in player.hand.tiles_map() {
                if let Some(idx) = ActionMask::tile_to_index(*tile) {
                    if idx < 108 {
                        visibility[idx] += count as f32;
                    }
                }
            }
        }
        
        // 统计已碰/杠的牌
        for player in &self.inner.players {
            for meld in &player.melds {
                let (tile, count) = match meld {
                    Meld::Triplet { tile } => (*tile, 3),
                    Meld::Kong { tile, .. } => (*tile, 4),
                };
                if let Some(idx) = ActionMask::tile_to_index(tile) {
                    if idx < 108 {
                        visibility[idx] += count as f32;
                    }
                }
            }
        }
        
        // 统计弃牌历史
        for discard_record in &self.inner.discard_history {
            if let Some(idx) = ActionMask::tile_to_index(discard_record.tile) {
                if idx < 108 {
                    visibility[idx] += 1.0;
                }
            }
        }
        
        visibility
    }

    /// 转换为字符串（用于调试）
    fn __repr__(&self) -> String {
        format!("PyGameState(turn={}, current_player={}, out_count={})", 
                self.inner.turn, self.inner.current_player, self.inner.out_count)
    }
}

// 单独的 impl 块用于内部访问方法（不在 #[pymethods] 中）
impl PyGameState {
    /// 获取内部 GameState（用于内部访问）
    pub(crate) fn inner(&self) -> &GameState {
        &self.inner
    }

    /// 获取可变内部 GameState（用于内部访问）
    pub(crate) fn inner_mut(&mut self) -> &mut GameState {
        &mut self.inner
    }
}

