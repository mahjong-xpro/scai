use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use crate::game::game_engine::GameEngine;
use crate::game::action::Action;
use crate::python::game_state::PyGameState;

/// Python 绑定的游戏引擎
#[pyclass]
pub struct PyGameEngine {
    inner: GameEngine,
}

#[pymethods]
impl PyGameEngine {
    /// 创建新的游戏引擎
    #[new]
    pub fn new() -> PyResult<Self> {
        Ok(Self {
            inner: GameEngine::new(),
        })
    }

    /// 初始化游戏（发牌）
    pub fn initialize(&mut self) -> PyResult<()> {
        self.inner.initialize()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Game initialization failed: {:?}", e)
            ))
    }

    /// 处理动作
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 玩家 ID (0-3)
    /// - `action_type`: 动作类型字符串 ("draw", "discard", "pong", "gang", "win", "pass")
    /// - `tile_index`: 牌索引（可选，用于 discard/pong/gang）
    /// - `is_concealed`: 是否暗杠（仅用于 gang）
    /// 
    /// # 返回
    /// 
    /// 动作结果字典
    pub fn process_action(
        &mut self,
        player_id: u8,
        action_type: &str,
        tile_index: Option<usize>,
        is_concealed: Option<bool>,
        py: Python,
    ) -> PyResult<PyObject> {
        use crate::engine::action_mask::ActionMask;
        
        let action = match action_type {
            "draw" => Action::Draw,
            "discard" => {
                let idx = tile_index.ok_or_else(|| 
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("tile_index required for discard")
                )?;
                let tile = ActionMask::index_to_tile(idx)
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid tile index"))?;
                Action::Discard { tile }
            },
            "pong" => {
                let idx = tile_index.ok_or_else(|| 
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("tile_index required for pong")
                )?;
                let tile = ActionMask::index_to_tile(idx)
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid tile index"))?;
                Action::Pong { tile }
            },
            "gang" => {
                let idx = tile_index.ok_or_else(|| 
                    PyErr::new::<pyo3::exceptions::PyValueError, _>("tile_index required for gang")
                )?;
                let tile = ActionMask::index_to_tile(idx)
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid tile index"))?;
                let is_concealed = is_concealed.unwrap_or(false);
                Action::Gang { tile, is_concealed }
            },
            "win" => Action::Win,
            "pass" => Action::Pass,
            _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Unknown action type: {}", action_type)
            )),
        };
        
        match self.inner.process_action(player_id, action) {
            Ok(result) => {
                // 将结果转换为 Python 字典
                let dict = PyDict::new(py);
                match result {
                    crate::game::game_engine::ActionResult::Drawn { tile } => {
                        dict.set_item("type", "drawn")?;
                        dict.set_item("tile", format!("{:?}", tile))?;
                    },
                    crate::game::game_engine::ActionResult::Discarded { tile, responses } => {
                        dict.set_item("type", "discarded")?;
                        dict.set_item("tile", format!("{:?}", tile))?;
                        let responses_list = PyList::empty(py);
                        for (pid, resp) in responses {
                            let resp_dict = PyDict::new(py);
                            resp_dict.set_item("player_id", pid)?;
                            resp_dict.set_item("response", format!("{:?}", resp))?;
                            responses_list.append(resp_dict)?;
                        }
                        dict.set_item("responses", responses_list)?;
                    },
                    crate::game::game_engine::ActionResult::Ponged { tile } => {
                        dict.set_item("type", "ponged")?;
                        dict.set_item("tile", format!("{:?}", tile))?;
                    },
                    crate::game::game_engine::ActionResult::Ganged { tile, kong_type, settlement } => {
                        dict.set_item("type", "ganged")?;
                        dict.set_item("tile", format!("{:?}", tile))?;
                        dict.set_item("kong_type", format!("{:?}", kong_type))?;
                        dict.set_item("settlement", format!("{:?}", settlement))?;
                    },
                    crate::game::game_engine::ActionResult::Won { player_id, win_result, settlement, can_continue, discarder_id, gang_pao_refund } => {
                        dict.set_item("type", "won")?;
                        dict.set_item("player_id", player_id)?;
                        dict.set_item("win_result", format!("{:?}", win_result))?;
                        dict.set_item("settlement", format!("{:?}", settlement))?;
                        dict.set_item("can_continue", can_continue)?;
                        if let Some(discarder) = discarder_id {
                            dict.set_item("discarder_id", discarder)?;
                        }
                        if let Some(ref refund) = gang_pao_refund {
                            dict.set_item("gang_pao_refund", format!("{:?}", refund))?;
                        }
                    },
                    crate::game::game_engine::ActionResult::Passed => {
                        dict.set_item("type", "passed")?;
                    },
                }
                Ok(dict.into())
            },
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Action failed: {:?}", e)
            )),
        }
    }

    /// 获取游戏状态
    #[getter]
    fn state(&self) -> PyGameState {
        // 使用 GameEngine 的 state 字段（public）
        PyGameState {
            inner: self.inner.state.clone(),
        }
    }

    /// 获取剩余牌数
    pub fn remaining_tiles(&self) -> usize {
        self.inner.wall.remaining_count()
    }

    /// 检查游戏是否结束
    pub fn is_game_over(&self) -> bool {
        self.inner.state.is_game_over()
    }

    /// 定缺（三花色必缺一）
    /// 
    /// # 参数
    /// 
    /// - `player_id`: 玩家 ID (0-3)
    /// - `suit`: 定缺花色字符串 ("Wan", "Tong", "Tiao")
    /// 
    /// # 返回
    /// 
    /// 是否成功定缺
    pub fn declare_suit(&mut self, player_id: u8, suit: &str) -> PyResult<bool> {
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
        
        Ok(BloodBattleRules::declare_suit(player_id, suit_enum, &mut self.inner.state))
    }

    /// 转换为字符串（用于调试）
    fn __repr__(&self) -> String {
        format!("PyGameEngine(turn={}, current_player={})",
                self.inner.state.turn, self.inner.state.current_player)
    }
}

