# 喂牌机制实现说明

## 概述

喂牌机制通过生成更容易学习的牌局，帮助AI在初期更快学会基本技能。目前Python端已实现框架，但需要Rust端支持才能完全工作。

## 当前状态

### ✅ 已实现（Python端）

1. **喂牌生成器** (`python/scai/selfplay/feeding_games.py`)
   - 生成接近听牌或已听牌的手牌
   - 支持多种胡牌类型（基本胡牌、七对、清一色）
   - 支持难度级别配置

2. **课程学习集成**
   - 在"学胡阶段"自动启用喂牌模式
   - 根据阶段自动启用/禁用喂牌

3. **配置支持**
   - 在 `config.yaml` 中配置喂牌参数
   - 支持难度级别和喂牌概率

### ⚠️ 需要实现（Rust端）

为了完全支持喂牌机制，需要在Rust端添加以下功能：

1. **设置玩家手牌**
   ```rust
   // 在 PyGameState 或 PyGameEngine 中添加
   pub fn set_player_hand(&mut self, player_id: u8, hand: Vec<(u8, u8)>) -> PyResult<()>
   ```
   - `hand`: 手牌列表，每个元素是 `(tile_index, count)`
   - `tile_index`: 牌型索引（0-26）
   - `count`: 该牌的数量（1-4）

2. **修改牌墙顺序**（可选，更高级）
   ```rust
   // 在 PyGameEngine 中添加
   pub fn set_wall_order(&mut self, tile_order: Vec<u8>) -> PyResult<()>
   ```
   - 允许设置牌墙的抽取顺序
   - 可以在牌墙中放置AI需要的牌

## 临时解决方案

在Rust端完全支持之前，可以使用以下临时方案：

### 方案1: 重新初始化游戏（简化版）

```python
# 在 play_game 中
if self.use_feeding and self.feeding_generator.should_generate_feeding_game():
    # 生成喂牌手牌
    feeding_hand = self.feeding_generator.generate_feeding_hand(0, 'basic')
    
    # 重新初始化游戏，直到手牌接近喂牌手牌
    # 这是一个简化的实现，实际效果可能不理想
    max_attempts = 10
    for attempt in range(max_attempts):
        engine.initialize()
        state = engine.state
        hand = state.get_player_hand(0)
        
        # 检查手牌是否接近喂牌手牌
        if self._is_hand_similar(hand, feeding_hand):
            break
```

### 方案2: 在Rust端添加支持（推荐）

在 `rust/src/python/game_state.rs` 或 `rust/src/python/game_engine.rs` 中添加：

```rust
#[pyo3(name = "set_player_hand")]
pub fn set_player_hand_py(
    &mut self,
    player_id: u8,
    hand: Vec<(u8, u8)>,  // (tile_index, count)
) -> PyResult<()> {
    if player_id >= 4 {
        return Err(PyValueError::new_err("Invalid player_id"));
    }
    
    let player = &mut self.0.players[player_id as usize];
    player.hand.clear();
    
    for (tile_index, count) in hand {
        if tile_index >= 27 {
            return Err(PyValueError::new_err("Invalid tile_index"));
        }
        if count > 4 {
            return Err(PyValueError::new_err("Invalid count"));
        }
        
        // 将 tile_index 转换为 Tile
        let tile = self._index_to_tile(tile_index)?;
        for _ in 0..count {
            player.hand.add_tile(tile);
        }
    }
    
    Ok(())
}

fn _index_to_tile(&self, index: u8) -> PyResult<Tile> {
    // 将 0-26 的索引转换为 Tile
    // 0-8: Wan(1-9)
    // 9-17: Tong(1-9)
    // 18-26: Tiao(1-9)
    if index < 9 {
        Ok(Tile::Wan(index + 1))
    } else if index < 18 {
        Ok(Tile::Tong(index - 9 + 1))
    } else if index < 27 {
        Ok(Tile::Tiao(index - 18 + 1))
    } else {
        Err(PyValueError::new_err("Invalid tile index"))
    }
}
```

## 使用方式

### 1. 在配置中启用

```yaml
curriculum_learning:
  enabled: true
  initial_stage: declare_suit
  feeding_games:
    enabled: true
    difficulty: easy
    feeding_rate: 0.2  # 2:8比例：20%喂牌，80%随机
    win_types:
      - basic
      - seven_pairs
```

### 2. 系统自动工作

- 在"学胡阶段"自动启用喂牌
- 80%的游戏使用喂牌模式
- 生成接近听牌的手牌，帮助AI学会胡牌

### 3. 手动控制

```python
from scai.selfplay.feeding_games import FeedingGameGenerator

generator = FeedingGameGenerator(difficulty='easy')

# 生成喂牌手牌
feeding_hand = generator.generate_feeding_hand(
    target_player_id=0,
    win_type='basic'
)
```

## 喂牌手牌示例

### 基本胡牌（接近听牌）

```
手牌: [1万, 2万, 3万, 4万, 5万, 6万, 7万, 8万, 9万, 1万, 2万, 3万, 1筒]
状态: 已听牌，听 1筒
```

### 七对（接近听牌）

```
手牌: [1万×2, 2万×2, 3万×2, 4万×2, 5万×2, 6万×2, 1筒]
状态: 接近七对，缺1张1筒
```

## 注意事项

1. **喂牌是训练辅助**: 只在特定阶段使用，最终要过渡到正常牌局
2. **逐步提高难度**: 从喂牌到正常牌局，逐步提高难度
3. **监控学习进度**: 确保AI真正学会了技能，而不只是依赖喂牌
4. **Rust端支持**: 需要Rust端添加设置手牌的功能才能完全工作

## 下一步

1. **实现Rust端支持**: 添加 `set_player_hand()` 方法
2. **测试喂牌效果**: 验证喂牌是否能帮助AI更快学会胡牌
3. **调整喂牌策略**: 根据实际效果调整喂牌概率和难度

