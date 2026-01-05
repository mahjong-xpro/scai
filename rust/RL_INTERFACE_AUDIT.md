# AI 训练专用接口审计 (RL Interface Audit)

## 审计结果

### ✅ 1. `fn to_tensor(&self) -> Vec<f32>` - 已实现

**用户要求**：
- 将复杂的 `GameState` 扁平化为 `Vec<f32>`
- 顶级 AI 必须包含"牌池可见性"特征（即：场上 108 张牌，每张目前出现了几张）

**实现状态**：✅ **已实现**

**实现位置**：
- `rust/src/python/game_state.rs` - `PyGameState::to_tensor()` 方法

**实现细节**：
1. **4D tensor 扁平化**：将 `state_to_tensor()` 返回的 4D tensor（64×4×9）扁平化为 2304 个浮点数
2. **牌池可见性特征**：通过 `compute_tile_visibility()` 方法统计每张牌（108 张）的出现次数
   - 统计所有玩家的手牌
   - 统计已碰/杠的牌（碰：3 张，杠：4 张）
   - 统计弃牌历史
   - 输出：108 个浮点数，每个表示该牌目前出现了几张（0-4）

**返回格式**：
- 总计：2412 个浮点数
  - 前 2304 个：4D tensor 扁平化（64 × 4 × 9）
  - 后 108 个：牌池可见性特征（每张牌的出现次数）

**方法签名**：
```rust
fn to_tensor(&self, player_id: u8, remaining_tiles: Option<usize>, py: Python) -> PyResult<Vec<f32>>
```

---

### ✅ 2. `fn get_action_mask(&self) -> Vec<f32>` - 已实现

**用户要求**：
- 返回一个长度为动作空间总数的 0/1 数组（`Vec<f32>`）

**实现状态**：✅ **已实现**

**实现位置**：
- `rust/src/python/action_mask.rs` - `PyActionMask::get_action_mask()` 静态方法

**实现细节**：
1. **生成动作掩码**：使用 `ActionMask::generate()` 生成动作掩码
2. **转换为布尔数组**：使用 `to_bool_array()` 转换为 434 个布尔值
3. **转换为浮点数数组**：将 `bool` 转换为 `f32`（true → 1.0，false → 0.0）

**返回格式**：
- 长度为 434 的 `Vec<f32>`
- 每个元素为 0.0 或 1.0
- 动作空间定义：
  - 索引 0-107: 出牌动作（对应 108 种牌）
  - 索引 108-215: 碰牌动作（对应 108 种牌）
  - 索引 216-323: 杠牌动作（对应 108 种牌）
  - 索引 324-431: 胡牌动作（对应 108 种牌）
  - 索引 432: 摸牌动作
  - 索引 433: 过（放弃）动作

**方法签名**：
```rust
#[staticmethod]
pub fn get_action_mask(
    player_id: u8,
    state: &PyGameState,
    is_own_turn: bool,
    discarded_tile: Option<u8>,
) -> PyResult<Vec<f32>>
```

---

## 总结

- ✅ **`to_tensor()` 方法**：已实现
  - 已添加到 `PyGameState`，返回 `Vec<f32>`
  - 包含 4D tensor 扁平化（2304 个浮点数）
  - 包含"牌池可见性"特征（108 个浮点数）
  - 总计：2412 个浮点数
  
- ✅ **`get_action_mask()` 方法**：已实现
  - 已添加到 `PyActionMask`，返回 `Vec<f32>`
  - 将 `bool` 转换为 `f32`（true → 1.0，false → 0.0）
  - 长度为 434（动作空间总数）

两个接口已实现，满足 AI 训练的需求。代码已通过编译检查。
