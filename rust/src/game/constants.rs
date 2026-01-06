/// 游戏常量定义
/// 
/// 集中管理所有魔法数字，提高代码可维护性

/// 最大回合数限制（防止无限循环）
pub const MAX_TURNS: u32 = 200;

/// 玩家数量
pub const NUM_PLAYERS: u8 = 4;

/// 总牌数（108 张：万、筒、条各 36 张）
pub const TOTAL_TILES: usize = 108;

/// 牌的种类数（27 种：3 种花色 × 9 种牌）
pub const NUM_TILE_TYPES: usize = 27;

/// 每种花色的牌数（36 张：1-9 各 4 张）
pub const TILES_PER_SUIT: usize = 36;

/// 每种牌的数量（4 张）
pub const COPIES_PER_TILE: u8 = 4;

/// 特征平面数量
pub const NUM_FEATURE_PLANES: usize = 64;

/// 每个玩家的特征维度（4 个玩家）
pub const NUM_PLAYERS_FEATURE: usize = 4;

/// 每种花色的牌数（9 种：1-9）
pub const RANKS_PER_SUIT: usize = 9;

