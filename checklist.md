# 血战到底 AI 开发 Checklist

这份 Checklist 是专为从零开始、Rust 驱动、强化学习自对弈的血战到底 AI 项目设计的。它按开发优先级排列，确保你从底层架构稳步推进到顶级算法实现。

---

## 🛠 第一阶段：Rust 核心引擎 (High-Performance Environment)

这是整个项目的地基，性能直接决定训练上限。

### 1.1 牌组数据结构设计

- [x] **基础数据结构**：
  - [x] 使用 `u8` 或位掩码（Bitmask）存储牌
  - [x] 定义 `Tile` 枚举（万、筒、条），实现 `Copy`、`Clone`、`PartialEq`、`Eq`、`Hash` trait
  - [x] 实现 `Tile` 到 `u8` 的快速转换（0-107 映射）
  - [x] 实现牌墙（Wall）数据结构：
    - [x] 使用 `Vec<Tile>` 或位数组存储 108 张牌
    - [x] 实现 `draw()` 方法：O(1) 时间复杂度的抽取
    - [x] 实现 `remaining_count()` 方法：快速查询剩余牌数
    - [x] 实现 `shuffle()` 方法：高效的洗牌算法
  - [x] 实现手牌（Hand）数据结构：
    - [x] 使用 `[u8; 108]` 数组或 `HashMap<Tile, u8>` 存储每张牌的数量
    - [x] 实现 `add_tile(tile: Tile)`：O(1) 添加
    - [x] 实现 `remove_tile(tile: Tile)`：O(1) 移除
    - [x] 实现 `has_tile(tile: Tile) -> bool`：O(1) 查询
    - [x] 实现 `tile_count(tile: Tile) -> u8`：查询特定牌的数量
    - [x] 实现 `to_sorted_vec() -> Vec<Tile>`：用于显示和调试

- [x] **位运算优化**：
  - [x] 使用位掩码表示牌的组合：
    - [x] 顺子检测：使用位运算快速判断连续三张牌
    - [x] 刻子检测：使用位运算快速判断三张相同牌
    - [x] 对子检测：使用位运算快速判断两张相同牌
  - [x] 实现高效的牌型匹配算法：
    - [x] 使用递归回溯算法判定基本胡牌型
    - [x] 使用查表法（Lookup Table）优化常见牌型判定
    - [x] 实现牌型缓存机制，避免重复计算
  - [x] 优化内存布局：
    - [x] 使用 `#[repr(C)]` 确保结构体内存对齐
    - [x] 使用 `Box<[T]>` 替代 `Vec<T>` 减少堆分配
    - [x] 使用 `SmallVec` 优化小数组场景

