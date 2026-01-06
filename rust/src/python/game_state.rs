use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use crate::game::state::GameState;
use crate::game::constants::NUM_PLAYERS;
use crate::tile::Tile;

/// Python 绑定的游戏状态
#[allow(non_local_definitions)] // PyO3 宏生成的 impl 定义
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
        if player_id >= NUM_PLAYERS {
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

    /// 设置玩家手牌
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 玩家 ID (0-3)
    /// - `hand_dict`: Python 字典，键为牌字符串（如 "Wan(1)"），值为数量
    /// 
    /// # 返回
    /// 
    /// 是否成功设置
    fn set_player_hand(&mut self, player_id: u8, hand_dict: &PyDict) -> PyResult<bool> {
        if player_id >= NUM_PLAYERS {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        // 先解析所有牌，避免借用冲突
        let mut tiles_to_add: Vec<(Tile, u8)> = Vec::new();
        for (tile_str, count_obj) in hand_dict.iter() {
            let tile_str: String = tile_str.extract()?;
            let count: u8 = count_obj.extract()?;
            
            // 解析牌字符串（格式：如 "Wan(1)", "Tong(5)", "Tiao(9)"）
            let tile = parse_tile_string(&tile_str)?;
            tiles_to_add.push((tile, count));
        }
        
        // 现在可以安全地借用 player
        let player = &mut self.inner.players[player_id as usize];
        
        // 清空当前手牌
        player.hand.clear();
        
        // 添加所有牌
        for (tile, count) in tiles_to_add {
            for _ in 0..count {
                if !player.hand.add_tile(tile) {
                    // 如果添加失败（超过4张），返回错误
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Cannot add more than 4 tiles of type: {:?}", tile)
                    ));
                }
            }
        }
        
        // 更新听牌状态
        player.check_ready();
        
        Ok(true)
    }

    /// 获取玩家定缺花色
    fn get_player_declared_suit(&self, player_id: u8) -> PyResult<Option<String>> {
        if player_id >= NUM_PLAYERS {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        let player = &self.inner.players[player_id as usize];
        Ok(player.declared_suit.map(|s| format!("{:?}", s)))
    }

    /// 设置玩家定缺花色
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 玩家 ID (0-3)
    /// - `suit`: 定缺花色字符串 ("Wan", "Tong", "Tiao")
    /// 
    /// # 返回
    /// 
    /// 是否成功设置
    fn set_player_declared_suit(&mut self, player_id: u8, suit: &str) -> PyResult<bool> {
        if player_id >= NUM_PLAYERS {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        use crate::tile::Suit;
        use crate::game::blood_battle::BloodBattleRules;
        
        let suit_enum = match suit {
            "Wan" => Suit::Wan,
            "Tong" => Suit::Tong,
            "Tiao" => Suit::Tiao,
            _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid suit: {}. Must be 'Wan', 'Tong', or 'Tiao'", suit)
            )),
        };
        
        Ok(BloodBattleRules::declare_suit(player_id, suit_enum, &mut self.inner))
    }

    /// 检查玩家是否已离场
    fn is_player_out(&self, player_id: u8) -> PyResult<bool> {
        if player_id >= NUM_PLAYERS {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        Ok(self.inner.players[player_id as usize].is_out)
    }

    /// 检查玩家是否听牌
    fn is_player_ready(&self, player_id: u8) -> PyResult<bool> {
        if player_id >= NUM_PLAYERS {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        Ok(self.inner.players[player_id as usize].is_ready)
    }

    /// 获取玩家的向听数
    /// 
    /// 向听数（Shanten Number）：表示当前手牌距离听牌还需要多少步
    /// - 0: 已听牌
    /// - 1: 一向听（差1张牌听牌）
    /// - 2: 二向听（差2张牌听牌）
    /// - 3+: 三向听及以上
    fn get_player_shanten(&self, player_id: u8) -> PyResult<u8> {
        if player_id >= NUM_PLAYERS {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        use crate::game::shanten::ShantenCalculator;
        let player = &self.inner.players[player_id as usize];
        let shanten = ShantenCalculator::calculate_shanten(&player.hand, &player.melds);
        Ok(shanten)
    }

    /// 获取玩家已碰/杠的牌组
    fn get_player_melds(&self, player_id: u8, py: Python) -> PyResult<PyObject> {
        if player_id >= NUM_PLAYERS {
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
    /// - `use_oracle`: 是否使用 Oracle 特征（上帝视角，仅训练时使用，默认 false）
    /// - `wall_tile_distribution`: 牌堆余牌分布（可选，108 个浮点数，每张牌的剩余数量 0-4）
    /// - `py`: Python 解释器
    /// 
    /// # 返回
    /// 
    /// 扁平化的 Vec<f32>，包含：
    /// 1. 4D tensor 扁平化（64 × 4 × 9 = 2304 个浮点数）
    /// 2. 牌池可见性特征（108 个浮点数，每张牌的出现次数 0-4）
    /// 
    /// 总计：2304 + 108 = 2412 个浮点数
    /// 
    /// # Oracle 特征
    /// 
    /// 当 `use_oracle=true` 时，特征编码会包含：
    /// - 对手的暗牌（手牌）- Plane 13-24
    /// - 牌堆余牌分布 - Plane 46-55
    /// 
    /// 这些特征仅在训练时使用，推理时应该设置为 `false`。
    fn to_tensor(
        &self,
        player_id: u8,
        remaining_tiles: Option<usize>,
        use_oracle: Option<bool>,
        wall_tile_distribution: Option<Vec<f32>>,
        py: Python,
    ) -> PyResult<Vec<f32>> {
        use crate::python::tensor::state_to_tensor;
        
        if player_id >= NUM_PLAYERS {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid player ID",
            ));
        }
        
        // 1. 获取 4D tensor
        let tensor_4d = state_to_tensor(self, player_id, remaining_tiles, use_oracle, wall_tile_distribution, py)?;
        
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

    /// 克隆游戏状态（深拷贝）
    /// 
    /// 用于 ISMCTS 等需要创建状态副本的场景
    fn clone(&self) -> Self {
        Self {
            inner: self.inner.clone(),
        }
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
    #[allow(dead_code)]
    pub(crate) fn inner_mut(&mut self) -> &mut GameState {
        &mut self.inner
    }
}

/// 解析牌字符串（辅助函数，不暴露给 Python）
/// 
/// 解析格式：如 "Wan(1)", "Tong(5)", "Tiao(9)"
pub(crate) fn parse_tile_string(tile_str: &str) -> PyResult<crate::tile::Tile> {
    // 尝试解析 "Wan(1)" 格式
    if let Some(open_paren) = tile_str.find('(') {
        let suit_str = &tile_str[..open_paren];
        let rank_str = &tile_str[open_paren + 1..tile_str.len() - 1];
        
        let rank: u8 = rank_str.parse()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid rank in tile string: {}", tile_str)
            ))?;
        
        if rank < 1 || rank > 9 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Rank must be between 1 and 9, got: {}", rank)
            ));
        }
        
        match suit_str {
            "Wan" => Ok(crate::tile::Tile::Wan(rank)),
            "Tong" => Ok(crate::tile::Tile::Tong(rank)),
            "Tiao" => Ok(crate::tile::Tile::Tiao(rank)),
            _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid suit in tile string: {}", tile_str)
            )),
        }
    } else {
        // 尝试解析其他格式（如 "1Wan"）
        // 这里简化处理，只支持 "Wan(1)" 格式
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unsupported tile string format: {}. Expected format: 'Wan(1)'", tile_str)
        ))
    }
}

