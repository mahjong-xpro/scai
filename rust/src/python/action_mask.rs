use pyo3::prelude::*;
use pyo3::types::PyList;
use crate::engine::action_mask::ActionMask;

/// Python 绑定的动作掩码
#[pyclass]
pub struct PyActionMask {
    inner: ActionMask,
}

#[pymethods]
impl PyActionMask {
    /// 创建新的动作掩码
    #[new]
    pub fn new() -> Self {
        Self {
            inner: ActionMask::new(),
        }
    }

    /// 生成动作掩码
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 玩家 ID (0-3)
    /// - `state`: 游戏状态
    /// - `discarded_tile`: 别人打出的牌（可选，如果是响应别人的出牌）
    /// 
    /// # 返回
    /// 
    /// 新的 PyActionMask 实例
    #[staticmethod]
    pub fn generate(
        player_id: u8,
        state: &crate::python::game_state::PyGameState,
        discarded_tile: Option<u8>,  // 使用索引而不是 Tile 对象
    ) -> PyResult<Self> {
        let tile = discarded_tile.and_then(|idx| ActionMask::index_to_tile(idx as usize));
        
        let mask = ActionMask::generate(player_id, state.inner(), tile);
        Ok(Self { inner: mask })
    }

    /// 生成动作掩码（自己的回合）
    #[staticmethod]
    pub fn generate_own_turn(
        player_id: u8,
        state: &crate::python::game_state::PyGameState,
    ) -> PyResult<Self> {
        let mask = ActionMask::generate(player_id, state.inner(), None);
        Ok(Self { inner: mask })
    }

    /// 转换为布尔数组（434 个动作）
    /// 
    /// # 参数
    /// 
    /// - `is_own_turn`: 是否是自己回合
    /// - `discarded_tile`: 别人打出的牌（可选，如果是响应别人的出牌）
    /// 
    /// # 返回
    /// 
    /// Python 列表，包含 434 个布尔值
    pub fn to_bool_array(
        &self,
        is_own_turn: bool,
        discarded_tile: Option<u8>,  // 使用索引
        py: Python,
    ) -> PyResult<PyObject> {
        let tile = discarded_tile.and_then(|idx| ActionMask::index_to_tile(idx as usize));
        let bool_mask = self.inner.to_bool_array(is_own_turn, tile);
        
        // 转换为 Python 列表
        let list = PyList::empty(py);
        for &val in bool_mask.iter() {
            list.append(val)?;
        }
        
        Ok(list.into())
    }

    /// 验证动作是否合法
    /// 
    /// # 参数
    /// 
    /// - `action_index`: 动作索引（0-433）
    /// - `player_id`: 玩家 ID
    /// - `state`: 游戏状态
    /// - `is_own_turn`: 是否是自己回合
    /// - `discarded_tile`: 别人打出的牌（可选）
    /// 
    /// # 返回
    /// 
    /// `True` 表示动作合法，`False` 表示非法
    #[staticmethod]
    pub fn validate_action(
        action_index: usize,
        player_id: u8,
        state: &crate::python::game_state::PyGameState,
        is_own_turn: bool,
        discarded_tile: Option<u8>,
    ) -> PyResult<bool> {
        let tile = discarded_tile.and_then(|idx| ActionMask::index_to_tile(idx as usize));
        Ok(ActionMask::validate_action(
            action_index,
            player_id,
            state.inner(),
            is_own_turn,
            tile,
        ))
    }

    /// 将牌索引转换为牌对象（用于调试）
    #[staticmethod]
    pub fn index_to_tile(index: usize) -> PyResult<String> {
        ActionMask::index_to_tile(index)
            .map(|tile| format!("{:?}", tile))
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid tile index"))
    }

    /// 将牌对象转换为索引
    #[staticmethod]
    pub fn tile_to_index(suit: u8, rank: u8) -> PyResult<usize> {
        use crate::tile::{Tile, Suit};
        
        let suit_enum = match suit {
            0 => Suit::Wan,
            1 => Suit::Tong,
            2 => Suit::Tiao,
            _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid suit")),
        };
        
        let tile = Tile::new(suit_enum, rank)
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid rank"))?;
        
        ActionMask::tile_to_index(tile)
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Failed to convert tile to index"))
    }

    /// 获取动作掩码（用于 AI 训练）
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 玩家 ID
    /// - `state`: 游戏状态
    /// - `is_own_turn`: 是否是自己回合
    /// - `discarded_tile`: 别人打出的牌（可选，使用索引 0-107）
    /// 
    /// # 返回
    /// 
    /// Vec<f32>，长度为 434，每个元素为 0.0 或 1.0
    #[staticmethod]
    pub fn get_action_mask(
        player_id: u8,
        state: &crate::python::game_state::PyGameState,
        is_own_turn: bool,
        discarded_tile: Option<u8>,
    ) -> PyResult<Vec<f32>> {
        let tile = discarded_tile.and_then(|idx| ActionMask::index_to_tile(idx as usize));
        let mask = ActionMask::generate(player_id, state.inner(), tile);
        let bool_mask = mask.to_bool_array(is_own_turn, tile);
        
        // 转换为 Vec<f32>（bool → f32：true → 1.0，false → 0.0）
        let result: Vec<f32> = bool_mask.iter().map(|&b| if b { 1.0 } else { 0.0 }).collect();
        
        Ok(result)
    }

    /// 转换为字符串（用于调试）
    fn __repr__(&self) -> String {
        format!("PyActionMask(can_win={}, can_pong={}, can_gang={}, can_discard={})",
                self.inner.can_win.len(),
                self.inner.can_pong.len(),
                self.inner.can_gang.len(),
                self.inner.can_discard.len())
    }
}

// 单独的 impl 块用于内部访问方法（不在 #[pymethods] 中）
impl PyActionMask {
    /// 获取内部 ActionMask（用于内部访问）
    pub(crate) fn inner(&self) -> &ActionMask {
        &self.inner
    }
}