- [x] **胡牌判定算法**：
  - [x] 实现平胡判定（基本胡牌型）：
    - [x] 递归回溯算法：找出 1 个对子 + 4 个顺子/刻子
  - [x] 实现七对判定：
    - [x] 快速检测：统计对子数量是否为 7
    - [x] 优化：使用位运算快速统计（match 模式匹配优化）
  - [x] 实现清一色判定：
    - [x] 检查所有牌是否属于同一花色
    - [x] 结合平胡或七对判定
  - [x] 实现其他特殊牌型判定：
    - [x] **基础番型**：
      - [x] 平胡（基本胡牌型：1个对子 + 4个顺子/刻子，番数：$2^0 = 1$）
      - [x] 七对（不经过碰杠，手牌由 7 个对子组成，番数：$2^2 = 4$）
      - [x] 对对胡（全部是刻子 + 1 个对子，番数：$2^1 = 2$）
      - [x] 清一色（全副牌只有一门花色，番数：$2^2 = 4$）
      - [x] 全带幺（所有顺子/刻子都包含1或9，番数：$2^2 = 4$）
      - [x] 金钩钓（经过碰杠后手牌仅剩 1 张牌，单钓胡牌，番数：$2^2 = 4$）
    - [x] **进阶加番（组合牌型）**：
      - [x] 清对（清一色 + 对对胡，番数：$2^{2+1} = 8$）
      - [x] 清七对（清一色 + 七对，番数：$2^{2+2} = 16$）
      - [x] 清金钩钓（清一色 + 金钩钓，番数：$2^{2+2} = 16$）
      - [x] 龙七对（七对 + 其中一对是四张，番数：七对(4) + 根数倍率）
        - [x] 双龙七对：2 组四张相同牌（16 番）
        - [x] 三龙七对：3 组四张相同牌（32 番）
      - [x] 清龙七对（清一色 + 龙七对，番数：$2^{2+3} = 32$）
  - [x] **番数计算系统**（文件：`rust/src/game/scoring.rs`）：
    - [x] **根（Gen）统计模块**：
      - [x] 在 `WinChecker` 或新建 `RootCounter` 中实现 `count_roots()` 方法
        - [x] 方法签名：`fn count_roots(hand: &Hand, melds: &[Meld]) -> u8`
        - [x] 统计手牌中 4 张相同牌的数量（遍历 `hand.tiles_map()`，查找 `count == 4`）
        - [x] 统计已开杠的牌（遍历 `melds`，查找 `Meld::Kong` 类型）
        - [x] 合并统计：手牌中的根 + 已开杠的根
        - [x] 返回根的总数量（u8，范围 0-4）
      - [x] 创建 `Meld` 枚举（表示碰/杠）：
        - [x] `Triplet { tile: Tile }` - 碰（刻子）
        - [x] `Kong { tile: Tile, is_concealed: bool }` - 杠（明杠/暗杠）
      - [x] 添加单元测试：
        - [x] 测试 0 个根的情况
        - [x] 测试 1 个根（手牌中 4 张相同牌）
        - [x] 测试 2 个根（手牌中 1 个 + 已开杠 1 个）
        - [x] 测试 3 个根的情况
        - [x] 测试边界情况（4 个根）
    - [x] **基础番数映射表**（文件：`rust/src/game/scoring.rs`）：
      - [x] 创建 `BaseFansCalculator` 结构体或模块级函数
      - [x] 实现 `base_fans(win_type: WinType) -> u32` 函数：
        - [x] 使用 `match` 表达式映射所有 `WinType` 到基础番数
        - [x] 番数映射规则（完整列表）：
          - [x] `Normal`：$2^0 = 1$ 番
          - [x] `AllTriplets`：$2^1 = 2$ 番
          - [x] `SevenPairs`：$2^2 = 4$ 番
          - [x] `PureSuit`：$2^2 = 4$ 番
          - [x] `AllTerminals`：$2^2 = 4$ 番
          - [x] `GoldenHook`：$2^2 = 4$ 番
          - [x] `PureAllTriplets`：$2^{2+1} = 8$ 番
          - [x] `PureSevenPairs`：$2^{2+2} = 16$ 番
          - [x] `PureGoldenHook`：$2^{2+2} = 16$ 番
          - [x] `DragonSevenPairs`：特殊处理，需要根数参数
          - [x] `PureDragonSevenPairs`：$2^{2+3} = 32$ 番（固定值）
      - [x] 实现 `dragon_seven_pairs_fans(roots: u8) -> u32` 函数：
        - [x] 双龙七对（2 根）：七对(4) × $2^2$ = 16 番
        - [x] 三龙七对（3 根）：七对(4) × $2^3$ = 32 番
      - [x] 添加单元测试：
        - [x] 测试所有 `WinType` 的基础番数（使用 `#[test]` 宏）
        - [x] 测试龙七对的动态计算（2 根、3 根）
        - [x] 测试边界情况（0 根、4 根）
    - [x] **倍率计算器（Settlement）**（文件：`rust/src/game/scoring.rs`）：
      - [x] 创建 `Settlement` 结构体：
        - [x] 字段定义：`#[derive(Debug, Clone, PartialEq, Eq)]`
        - [x] `base_pattern: u32` - 基础番
        - [x] `roots: u8` - 根的数量（0-4）
        - [x] `action_bonus: u8` - 动作加成数量（0-5，最多 5 个动作）
        - [x] 使用 `ActionFlags` 结构体记录动作触发状态：
          - [x] `is_zi_mo: bool` - 是否自摸
          - [x] `is_gang_kai: bool` - 是否杠上开花
          - [x] `is_gang_pao: bool` - 是否杠上炮
          - [x] `is_qiang_gang: bool` - 是否抢杠胡
          - [x] `is_hai_di: bool` - 是否海底捞月
      - [x] 实现 `new()` 构造函数：
        - [x] 参数：`base_pattern, roots, action_bonus`
        - [x] 验证参数有效性（roots <= 4, action_bonus <= 5）
      - [x] 实现 `total_fans(&self) -> Option<u32>` 方法：
        - [x] 根数倍率：`base * 2_u32.pow(roots as u32)`
        - [x] 动作加成倍率：`result * 2_u32.pow(action_bonus as u32)`
        - [x] 完整公式：`base_pattern × 2^roots × 2^action_bonus`
        - [x] 处理溢出：使用 `checked_mul()` 和 `checked_pow()`
      - [x] 实现 `calculate(win_result: &WinResult, roots: u8, actions: &ActionFlags) -> Settlement` 静态方法：
        - [x] 从 `WinResult` 获取基础番数（调用 `base_fans()`）
        - [x] 从 `ActionFlags` 统计动作加成数量
        - [x] 处理龙七对的特殊情况（基础番数已包含根数倍率）
        - [x] 创建并返回 `Settlement` 实例
      - [x] 创建 `ActionFlags` 结构体（记录动作触发状态）：
        - [x] `is_zi_mo: bool`
        - [x] `is_gang_kai: bool`
        - [x] `is_gang_pao: bool`
        - [x] `is_qiang_gang: bool`
        - [x] `is_hai_di: bool`
        - [x] 实现 `count(&self) -> u8` 方法：统计动作数量
      - [x] 添加单元测试：
        - [x] 测试基础番数计算（无根、无动作）
        - [x] 测试根数倍率（1 根、2 根、3 根）
        - [x] 测试动作加成（单个动作、多个动作）
        - [x] 测试组合情况（基础番 + 根 + 动作）
        - [x] 测试边界情况（最大番数、溢出处理）
    - [x] **番数计算集成**：
      - [x] 在 `WinResult` 中添加 `calculate_fans()` 方法（可选）：
        - [x] 方法签名：`fn calculate_fans(&self, roots: u8, actions: &ActionFlags) -> Option<u32>`
        - [x] 调用 `Settlement::calculate()` 并返回 `total_fans()`
      - [x] 在 `game/state.rs` 中集成根数统计：
        - [x] 在 `GameState` 中添加 `melds: [Vec<Meld>; 4]` 字段（4 个玩家）
        - [x] 在胡牌判定时调用 `count_roots(hand, &state.melds[player_id])`
      - [x] 在 `game/state.rs` 中集成动作触发番：
        - [x] 在 `GameState` 中添加 `action_flags: ActionFlags` 字段
        - [x] 在 `GameState` 中添加 `last_action: Option<Action>` 字段
        - [x] 在 `GameState` 中添加 `is_last_tile: bool` 字段
        - [x] 在 `GameState` 中添加 `gang_history: Vec<GangRecord>` 字段
        - [x] 实现动作判定方法：`check_zi_mo()`, `check_gang_kai()`, `check_gang_pao()`, `check_qiang_gang()`, `check_hai_di()`
      - [x] 添加集成测试（文件：`rust/tests/scoring_test.rs`）：
        - [x] 测试完整流程：胡牌判定 → 根数统计 → 番数计算
        - [x] 测试各种组合：不同牌型 + 不同根数 + 不同动作
        - [x] 测试示例计算（参考胡牌规则.md 第 8 章）
  - [x] **动作触发番**（实时状态加成，文件：`rust/src/game/state.rs`）：
    - [x] **游戏状态记录**：
      - [x] 在 `GameState` 中添加动作触发状态字段：
        - [x] `last_action: Option<Action>` - 上一个动作
        - [x] `is_last_tile: bool` - 是否最后一张牌
        - [x] `gang_history: Vec<GangRecord>` - 杠牌历史记录
      - [x] 创建 `GangRecord` 结构体：
        - [x] `player_id: u8` - 杠牌玩家
        - [x] `tile: Tile` - 杠的牌
        - [x] `is_concealed: bool` - 是否暗杠
        - [x] `turn: u32` - 杠牌回合数
    - [x] **自摸判定**：
      - [x] 实现 `check_zi_mo()` 方法：判断 `last_action == Action::Draw`
      - [x] 设置 `action_flags.is_zi_mo = true`
      - [x] 添加单元测试：测试自摸判定逻辑（在 `GameState` 测试中）
    - [x] **杠上开花判定**：
      - [x] 实现 `check_gang_kai(is_winning: bool)` 方法
      - [x] 检查：上一个动作是 `Action::Gang`，且当前要胡牌
      - [x] 设置 `action_flags.is_gang_kai = true`
      - [x] 添加单元测试：测试杠上开花判定
    - [x] **杠上炮判定**：
      - [x] 实现 `check_gang_pao(discarded_tile: &Tile, is_winning: bool)` 方法
      - [x] 检查：上一个动作是 `Action::Gang`，且打出的牌被别人胡
      - [x] 设置 `action_flags.is_gang_pao = true`
      - [x] 记录点炮者信息（用于结算，在 `GameState` 中）
    - [x] **抢杠胡判定**：
      - [x] 实现 `check_qiang_gang(gang_tile: &Tile, is_winning: bool)` 方法
      - [x] 检查：其他玩家在"弯杠"（补杠）时，你胡他那张牌
      - [x] 设置 `action_flags.is_qiang_gang = true`
    - [x] **海底捞月判定**：
      - [x] 实现 `check_hai_di()` 方法
      - [x] 检查：`is_last_tile == true` 且当前动作是 `Action::Win`
      - [x] 设置 `action_flags.is_hai_di = true`
  - [x] **核心准则检查**（Action Masking，文件：`rust/src/engine/action_mask.rs`）：
    - [x] **缺一门检查**：
      - [x] 创建 `check_missing_suit()` 函数（在 `game/rules.rs` 中）：
        - [x] 参数：`hand: &Hand, declared_suit: Option<Suit>`
        - [x] 检查手牌中是否还有定缺门的牌
        - [x] 返回：`bool`（true 表示可以胡牌，false 表示不能胡）
      - [x] 在 `ActionMask::can_win()` 中调用此函数
      - [x] 添加单元测试：测试缺一门检查逻辑
    - [x] **过胡限制**：
      - [x] 在 `GameState` 中添加 `passed_wins: [Vec<PassedWin>; 4]` 字段（4 个玩家）：
        - [x] `tile: Tile` - 放弃的牌
        - [x] `fans: u32` - 放弃时的番数
        - [x] `turn: u32` - 放弃的回合数
      - [x] 创建 `PassedWin` 结构体记录放弃的胡牌（在 `game/state.rs` 中）
      - [x] 实现 `can_win_after_pass()` 函数（在 `game/rules.rs` 中）：
        - [x] 检查：当前要胡的牌是否在 `passed_wins` 中
        - [x] 检查：当前番数是否 <= 放弃时的番数
        - [x] 返回：`bool`（true 表示可以胡，false 表示不能胡）
      - [x] 在 `ActionMask::can_win()` 中调用此函数
      - [x] 添加单元测试：测试过胡限制逻辑
    - [x] **不能吃牌**：
      - [x] 在 `ActionMask::can_chi()` 中直接返回 `false`
      - [x] 在 `Action` 枚举中不包含 `Chi` 变体（四川麻将禁止吃牌）
      - [x] 在游戏规则中明确禁止吃牌（通过 `can_chi()` 方法）
      - [x] 添加单元测试：验证吃牌动作被禁止
  - [x] **性能要求**（文件：`rust/benches/`）：
    - [x] **性能基准测试**：
      - [x] 创建 `win_check_bench.rs`：
        - [x] 使用 `criterion` crate 进行基准测试
        - [x] 测试 `check_win()` 方法的性能
        - [x] 测试不同牌型的判定时间（平胡、七对）
        - [x] 目标：所有胡牌判定 < 10μs（待验证）
      - [x] 创建 `scoring_bench.rs`：
        - [x] 测试 `Settlement::total_fans()` 的性能
        - [x] 测试 `count_roots()` 的性能
        - [x] 测试 `BaseFansCalculator::base_fans()` 的性能
        - [x] 测试 `Settlement::calculate()` 的性能
        - [x] 目标：番数计算 < 1μs（待验证）
      - [x] 创建 `action_mask_bench.rs`：
        - [x] 测试 `ActionMask::can_win()` 的性能
        - [x] 目标：动作掩码生成 < 5μs（待验证）
    - [x] **性能优化**：
      - [x] 使用 `cargo bench` 运行基准测试：
        - [x] 创建基准测试脚本（`scripts/benchmark.sh`）
        - [x] 配置基准测试文件（`benches/*.rs`）
      - [x] 识别热点路径（Hot Path）：
        - [x] 文档化性能分析工具使用方法（`PERFORMANCE.md`）
        - [x] 记录最耗时的函数调用（待实际运行基准测试后补充）
      - [x] 优化策略：
        - [x] 减少不必要的内存分配（优化缓存策略）
        - [x] 使用 `#[inline]` 标记热点函数：
          - [x] `WinChecker::check_win()`
          - [x] `WinChecker::check_seven_pairs()`
          - [x] `WinChecker::hand_hash()`
          - [x] `WinChecker::is_pure_suit()`
          - [x] `BaseFansCalculator::base_fans()`
          - [x] `RootCounter::count_roots()`
          - [x] `ActionFlags::count()`
          - [x] `Settlement::total_fans()`
        - [x] 优化缓存策略（`result_cache`）：
          - [x] 限制缓存大小（默认 1000 个条目）
          - [x] 实现简单的 LRU 策略（缓存满时清空）
          - [x] 添加 `with_cache_size()` 方法支持自定义缓存大小
        - [x] 使用 `SmallVec` 优化小数组（已实现）
      - [x] 性能回归测试：
        - [x] 创建性能回归测试脚本（`scripts/performance_check.sh`）
        - [x] 在 CI/CD 中集成性能测试（`.github/workflows/performance.yml`）
        - [x] 创建性能文档（`PERFORMANCE.md`）
        - [ ] 设置性能阈值，防止性能退化（待实际运行基准测试后设置）

