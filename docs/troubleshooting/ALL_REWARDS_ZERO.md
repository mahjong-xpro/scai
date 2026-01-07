# 所有奖励为零的问题分析

## 问题描述

训练日志显示：
- **所有轨迹都是有效的**（100% valid rate）
- **所有奖励都是 0**（100% 的轨迹都有 "All rewards are zero" 警告）
- 训练在进行，loss 值看起来正常

## 问题分析

### 1. 奖励计算逻辑

奖励由两部分组成：
1. **单步奖励**（`compute_step_reward`）：在游戏进行过程中计算
2. **最终奖励**（`compute_final_reward`）：在游戏结束时计算

### 2. 单步奖励返回 0 的原因

`compute_step_reward` 在以下情况下返回 0.0：

1. **奖励配置问题**：
   - 如果 `reward_config.get('raw_score_only', False) == True`，直接返回 0.0
   - 如果 `reward_config` 中没有配置相应的奖励项，且默认值也为 0

2. **游戏状态问题**：
   - `is_ready=False`（玩家没有听牌）
   - `is_hu=False`（玩家没有胡牌）
   - `is_flower_pig=False`（玩家没有成为花猪）
   - 没有向听数改善（`shanten` 和 `previous_shanten` 未提供或未改善）

3. **Worker 初始化问题**：
   - `SelfPlayWorker` 中 `RewardShaping` 初始化时没有传入 `reward_config`
   - 这意味着 worker 使用的是默认配置，可能与主进程的配置不一致

### 3. 最终奖励返回 0 的原因

`compute_final_reward` 在以下情况下返回 0.0：

1. **游戏流局**：
   - 如果游戏流局（没有玩家胡牌），`final_score` 可能是 0.0
   - 如果 `final_score == 0.0`，且 `raw_score_only=False`，最终奖励也是 0.0

2. **得分提取失败**：
   - `_extract_final_score_from_settlement` 使用正则表达式从结算字符串中提取得分
   - 如果解析失败，返回 0.0
   - 如果游戏流局，可能没有结算字符串

### 4. 当前代码问题

**问题 1：Worker 中的 RewardShaping 没有 reward_config**

```python
# worker.py 第 83 行
self.reward_shaping = RewardShaping()  # 没有传入 reward_config
```

**问题 2：奖励计算时没有传入向听数**

```python
# worker.py 第 410-414 行
reward = self.reward_shaping.compute_step_reward(
    is_ready=is_ready_after,
    is_hu=is_hu,
    is_flower_pig=is_flower_pig,
    # 缺少：shanten, previous_shanten 等参数
)
```

**问题 3：游戏可能流局**

如果游戏流局（没有玩家胡牌），所有奖励都是 0。

## 诊断步骤

### 1. 检查游戏是否正常结束

在 `worker.py` 中添加日志，检查：
- 游戏是否正常结束（有玩家胡牌）
- 游戏流局的比例
- `final_score` 的分布

### 2. 检查奖励配置

检查 `reward_config` 是否被正确传递到 worker：
- 主进程中的 `reward_config` 是什么
- Worker 中的 `RewardShaping` 是否使用了正确的配置

### 3. 检查奖励计算

在 `worker.py` 中添加日志，检查：
- `is_ready`、`is_hu`、`is_flower_pig` 的值
- `compute_step_reward` 的返回值
- `final_score` 的值
- `compute_final_reward` 的返回值

## 解决方案

### 方案 1：传递 reward_config 到 Worker（推荐）

修改 `worker.py`，让 `RewardShaping` 使用与主进程相同的配置：

```python
# 在 DataCollector 中传递 reward_config
def collect(self, model_state_dict, ...):
    # ...
    reward_config = self.reward_shaping.reward_config
    # 传递给 worker
    futures = [worker.play_game.remote(
        model_state_dict=model_state_dict,
        reward_config=reward_config,  # 传递配置
        ...
    ) for worker in self.workers]
```

```python
# 在 SelfPlayWorker 中使用 reward_config
def __init__(self, ..., reward_config=None):
    # ...
    self.reward_shaping = RewardShaping(reward_config=reward_config or {})
```

### 方案 2：添加向听数奖励

在 `worker.py` 中计算并传递向听数：

```python
# 计算向听数
shanten = self._calculate_shanten(state, current_player)
previous_shanten = trajectory.get('last_shanten', None)

# 传递到奖励计算
reward = self.reward_shaping.compute_step_reward(
    is_ready=is_ready_after,
    is_hu=is_hu,
    is_flower_pig=is_flower_pig,
    shanten=shanten,
    previous_shanten=previous_shanten,
)
```

### 方案 3：改进最终得分提取

改进 `_extract_final_score_from_settlement`，确保正确提取得分：

```python
def _extract_final_score_from_settlement(
    self,
    settlement_str: str,
    player_id: int,
) -> float:
    """从结算结果中提取最终得分"""
    try:
        # 尝试解析 JSON 格式的结算结果
        import json
        settlement = json.loads(settlement_str)
        if 'payments' in settlement:
            payments = settlement['payments']
            if player_id in payments:
                return float(payments[player_id])
    except:
        pass
    
    # 回退到正则表达式
    try:
        import re
        pattern = rf'{player_id}:\s*([+-]?\d+)'
        match = re.search(pattern, settlement_str)
        if match:
            return float(match.group(1))
    except:
        pass
    
    return 0.0
```

### 方案 4：添加调试日志

在 `worker.py` 中添加调试日志，帮助诊断问题：

```python
# 在奖励计算后添加日志
if reward != 0.0:
    print(f"Worker {self.worker_id}, Game {game_id}, Turn {turn_count}, "
          f"Reward: {reward}, is_ready: {is_ready_after}, "
          f"is_hu: {is_hu}, is_flower_pig: {is_flower_pig}")

# 在游戏结束时添加日志
if trajectory['final_score'] != 0.0:
    print(f"Worker {self.worker_id}, Game {game_id}, "
          f"Final score: {trajectory['final_score']}")
else:
    print(f"Worker {self.worker_id}, Game {game_id}, "
          f"Game ended with final_score=0.0 (可能流局)")
```

## 临时解决方案

如果问题是由于游戏流局导致的，可以：

1. **增加游戏长度**：确保游戏有足够的时间让玩家胡牌
2. **降低胡牌难度**：在初期训练中，降低胡牌的门槛
3. **添加稀疏奖励**：即使游戏流局，也给予少量奖励（例如：根据向听数给予奖励）

## 检查清单

- [ ] 检查游戏是否正常结束（有玩家胡牌）
- [ ] 检查 `reward_config` 是否被正确传递到 worker
- [ ] 检查 `compute_step_reward` 的输入参数
- [ ] 检查 `_extract_final_score_from_settlement` 是否正确提取得分
- [ ] 添加调试日志，查看奖励计算的详细过程

## 总结

"All rewards are zero" 的问题可能由以下原因导致：

1. **奖励配置未传递到 Worker**：Worker 中的 `RewardShaping` 使用默认配置，可能所有奖励都是 0
2. **游戏流局**：如果游戏流局（没有玩家胡牌），所有奖励都是 0
3. **奖励计算参数缺失**：如果 `is_ready`、`is_hu`、`is_flower_pig` 都是 `False`，且没有向听数奖励，所有奖励都是 0

**建议**：
1. 首先检查游戏是否正常结束（有玩家胡牌）
2. 然后检查 `reward_config` 是否被正确传递到 worker
3. 最后添加调试日志，查看奖励计算的详细过程

