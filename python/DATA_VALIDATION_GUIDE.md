# 数据验证指南 (Data Validation Guide)

## 概述

数据验证系统确保收集的轨迹数据质量，防止无效数据影响训练。系统会检查状态、动作、奖励、价值估计等所有数据的完整性和正确性。

## 快速开始

### 基本使用

数据验证已集成到 `DataCollector` 中，默认启用：

```python
from scai.selfplay.collector import DataCollector
from scai.training.buffer import ReplayBuffer
from scai.training.reward_shaping import RewardShaping

# 创建数据收集器（默认启用验证）
collector = DataCollector(
    buffer=buffer,
    reward_shaping=reward_shaping,
    validate_data=True,          # 启用数据验证
    strict_validation=False,    # 非严格模式（只警告，不抛出异常）
)
```

### 配置

在 `config.yaml` 中配置：

```yaml
selfplay:
  validate_data: true          # 是否验证轨迹数据
  strict_validation: false     # 严格验证模式
```

## 验证内容

### 1. 状态验证

- **形状检查**: 验证状态张量形状是否为 `(64, 4, 9)`
- **NaN/Inf 检查**: 检测无效数值
- **数值范围**: 检查数值是否在合理范围内

```python
# 状态应该是 numpy 数组，形状为 (64, 4, 9)
state = np.array(...)  # shape: (64, 4, 9)
```

### 2. 动作验证

- **类型检查**: 验证动作是否为整数
- **范围检查**: 验证动作是否在 `[0, 434)` 范围内
- **合法性检查**: 验证动作是否被动作掩码允许

```python
# 动作应该是整数，范围 [0, 434)
action = 123  # 0 <= action < 434
```

### 3. 奖励验证

- **类型检查**: 验证奖励是否为数字
- **NaN/Inf 检查**: 检测无效数值
- **数值范围**: 检查奖励是否在合理范围内（通常 `[-1000, 1000]`）

```python
# 奖励应该是浮点数
reward = 10.5  # 合理的奖励值
```

### 4. 价值验证

- **类型检查**: 验证价值估计是否为数字
- **NaN/Inf 检查**: 检测无效数值

```python
# 价值估计应该是浮点数
value = 5.2  # 合理的价值估计
```

### 5. 对数概率验证

- **类型检查**: 验证对数概率是否为数字
- **NaN/Inf 检查**: 检测无效数值（`-inf` 是允许的，表示概率为 0）
- **数值范围**: 检查对数概率是否 `<= 0`（概率的对数应该 <= 0）

```python
# 对数概率应该是浮点数，通常 <= 0
log_prob = -2.3  # 合理的对数概率
```

### 6. 动作掩码验证

- **形状检查**: 验证动作掩码形状是否为 `(434,)`
- **值检查**: 验证掩码值是否为 0 或 1
- **一致性检查**: 验证选择的动作是否被掩码允许

```python
# 动作掩码应该是 numpy 数组，形状为 (434,)，值为 0 或 1
action_mask = np.array([0, 1, 1, 0, ...])  # shape: (434,)
assert action_mask[action] == 1  # 选择的动作必须被允许
```

### 7. 轨迹完整性验证

- **长度一致性**: 验证所有字段的长度是否一致
- **Done 标志**: 检查轨迹是否有 done 标志
- **奖励序列**: 检查奖励序列的合理性

```python
# 所有字段应该有相同的长度
len(states) == len(actions) == len(rewards) == len(values) == len(log_probs) == len(dones)
```

## 验证模式

### 严格模式 (`strict_validation=True`)

- **行为**: 发现错误时抛出异常，跳过无效轨迹
- **适用场景**: 开发阶段、调试、确保数据质量
- **优点**: 立即发现问题，防止无效数据进入训练
- **缺点**: 可能因为个别错误导致大量数据被丢弃

```python
collector = DataCollector(
    validate_data=True,
    strict_validation=True,  # 严格模式
)
```

### 非严格模式 (`strict_validation=False`)

- **行为**: 发现错误时只警告，继续处理轨迹
- **适用场景**: 生产环境、大规模训练
- **优点**: 不会因为个别错误导致数据丢失
- **缺点**: 可能允许一些无效数据进入训练

```python
collector = DataCollector(
    validate_data=True,
    strict_validation=False,  # 非严格模式（默认）
)
```

## 验证统计

数据收集器会返回验证统计信息：