- [x] **数据结构验证**：
  - [x] 单元测试覆盖所有牌型判定：
    - [x] 测试所有基本胡牌型（14 张牌的各种组合）：
      - [x] 基本胡牌型（1 个对子 + 4 个顺子）
      - [x] 基本胡牌型（1 个对子 + 4 个刻子）
      - [x] 基本胡牌型（混合：顺子 + 刻子）
      - [x] 七对的各种组合
      - [x] 对对胡的各种组合
    - [x] 测试边界情况（空手牌、满手牌等）：
      - [x] 空手牌
      - [x] 单张牌
      - [x] 13 张牌（不完整）
      - [x] 15 张牌（超出）
      - [x] 14 张相同牌（无效组合）
      - [x] 无效组合
    - [x] 测试非法输入的处理：
      - [x] 随机无效组合
      - [x] 部分有效 + 部分无效组合
  - [x] 集成测试（文件：`rust/tests/integration_test.rs`）：
    - [x] 测试完整的牌局流程（发牌、出牌、胡牌）：
      - [x] 创建牌墙并洗牌
      - [x] 发牌给 4 个玩家
      - [x] 模拟游戏流程（摸牌、出牌、胡牌）
      - [x] 验证游戏状态
    - [x] 测试多线程并发场景：
      - [x] 多线程并发胡牌判定（4 线程）
      - [x] 并发访问 WinChecker（8 线程）
      - [x] 使用 Arc 和 Mutex 保护共享状态
  - [x] 性能压力测试（文件：`rust/tests/performance_stress_test.rs`）：
    - [x] 单线程每秒处理 10,000+ 次胡牌判定：
      - [x] 实现性能测试函数
      - [x] 验证每秒处理次数 >= 10,000
      - [x] 使用 `#[ignore]` 标记，需要时使用 `cargo test -- --ignored`
    - [x] 多线程并发测试（4-8 线程）：
      - [x] 8 线程并发测试
      - [x] 使用原子计数器统计总迭代次数
      - [x] 验证多线程性能（允许 20% 性能损失）
    - [x] 内存使用监控（避免内存泄漏）：
      - [x] 测试缓存大小限制
      - [x] 验证缓存不会无限增长
      - [x] 长时间运行压力测试（5 秒）
      - [x] 添加 `cache_size()` 方法用于测试和监控

