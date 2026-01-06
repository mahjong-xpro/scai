/// Python 绑定模块
/// 
/// 提供 PyO3 接口，将 Rust 游戏引擎暴露给 Python

// 允许 PyO3 宏生成的 non-local impl 定义（这是 PyO3 的正常行为）
#![allow(non_local_definitions)]

#[cfg(feature = "python")]
pub mod game_state;
#[cfg(feature = "python")]
pub mod action_mask;
#[cfg(feature = "python")]
pub mod tensor;
#[cfg(feature = "python")]
pub mod game_engine;

#[cfg(feature = "python")]
use pyo3::prelude::*;

/// Python 模块初始化
#[cfg(feature = "python")]
#[pymodule]
fn scai_engine(_py: Python, m: &PyModule) -> PyResult<()> {
    use game_state::PyGameState;
    use action_mask::PyActionMask;
    use game_engine::PyGameEngine;
    
    m.add_class::<PyGameState>()?;
    m.add_class::<PyActionMask>()?;
    m.add_class::<PyGameEngine>()?;
    m.add_function(pyo3::wrap_pyfunction!(tensor::state_to_tensor, m)?)?;
    m.add_function(pyo3::wrap_pyfunction!(tensor::action_mask_to_array, m)?)?;
    Ok(())
}

