/// 血战到底 AI 引擎
/// 
/// 高性能 Rust 实现，用于强化学习训练

pub mod tile;
pub mod utils;
pub mod game;
pub mod engine;

// 重新导出常用类型
pub use tile::{Tile, Suit, Wall, Hand};
pub use utils::{SuitMask, HandMask};
pub use game::scoring::{Meld, RootCounter, BaseFansCalculator, ActionFlags, Settlement};
pub use game::state::{GameState, GangRecord, PassedWin};
pub use game::action::Action;
pub use game::player::Player;
pub use game::settlement::{SettlementResult, GangSettlement, FinalSettlement};
pub use game::blood_battle::BloodBattleRules;
pub use game::kong::{KongHandler, KongType};
pub use game::pong::PongHandler;
pub use game::ready::ReadyChecker;
pub use engine::action_mask::ActionMask;
pub use game::game_engine::{GameEngine, GameError, GameResult, FinalSettlementResult};
pub use game::action_callback::{ActionCallback, FnActionCallback};

// Python 绑定模块
#[cfg(feature = "python")]
pub mod python;

