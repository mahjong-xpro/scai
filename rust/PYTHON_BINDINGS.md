# PyO3 接口绑定实现说明

## 概述

已实现完整的 PyO3 接口绑定，将 Rust 游戏引擎暴露给 Python，支持高性能的游戏状态转换和动作处理。

## 已实现的模块

### 1. `PyGameState` - 游戏状态绑定

**文件**: `src/python/game_state.rs`

**功能**:
- 将 `GameState` 暴露给 Python
- 提供游戏状态的查询接口
- 支持获取玩家手牌、定缺、听牌状态等

**主要方法**:
- `new()` - 创建新的游戏状态
- `get_player_hand()` - 获取玩家手牌（返回 Python 字典）
- `get_player_declared_suit()` - 获取玩家定缺花色
- `is_player_out()` - 检查玩家是否已离场
- `is_player_ready()` - 检查玩家是否听牌
- `is_game_over()` - 检查游戏是否结束

### 2. `PyActionMask` - 动作掩码绑定

**文件**: `src/python/action_mask.rs`

**功能**:
- 将 `ActionMask` 暴露给 Python
- 生成合法动作掩码
- 验证动作合法性

**主要方法**:
- `generate()` - 生成动作掩码（响应别人的出牌）
- `generate_own_turn()` - 生成动作掩码（自己的回合）
- `to_bool_array()` - 转换为布尔数组（434 个动作）
- `validate_action()` - 验证动作是否合法
- `tile_to_index()` / `index_to_tile()` - 牌和索引的转换

### 3. `PyGameEngine` - 游戏引擎绑定

**文件**: `src/python/game_engine.rs`

**功能**:
- 将 `GameEngine` 暴露给 Python
- 处理游戏动作
- 管理游戏流程

**主要方法**:
- `new()` - 创建新的游戏引擎
- `initialize()` - 初始化游戏（发牌）
- `process_action()` - 处理动作（draw, discard, pong, gang, win, pass）
- `is_game_over()` - 检查游戏是否结束
- `state` - 获取游戏状态

### 4. Tensor 转换函数

**文件**: `src/python/tensor.rs`

**功能**:
- 在 Rust 侧完成 Tensor 转换，减少内存拷贝
- 支持游戏状态和动作掩码的 NumPy 数组转换

**主要函数**:
- `state_to_tensor()` - 将游戏状态转换为 NumPy 数组 (64×4×9)
- `action_mask_to_array()` - 将动作掩码转换为 NumPy 数组 (434,)

## 特征图设计

### 游戏状态 Tensor (64×4×9)

- **64 个特征平面**:
  - 平面 0-3: 自己的手牌（4 层，表示数量 1-4）
  - 平面 4-27: 其他三个玩家的手牌（每个玩家 4 层）
  - 平面 28-31: 定缺状态（4 个玩家）
  - 平面 32-35: 已碰/杠的牌（4 个玩家）
  - 平面 40-43: 玩家状态（是否离场）
  - 平面 44-47: 听牌状态
  - 平面 48-51: 回合信息
  - 平面 52-55: 当前玩家信息
  - 平面 56-59: 最后一张牌标记
  - 平面 60-63: 保留用于未来扩展

- **4 个玩家**: 每个特征平面包含 4 个玩家的信息
- **9 种牌**: 每种花色 1-9

### 动作掩码数组 (434,)

- 索引 0-107: 出牌动作（对应 108 种牌）
- 索引 108-215: 碰牌动作（对应 108 种牌）
- 索引 216-323: 杠牌动作（对应 108 种牌）
- 索引 324-431: 胡牌动作（对应 108 种牌）
- 索引 432: 摸牌动作
- 索引 433: 过（放弃）动作

## 使用示例

### Python 代码示例

```python
import scai_engine
import numpy as np

# 创建游戏引擎
engine = scai_engine.PyGameEngine()
engine.initialize()

# 获取游戏状态
state = engine.state

# 生成动作掩码（自己的回合）
mask = scai_engine.PyActionMask.generate_own_turn(0, state)
bool_mask = mask.to_bool_array(True, None)

# 转换为 NumPy 数组
action_array = scai_engine.action_mask_to_array(mask, True, None)

# 将游戏状态转换为 Tensor
tensor = scai_engine.state_to_tensor(state, 0)
print(f"Tensor 形状: {tensor.shape}")  # (64, 4, 9)

# 处理动作
result = engine.process_action(
    player_id=0,
    action_type="draw",
    tile_index=None,
    is_concealed=None
)

# 验证动作是否合法
is_valid = scai_engine.PyActionMask.validate_action(
    action_index=432,  # 摸牌动作
    player_id=0,
    state=state,
    is_own_turn=True,
    discarded_tile=None
)
```

### 完整游戏流程示例

```python
import scai_engine
import numpy as np

# 1. 创建并初始化游戏
engine = scai_engine.PyGameEngine()
engine.initialize()

# 2. 获取当前游戏状态
state = engine.state
print(f"当前玩家: {state.current_player}")
print(f"回合数: {state.turn}")

# 3. 生成当前玩家的动作掩码
player_id = state.current_player
mask = scai_engine.PyActionMask.generate_own_turn(player_id, state)

# 4. 转换为 NumPy 数组用于神经网络
action_mask = scai_engine.action_mask_to_array(mask, True, None)
state_tensor = scai_engine.state_to_tensor(state, player_id)

# 5. 使用神经网络选择动作（示例）
# action_index = neural_network.predict(state_tensor, action_mask)

# 6. 执行动作
result = engine.process_action(
    player_id=player_id,
    action_type="draw",  # 或 "discard", "pong", "gang", "win", "pass"
    tile_index=None,  # 对于 discard/pong/gang 需要提供牌索引
    is_concealed=None  # 对于 gang 需要提供是否暗杠
)

# 7. 检查游戏是否结束
if engine.is_game_over():
    print("游戏结束")
```

### 测试

运行 Python 测试：

```bash
# 确保已编译 Python 扩展模块
cd rust
cargo build --release --features python

# 运行测试
cd ..
python tests/test_python_bindings.py
```

## 编译和安装

### 编译 Python 扩展模块

```bash
cd rust
cargo build --release --features python
```

### 安装到 Python 环境

```bash
# 使用 maturin（推荐）
pip install maturin
maturin develop --features python

# 或手动安装
python setup.py install
```

## 性能优化

1. **Tensor 转换在 Rust 侧完成**: 所有 NumPy 数组的创建和填充都在 Rust 侧完成，避免 Python 侧的内存拷贝
2. **零拷贝转换**: 使用 PyO3 和 numpy 的零拷贝特性，直接共享内存
3. **特征**: 使用 `python` feature 控制是否编译 Python 绑定，避免不必要的依赖

## 注意事项

1. 需要安装 PyO3 和 numpy Rust 绑定
2. 需要 Python 3.8+ 和 NumPy
3. 编译时需要启用 `python` feature: `cargo build --features python`