### 1.2 血战规则实现

- [x] **初始定缺**：三花色必缺一
  - [x] 实现 `Player::declare_suit()` 方法
  - [x] 实现 `BloodBattleRules::declare_suit()` 方法
  - [x] 实现 `BloodBattleRules::all_players_declared()` 检查
  - [x] 添加单元测试和集成测试
- [x] **刮风下雨**：即时杠钱结算逻辑
  - [x] 实现 `GangSettlement::calculate_gang_payment()` 方法
    - [x] 暗杠结算：每人给 2 分
    - [x] 明杠结算：每人给 1 分
  - [x] 实现 `GangSettlement::calculate_gang_pao_refund()` 方法（杠上炮退税）
  - [x] 在 `Player` 中添加 `gang_earnings` 字段记录杠钱收入
  - [x] 添加单元测试和集成测试
- [x] **玩家离场逻辑**：一家胡牌后，其余玩家继续，直至牌墙摸完或仅剩一人
  - [x] 在 `GameState` 中添加 `out_count` 字段
  - [x] 实现 `GameState::mark_player_out()` 方法
  - [x] 实现 `GameState::is_game_over()` 方法
  - [x] 实现 `GameState::next_active_player()` 方法
  - [x] 实现 `BloodBattleRules::handle_player_out()` 方法
  - [x] 实现 `BloodBattleRules::can_continue()` 方法
  - [x] 实现 `BloodBattleRules::get_active_players()` 方法
  - [x] 添加单元测试和集成测试
