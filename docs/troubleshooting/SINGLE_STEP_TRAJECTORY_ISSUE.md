# 单步轨迹问题分析

## 问题描述

观察到所有轨迹只有1步，且所有奖励都是0：
```
Debug: Trajectory 0: All 1 step rewards are zero
  First 5 rewards: [0.0]
  Final score: 0.0
```

## 问题分析

### 正常流程应该是：
1. 摸牌
2. 获取状态和动作掩码
3. **保存状态**（`trajectory['states'].append(...)`）
4. 执行动作
5. **添加奖励**（`trajectory['rewards'].append(...)`）
6. 继续下一回合

### 问题流程（只有1步）：
1. 摸牌
2. 获取状态和动作掩码
3. **保存状态**（`trajectory['states'].append(...)`）
4. **游戏提前退出**（在动作执行前或动作执行失败）
5. **没有添加奖励**（或添加了0.0奖励）
6. 游戏结束

## 可能的原因

### 1. **动作执行失败导致continue**
**位置**：`worker.py:599-603`
```python
except Exception as e:
    print(f"Worker {self.worker_id}, Game {game_id}, Turn {turn_count} error: {e}")
    # 如果动作失败，添加默认奖励并跳过这个回合
    trajectory['rewards'].append(0.0)
    continue
```

**问题**：
- 如果动作执行失败，会添加0.0奖励并`continue`
- 但如果下一个循环也失败，或者游戏提前退出，就会导致只有1步

### 2. **游戏提前退出（在动作执行前）**
**可能的位置**：
- 摸牌后状态获取失败（line 342-347）
- 其他异常导致提前`break`

**问题**：
- 如果状态已经保存（line 436），但动作还没执行就退出
- 会导致状态数量 > 奖励数量
- 代码会在最后补齐（line 648-651），但补齐的是0.0

### 3. **游戏在第一次循环就退出**
**可能的原因**：
- 游戏初始化失败
- 定缺阶段失败
- 第一次摸牌就失败
- 第一次状态获取就失败

## 诊断步骤

### 1. 检查日志
查找以下错误信息：
- `"Failed to get state"`
- `"Draw error"`
- `"Turn X error"`
- `"Game X ended early"`

### 2. 检查轨迹数据
```python
# 检查轨迹完整性
print(f"States: {len(trajectory['states'])}")
print(f"Actions: {len(trajectory['actions'])}")
print(f"Rewards: {len(trajectory['rewards'])}")
print(f"Dones: {len(trajectory['dones'])}")
print(f"Readable states: {len(trajectory.get('readable_states', []))}")
```

### 3. 检查游戏结束原因
```python
if trajectory.get('readable_states'):
    final_state = trajectory['readable_states'][-1]
    end_reason = final_state.get('game_end_reason', 'unknown')
    print(f"Game end reason: {end_reason}")
```

## 解决方案

### 1. **增加详细日志**
在关键位置添加日志，记录游戏退出的原因：
```python
if len(trajectory['states']) == 1:
    logger.warning(f"Game {game_id} ended after only 1 step. "
                   f"Turn: {turn_count}, "
                   f"Remaining tiles: {engine.remaining_tiles()}, "
                   f"Game over: {engine.is_game_over()}")
```

### 2. **检查动作执行失败的原因**
如果动作执行频繁失败，需要：
- 检查动作掩码是否正确
- 检查动作是否合法
- 检查游戏引擎状态

### 3. **改进错误处理**
对于动作执行失败，不应该简单地`continue`，应该：
- 记录失败原因
- 检查是否可以恢复
- 如果无法恢复，应该正常退出而不是继续

### 4. **验证游戏初始化**
确保游戏正确初始化：
- 检查定缺是否成功
- 检查游戏引擎状态
- 检查是否有足够的牌

## 临时解决方案

如果问题持续，可以：
1. **过滤单步轨迹**：在collector中过滤掉只有1步的轨迹
2. **增加最小步数要求**：只保存至少N步的轨迹
3. **增加重试机制**：对于失败的游戏，重试一次

## 建议的代码修改

### 1. 在游戏循环开始前检查
```python
# 检查游戏是否已经结束
if engine.is_game_over():
    logger.warning(f"Game {game_id} already over before main loop")
    return empty_trajectory()

# 检查牌墙
if engine.remaining_tiles() == 0:
    logger.warning(f"Game {game_id} has no tiles before main loop")
    return empty_trajectory()
```

### 2. 在动作执行失败时记录详细信息
```python
except Exception as e:
    logger.error(f"Worker {self.worker_id}, Game {game_id}, Turn {turn_count} error: {e}")
    logger.error(f"  Action: {action_type}, tile_index: {tile_index}")
    logger.error(f"  Current player: {current_player}")
    logger.error(f"  Remaining tiles: {engine.remaining_tiles()}")
    logger.error(f"  Game over: {engine.is_game_over()}")
    # 如果动作失败，添加默认奖励并跳过这个回合
    trajectory['rewards'].append(0.0)
    continue
```

### 3. 在游戏结束时检查轨迹完整性
```python
# 检查轨迹是否异常短
if len(trajectory['states']) <= 1:
    logger.warning(f"Game {game_id} ended with only {len(trajectory['states'])} steps. "
                   f"This is unusual. Check logs for errors.")
```