```python
stats = collector.collect(model_state_dict)

# 统计信息包含验证结果
if 'validation' in stats:
    print(f"有效轨迹数: {stats['validation']['valid_trajectories']}")
    print(f"无效轨迹数: {stats['validation']['invalid_trajectories']}")
    print(f"有效率: {stats['validation']['valid_rate']:.2%}")
    print(f"错误数: {stats['validation']['num_errors']}")
    print(f"警告数: {stats['validation']['num_warnings']}")
```

## 直接使用验证器

也可以直接使用 `DataValidator` 验证数据：

```python
from scai.utils.data_validator import DataValidator

# 创建验证器
validator = DataValidator(
    state_shape=(64, 4, 9),
    action_space_size=434,
    strict_mode=False,
)

# 验证单个轨迹
trajectory = {
    'states': [...],
    'actions': [...],
    'rewards': [...],
    'values': [...],
    'log_probs': [...],
    'dones': [...],
    'action_masks': [...],
}

is_valid, errors = validator.validate_trajectory(trajectory, trajectory_id="traj_1")

if not is_valid:
    print(f"轨迹无效，错误数: {len(errors)}")
    for error in errors:
        print(f"  - {error}")

# 验证一批轨迹
trajectories = [trajectory1, trajectory2, ...]
valid_flags, error_lists = validator.validate_batch(trajectories)

# 获取验证统计
stats = validator.get_validation_stats()
validator.print_stats()
```

## 常见错误和解决方案

### 错误 1: 状态形状不匹配

**错误信息**: `State shape (64, 4, 9) != expected (64, 4, 9)`

**可能原因**:
- 特征张量计算错误
- 状态编码问题

**解决方案**:
- 检查 `state_to_tensor` 函数的输出
- 验证特征张量的形状

### 错误 2: 动作超出范围

**错误信息**: `Action 500 out of range [0, 434)`

**可能原因**:
- 动作采样错误
- 动作索引计算错误

**解决方案**:
- 检查动作采样逻辑
- 验证动作索引计算

### 错误 3: 动作不被掩码允许

**错误信息**: `Action 123 is not allowed by action mask`

**可能原因**:
- 动作掩码生成错误
- 动作采样时未正确应用掩码

**解决方案**:
- 检查动作掩码生成逻辑
- 确保采样时应用了掩码

### 错误 4: 状态包含 NaN

**错误信息**: `State contains NaN values`

**可能原因**:
- 特征计算中的除零错误
- 未初始化的数组

**解决方案**:
- 检查特征计算逻辑
- 添加数值稳定性检查

### 错误 5: 奖励为 NaN

**错误信息**: `Reward is NaN`

**可能原因**:
- 奖励计算错误
- 除零错误

**解决方案**:
- 检查奖励计算逻辑
- 添加数值稳定性检查

## 最佳实践

### 1. 开发阶段使用严格模式

在开发和调试阶段，使用严格模式可以立即发现问题：

```yaml
selfplay:
  validate_data: true
  strict_validation: true  # 严格模式
```

### 2. 生产环境使用非严格模式

在生产环境和大规模训练中，使用非严格模式避免数据丢失：

```yaml
selfplay:
  validate_data: true
  strict_validation: false  # 非严格模式
```

### 3. 定期检查验证统计

定期检查验证统计，监控数据质量：

```python
stats = collector.collect(model_state_dict)

if 'validation' in stats:
    valid_rate = stats['validation']['valid_rate']
    if valid_rate < 0.95:  # 有效率低于 95%
        print(f"Warning: Low validation rate: {valid_rate:.2%}")
```

### 4. 记录验证结果

将验证结果记录到日志中：

```python
from scai.utils.logger import get_logger

logger = get_logger()
stats = collector.collect(model_state_dict)

if 'validation' in stats:
    logger.info(
        "Data collection completed",
        validation_stats=stats['validation'],
    )
```

### 5. 禁用验证以提高性能

如果数据质量已经稳定，可以禁用验证以提高性能：

```yaml
selfplay:
  validate_data: false  # 禁用验证
```

## 性能影响

数据验证会带来一定的性能开销：

- **状态验证**: ~0.1ms per step
- **动作验证**: ~0.01ms per step
- **完整验证**: ~0.5ms per trajectory

对于大规模训练，验证开销通常可以忽略不计（< 1%）。

## 总结

数据验证系统提供了完整的数据质量保证：

- ✅ 全面的验证检查
- ✅ 灵活的模式选择
- ✅ 详细的统计信息
- ✅ 易于集成和使用
- ✅ 可配置的性能开销

通过合理使用数据验证系统，可以确保训练数据的质量，提高训练效果。