- [x] **局末结算**：
  - [x] 查大叫（未听牌赔付）：
    - [x] 实现 `FinalSettlement::check_not_ready()` 方法
    - [x] 未听牌玩家赔给听牌玩家（按听牌者最高番数）
    - [x] 添加单元测试
  - [x] 查花猪（未打完缺门赔付）：
    - [x] 实现 `Player::has_declared_suit_tiles()` 方法
    - [x] 实现 `FinalSettlement::check_flower_pig()` 方法
    - [x] 花猪赔给所有非花猪玩家（按最大番数）
    - [x] 添加单元测试
  - [x] 退税：
    - [x] 实现 `Player::refund_gang_earnings()` 方法
    - [x] 实现 `FinalSettlement::refund_gang_money()` 方法
    - [x] 杠牌者被查出花猪或未听牌时，退还杠钱
    - [x] 添加单元测试

### 1.3 合法动作掩码 (Action Masking)

- [x] 编写函数，根据定缺和当前状态返回 `[bool; N]` 向量
  - [x] 实现 `ActionMask::to_bool_array()` 方法（434 个动作）
  - [x] 动作空间：出牌(0-107) + 碰牌(108-215) + 杠牌(216-323) + 胡牌(324-431) + 摸牌(432) + 过(433)
  - [x] 实现 `ActionMask::tile_to_index()` 和 `index_to_tile()` 用于索引映射
