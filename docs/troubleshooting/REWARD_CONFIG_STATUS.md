# 奖励配置状态检查

## 当前配置状态

### 1. config.yaml 中的基础奖励配置 ✅

```yaml
training:
  ready_reward: 0.1            # 听牌奖励
  hu_reward: 1.0               # 胡牌奖励
  flower_pig_penalty: -5.0     # 花猪惩罚
  final_score_weight: 1.0      # 最终得分权重
```

**状态**：✅ 已配置

### 2. 课程学习配置 ⚠️

```yaml
curriculum_learning:
  enabled: false               # ⚠️ 课程学习未启用
```

**状态**：⚠️ **未启用**

**影响**：
- 如果 `curriculum_learning.enabled = false`，`initial_reward_config = {}`（空字典）
- `RewardShaping` 会使用空的 `reward_config = {}`
- 在 `compute_step_reward` 中，如果 `reward_config` 是空的，很多奖励项无法计算

### 3. RewardShaping 的默认行为

查看 `reward_shaping.py` 的 `compute_step_reward` 方法：

```python
def compute_step_reward(
    self,
    is_ready: bool = False,
    is_hu: bool = False,
    is_flower_pig: bool = False,
    shanten: Optional[int] = None,
    previous_shanten: Optional[int] = None,
    ...
) -> float:
    reward = 0.0
    
    # 如果使用阶段特定的奖励配置
    if self.reward_config.get('raw_score_only', False):
        return 0.0
    
    # 定缺相关奖励（阶段1）
    if lack_color_discard:
        reward += self.reward_config.get('lack_color_discard', 0.0)  # ⚠️ 如果 reward_config 是空的，返回 0.0
    
    # 向听数奖励（阶段2-4）
    shanten_weight = self.reward_config.get('shanten_reward', self.shanten_reward_weight if self.use_shanten_reward else 0.0)
    # ⚠️ 如果 reward_config 是空的，且 use_shanten_reward=False，shanten_weight = 0.0
    
    # 听牌奖励（如果未在向听数奖励中处理）
    if is_ready and shanten_weight == 0:
        reward += self.reward_config.get('ready_reward', self.ready_reward)  # ✅ 会使用 self.ready_reward (0.1)
    
    # 胡牌奖励（阶段3+）
    if is_hu:
        reward += self.reward_config.get('base_win', self.hu_reward)  # ✅ 会使用 self.hu_reward (1.0)
    
    # 花猪惩罚
    if is_flower_pig:
        reward += self.reward_config.get('flower_pig_penalty', self.flower_pig_penalty)  # ✅ 会使用 self.flower_pig_penalty (-5.0)
```

**分析**：
- ✅ **基础奖励会生效**：`is_ready`、`is_hu`、`is_flower_pig` 会使用 `self.ready_reward`、`self.hu_reward`、`self.flower_pig_penalty`
- ⚠️ **阶段特定奖励不会生效**：如果 `reward_config` 是空的，`lack_color_discard`、`shanten_reward` 等会返回 0.0
- ⚠️ **向听数奖励不会生效**：如果 `reward_config` 是空的，且 `use_shanten_reward=False`，向听数奖励不会计算

## 问题诊断

### 如果所有奖励都是 0，可能的原因：

1. **游戏流局**：没有玩家胡牌，`is_hu=False`，`final_score=0.0`
2. **玩家未听牌**：`is_ready=False`，且没有向听数奖励
3. **玩家未成为花猪**：`is_flower_pig=False`
4. **reward_config 为空**：阶段特定奖励（如向听数奖励）无法计算

## 解决方案

### 方案 1：启用课程学习（推荐）

修改 `config.yaml`：

```yaml
curriculum_learning:
  enabled: true                # ✅ 启用课程学习
  initial_stage: declare_suit  # 从定缺阶段开始
```

**优点**：
- 自动配置各阶段的奖励权重
- 根据训练进度自动调整奖励
- 提供更丰富的奖励信号

**缺点**：
- 需要课程学习模块支持

### 方案 2：手动配置 reward_config

在 `train.py` 中手动设置 `reward_config`：

```python
# 如果没有课程学习，使用默认的 reward_config
if not curriculum:
    initial_reward_config = {
        'ready_reward': 0.1,      # 听牌奖励
        'base_win': 1.0,          # 胡牌奖励
        'flower_pig_penalty': -5.0, # 花猪惩罚
        'shanten_reward': 0.05,    # 向听数奖励权重（可选）
        'shanten_decrease': 2.0,   # 向听数减少奖励（可选）
        'shanten_increase': -1.5,  # 向听数增加惩罚（可选）
    }
else:
    initial_reward_config = curriculum.get_current_reward_config()

reward_shaping = RewardShaping(
    ready_reward=training_config.get('ready_reward', 0.1),
    hu_reward=training_config.get('hu_reward', 1.0),
    flower_pig_penalty=training_config.get('flower_pig_penalty', -5.0),
    final_score_weight=training_config.get('final_score_weight', 1.0),
    reward_config=initial_reward_config,
)
```

### 方案 3：检查游戏是否正常结束

添加日志，检查游戏流局的比例：

```python
# 在 worker.py 中添加
if trajectory['final_score'] == 0.0:
    print(f"Worker {self.worker_id}, Game {game_id}: Game ended with final_score=0.0 (可能流局)")
```

## 当前状态总结

### ✅ 已配置
- `config.yaml` 中的基础奖励参数（`ready_reward`, `hu_reward`, `flower_pig_penalty`, `final_score_weight`）
- `RewardShaping` 会使用这些基础参数

### ⚠️ 未配置
- `curriculum_learning.enabled = false`，所以 `reward_config = {}`
- 阶段特定奖励（如向听数奖励）无法使用
- 如果游戏流局或玩家未听牌/未胡牌，奖励可能为 0

### 🔍 需要确认
1. 游戏是否正常结束（有玩家胡牌）？
2. 玩家是否听牌（`is_ready=True`）？
3. 玩家是否胡牌（`is_hu=True`）？
4. 最终得分是否正确提取（`final_score != 0.0`）？

## 建议

1. **首先检查游戏是否正常结束**：添加日志，统计游戏流局的比例
2. **如果游戏流局比例高**：考虑启用课程学习或添加向听数奖励
3. **如果游戏正常结束但奖励仍为 0**：检查 `is_ready`、`is_hu`、`is_flower_pig` 的值
4. **如果基础奖励应该生效但未生效**：检查 `reward_config` 传递是否正确

