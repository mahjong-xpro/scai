# 特征编码器 (Observation Encoder) 实现

## 概述

特征编码器将游戏状态（GameState）转换为多维张量，为 AI 提供"空间感"。所有编码在 Rust 侧完成，避免 Python 端处理的低效。

## 张量规格

- **形状**: `[64, 4, 9]`
  - 64 个特征平面
  - 4 个玩家
  - 9 种牌（每种花色 1-9）

## 核心特征平面（前 13 个）

### Plane 0-3: 自身手牌（One-hot 表示 1-4 张）

每个平面表示手牌中该牌的数量：
- Plane 0: 有 1 张的牌
- Plane 1: 有 2 张的牌
- Plane 2: 有 3 张的牌
- Plane 3: 有 4 张的牌

**编码方式**: One-hot，如果手牌中有 N 张某牌，则在 Plane (N-1) 的对应位置标记为 1.0

### Plane 4-10: 三个对手的弃牌（带顺序感）

**分配策略**:
- 对手 1: Plane 4-5（最近 2 次弃牌）
- 对手 2: Plane 6-7（最近 2 次弃牌）
- 对手 3: Plane 8-9（最近 2 次弃牌）
- Plane 10: 最近一次弃牌（所有玩家，全局视角）

**编码方式**: 
- 从弃牌历史中筛选每个对手的弃牌
- 按时间倒序（最近优先）填充到对应平面
- Plane 10 记录最近一次弃牌，提供全局视角

### Plane 11: 场上剩余牌堆计数

**编码方式**: 
- 将剩余牌数归一化到 [0, 1] 范围（假设最多 108 张）
- 公式: `normalized_count = min(remaining / 108.0, 1.0)`
- 所有位置填充相同的归一化值

### Plane 12: 定缺掩码

**编码方式**:
- 标记每个玩家的定缺花色
- 如果玩家 P 定缺花色 S，则在 Plane 12 的 [P, S, *] 位置标记为 1.0

## 扩展特征平面（13-63）

保留原有特征，从 Plane 13 开始：
- Plane 13-24: 其他三个玩家的手牌（每个玩家 4 层）
- Plane 25-28: 已碰/杠的牌（4 个玩家）
- Plane 29-32: 玩家状态（是否离场）
- Plane 33-36: 听牌状态
- Plane 37-40: 回合信息
- Plane 41-44: 当前玩家信息
- Plane 45: 最后一张牌标记
- Plane 46-63: 保留用于未来扩展

## 数据结构增强

### 弃牌历史记录

在 `GameState` 中添加了 `discard_history: Vec<DiscardRecord>`：

```rust
pub struct DiscardRecord {
    pub player_id: u8,
    pub tile: Tile,
    pub turn: u32,
}
```

每次出牌时自动记录到 `discard_history`。

## API 接口

### Rust 函数

```rust
pub fn state_to_tensor(
    state: &PyGameState,
    player_id: u8,
    remaining_tiles: Option<usize>,
    py: Python,
) -> PyResult<Py<PyArray3<f32>>>
```

### Python 调用

```python
import scai_engine

# 创建游戏引擎
engine = scai_engine.PyGameEngine()
engine.initialize()

# 获取游戏状态和剩余牌数
state = engine.state
remaining = engine.remaining_tiles()

# 转换为张量（从玩家 0 的视角）
tensor = scai_engine.state_to_tensor(state, 0, remaining)
print(f"Tensor 形状: {tensor.shape}")  # (64, 4, 9)
```

## 设计优势

1. **空间感**: 通过多平面编码，AI 可以理解牌的分布和顺序
2. **高效**: 所有编码在 Rust 侧完成，避免 Python 端的内存拷贝
3. **可扩展**: 保留 64 个平面，便于未来添加新特征
4. **顺序感**: 弃牌历史记录提供时间序列信息

## 使用示例

### 示例 1: 基本使用

```python
import scai_engine
import numpy as np

engine = scai_engine.PyGameEngine()
engine.initialize()

state = engine.state
remaining = engine.remaining_tiles()

# 从玩家 0 的视角编码
tensor = scai_engine.state_to_tensor(state, 0, remaining)

# 检查自身手牌（Plane 0-3）
own_hand = tensor[0:4, :, :]  # Shape: (4, 4, 9)

# 检查对手弃牌（Plane 4-10）
opponent_discards = tensor[4:11, :, :]  # Shape: (7, 4, 9)

# 检查剩余牌数（Plane 11）
remaining_count = tensor[11, 0, 0]  # 所有位置值相同

# 检查定缺掩码（Plane 12）
declared_mask = tensor[12, :, :]  # Shape: (4, 9)
```

### 示例 2: 神经网络输入

```python
# 将张量转换为 PyTorch Tensor
import torch

tensor = scai_engine.state_to_tensor(state, player_id, remaining)
state_tensor = torch.from_numpy(tensor)

# 输入到神经网络（假设输入形状为 [batch, channels, height, width]）
# 需要添加 batch 维度
state_batch = state_tensor.unsqueeze(0)  # Shape: (1, 64, 4, 9)

# 通过神经网络
output = model(state_batch)
```

## 注意事项

1. **剩余牌数**: 如果未提供 `remaining_tiles`，默认使用 0（Plane 11 全为 0）
2. **弃牌历史**: 只记录最近几次弃牌，避免历史过长
3. **视角**: 张量编码是从指定玩家视角，手牌信息会相应调整
4. **归一化**: 剩余牌数归一化到 [0, 1]，便于神经网络处理

## 性能优化

- 使用 `PyArray3::zeros` 预分配内存
- 在 Rust 侧完成所有计算，避免 Python 循环
- 使用 unsafe 块直接操作数组，减少边界检查

## 测试

运行测试确保编码器正常工作：

```bash
cd rust
cargo test --lib
```

## 未来扩展

可以考虑添加的特征：
- 已碰/杠的牌的历史信息
- 玩家动作历史（最近 N 次动作）
- 听牌可能性（概率分布）
- 对手可能的听牌牌型