- [x] 严禁 AI 执行非法操作
  - [x] 实现 `ActionMask::validate_action()` 严格验证动作合法性
  - [x] 检查缺一门、过胡限制、定缺门等规则
  - [x] 区分自己回合和响应回合的动作限制
  - [x] 添加单元测试验证非法操作被禁止

### 1.4 PyO3 接口绑定

- [x] 实现 Python 调用的包装器
  - [x] 实现 `PyGameState` - 游戏状态的 Python 绑定
  - [x] 实现 `PyActionMask` - 动作掩码的 Python 绑定
  - [x] 实现 `PyGameEngine` - 游戏引擎的 Python 绑定
  - [x] 添加 Python 模块初始化函数
- [x] 确保 Tensor 转换在 Rust 侧完成以减少内存拷贝
  - [x] 实现 `state_to_tensor()` - 将游戏状态转换为 NumPy 数组 (64×4×9)
  - [x] 实现 `action_mask_to_array()` - 将动作掩码转换为 NumPy 数组 (434,)
  - [x] 所有 Tensor 转换在 Rust 侧完成，避免 Python 侧的内存拷贝

---

## 🧠 第二阶段：神经网络与表示学习 (Representation)

定义 AI 如何"看"和"想"。

### 2.1 特征编码设计

- [ ] **基础层**：
  - [ ] 手牌（4 层）
  - [ ] 弃牌
  - [ ] 副露
- [ ] **全局层**：
  - [ ] 剩余牌数
  - [ ] 当前局势（谁已胡、谁离场）
  - [ ] 各家定缺色

### 2.2 模型架构搭建

- [ ] 实现 20+ 层的 ResNet 或轻量级 Transformer 骨干网
- [ ] 设计 Dual-head 输出：
  - [ ] Policy（动作概率）
  - [ ] Value（期望收益分数）

### 2.3 Oracle 特征设计

- [ ] 为"上帝视角"准备特有通道（对手暗牌、牌堆余牌）
- [ ] 仅限训练阶段使用

---

## 🚀 第三阶段：强化学习训练循环 (Self-Play Loop)

让 AI 能够通过自我博弈产生进化。

### 3.1 分布式框架配置

- [ ] 配置 Ray 或分布式并行环境
- [ ] 支持数百个 Rust 实例同时生成轨迹（Trajectories）

### 3.2 PPO 算法核心

- [ ] 实现经验回放池
- [ ] 优势函数（Advantage）计算
- [ ] 策略裁剪（Clipping）

### 3.3 奖励函数初调 (Reward Shaping)

- [ ] **引导奖惩**：
  - [ ] 早期学会听牌
  - [ ] 避免成为花猪
- [ ] **最终奖励**：以局末真实得分（金币/积分）为唯一最终指标

### 3.4 评估系统 (Evaluator)

- [ ] 实现 Elo 评分机制
- [ ] 定期自动保存 Checkpoint
- [ ] 与历史最强版本对弈

---

## 🎯 第四阶段：顶级博弈优化 (Expert Tuning)

从"会打"到"顶级"的飞跃。

### 4.1 ISMCTS 搜索算法

- [ ] 在推理端实现信息集蒙特卡洛树搜索
- [ ] 对未知牌墙进行 Determinization 采样

### 4.2 对抗性鲁棒训练

- [ ] 针对性模拟极端局势：
  - [ ] 被三家定缺针对
  - [ ] 起手极烂
- [ ] 提升防御避炮能力

### 4.3 超参数自动化搜索

- [ ] 学习率调优
- [ ] 探索因子（Entropy Loss）调优
- [ ] 搜索深度调优

---

## 📈 进度里程碑 (Milestones)

### Level 1 (Entry) - 入门级

- AI 能正确执行定缺、出牌、胡牌
- 不再因花猪被扣分

### Level 2 (Amateur) - 业余级

- AI 学会基本的凑番策略（如清一色、对对胡）
- 开始主动避开对手的缺门色

### Level 3 (Pro) - 专业级

- AI 掌握"过胡"博大番的时机
- 通过上帝视角训练学会在残局精准防守

### Level 4 (Elite) - 精英级

- AI 在大规模对测中稳定击败高水平人类玩家模型
- 掌握复杂的诱导操作（如打假缺）

---

## 使用说明

- 每个阶段按顺序完成，确保基础稳固后再进入下一阶段
- 使用复选框 `[ ]` 跟踪完成进度
- 完成所有 Level 1 任务后，AI 应能正常运行基本对局
- 达到 Level 4 后，AI 应具备人类顶级水平
