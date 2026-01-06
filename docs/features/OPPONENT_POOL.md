# 对手池系统使用指南 (Opponent Pool Guide)

## 概述

对手池系统是达到人类顶级水平的关键组件，模仿 AlphaZero 和 Suphx 的核心特性。它通过管理历史模型，实现多样化的对手策略，防止过拟合，提升训练稳定性。

## 为什么需要对手池？

### 问题：当前系统的局限性

当前系统只有**当前模型自对弈**：
```python
# 所有玩家使用同一模型
model_state_dict = model.state_dict()
trajectories = collect_trajectories_parallel(workers, model_state_dict)
```

**问题**:
- ❌ 容易过拟合：模型只学习对抗自己的策略
- ❌ 策略单一：所有对手使用相同策略
- ❌ 训练不稳定：可能退化到局部最优

### 解决方案：对手池系统

对手池系统提供：
- ✅ **策略多样性**: 不同历史版本代表不同策略风格
- ✅ **防止过拟合**: 与历史版本对弈，学习更通用的策略
- ✅ **训练稳定性**: 防止模型退化，保持策略多样性

---

## 快速开始

### 基本使用

```python
from scai.selfplay.opponent_pool import OpponentPool
from scai.selfplay.collector import DataCollector

# 创建对手池
opponent_pool = OpponentPool(
    checkpoint_dir='./checkpoints',
    pool_size=10,  # 保留最近10个版本
    selection_strategy='uniform',  # 均匀随机选择
)

# 启用对手池
collector = DataCollector(...)
collector.enable_opponent_pool(
    checkpoint_dir='./checkpoints',
    pool_size=10,
    selection_strategy='uniform',
)

# 添加模型到池中
collector.add_model_to_pool(
    model=model,
    iteration=100,
    elo_rating=1500.0,
)

# 收集数据（自动使用对手池）
stats = collector.collect(model_state_dict, current_iteration=100)
```

---

## 选择策略

### 1. 均匀随机（uniform）

所有模型被选中的概率相等。

```python
opponent_pool = OpponentPool(selection_strategy='uniform')
```

**适用场景**: 默认策略，简单有效

### 2. 按 Elo 加权（weighted_by_elo）

Elo 评分越高的模型，被选中概率越大。

```python
opponent_pool = OpponentPool(selection_strategy='weighted_by_elo')
```

**适用场景**: 希望更多与强对手对弈

### 3. 最近优先（recent）

优先选择最近的模型。

```python
opponent_pool = OpponentPool(selection_strategy='recent')
```

**适用场景**: 希望更多与最新版本对弈

### 4. 多样性选择（diverse）

选择 Elo 差异较大的模型，确保策略多样性。

```python
opponent_pool = OpponentPool(
    selection_strategy='diverse',
    min_elo_diff=100.0,  # 最小 Elo 差异
)
```

**适用场景**: 希望训练模型应对各种不同强度的对手

---

## 集成到训练流程

### 方法 1: 在 DataCollector 中启用（推荐）

```python
# 在训练脚本中
collector = DataCollector(...)

# 启用对手池
collector.enable_opponent_pool(
    checkpoint_dir=checkpoint_dir,
    pool_size=10,
    selection_strategy='uniform',
)

# 在训练循环中
for iteration in range(num_iterations):
    # 添加当前模型到池中
    elo_rating = evaluator.get_model_elo(f"iteration_{iteration}")
    collector.add_model_to_pool(
        model=model,
        iteration=iteration,
        elo_rating=elo_rating,
    )
    
    # 收集数据（自动使用对手池）
    stats = collector.collect(
        model.state_dict(),
        current_iteration=iteration,
    )
```

### 方法 2: 直接使用 OpponentPool

```python
from scai.selfplay.opponent_pool import OpponentPool

# 创建对手池
opponent_pool = OpponentPool(
    checkpoint_dir='./checkpoints',
    pool_size=10,
)

# 从 Checkpoint 加载历史模型
opponent_pool.load_from_checkpoints(max_models=10)

# 采样对手
opponents = opponent_pool.sample_opponents(num_opponents=3)

# 获取模型状态字典
opponent_state_dicts = [
    opponent_pool.get_model_state_dict(opp) for opp in opponents
]

# 在 SelfPlayWorker 中使用不同的模型
# （需要修改 worker 以支持多模型）
```

---

## 配置

在 `config.yaml` 中配置：

```yaml
selfplay:
  # 对手池配置
  opponent_pool:
    enabled: true              # 是否启用对手池
    pool_size: 10             # 池大小
    selection_strategy: uniform  # 选择策略
    min_elo_diff: 100.0       # 最小 Elo 差异（用于多样性选择）
    auto_load: true           # 自动从 Checkpoint 加载
    max_models_to_load: 10    # 最大加载数量
```

---

## 最佳实践

### 1. 池大小选择

- **小池（5-10）**: 快速迭代，适合早期训练
- **中池（10-20）**: 平衡多样性和效率，适合中期训练
- **大池（20+）**: 最大多样性，适合后期训练

### 2. 选择策略选择

- **早期训练**: 使用 `uniform` 或 `recent`，快速迭代
- **中期训练**: 使用 `weighted_by_elo`，更多与强对手对弈
- **后期训练**: 使用 `diverse`，确保策略多样性

### 3. Elo 更新

定期更新对手的 Elo 评分：

```python
# 获取所有模型的 Elo 评分
elo_ratings = {}
for model_id in evaluator.elo.get_ratings():
    elo_ratings[model_id] = evaluator.get_model_elo(model_id)

# 更新对手池
opponent_pool.update_elo_ratings(elo_ratings)
```

### 4. 池管理

定期清理和更新池：

```python
# 移除低 Elo 的模型
opponent_pool.load_from_checkpoints(
    max_models=10,
    min_elo=1200.0,  # 只保留 Elo >= 1200 的模型
)
```

---

## 性能考虑

### 内存使用

- 每个模型状态字典约 10-50 MB（取决于模型大小）
- 池大小 10 约占用 100-500 MB
- 建议根据内存情况调整池大小

### 计算开销

- 模型加载：首次加载需要时间，后续使用缓存
- 采样开销：可忽略不计
- 总体影响：< 1% 的训练时间

---

## 故障排查

### 问题 1: 对手池为空

**原因**: 没有模型添加到池中

**解决方案**:
```python
# 手动添加模型
opponent_pool.add_model(model, iteration=100, elo_rating=1500.0)

# 或从 Checkpoint 加载
opponent_pool.load_from_checkpoints()
```

### 问题 2: 采样失败

**原因**: 池中没有足够的模型

**解决方案**:
```python
# 检查池大小
stats = opponent_pool.get_stats()
print(f"Pool size: {stats['pool_size']}")

# 如果池太小，添加更多模型
if stats['pool_size'] < 3:
    opponent_pool.load_from_checkpoints()
```

### 问题 3: 模型加载失败

**原因**: Checkpoint 文件损坏或路径错误

**解决方案**:
```python
# 验证 Checkpoint
from scai.utils.checkpoint import CheckpointManager
manager = CheckpointManager('./checkpoints')
verification = manager.verify_checkpoint(checkpoint_path)
print(verification)
```

---

## 统计信息

获取对手池统计信息：

```python
stats = opponent_pool.get_stats()
print(f"池大小: {stats['pool_size']}")
print(f"平均 Elo: {stats['avg_elo']:.2f}")
print(f"最低 Elo: {stats['min_elo']:.2f}")
print(f"最高 Elo: {stats['max_elo']:.2f}")
print(f"总添加数: {stats['total_models_added']}")
print(f"总选择数: {stats['total_selections']}")
```

---

## 总结

对手池系统是达到人类顶级水平的关键组件：

- ✅ **策略多样性**: 不同历史版本提供不同策略
- ✅ **防止过拟合**: 与历史版本对弈，学习通用策略
- ✅ **训练稳定性**: 防止模型退化
- ✅ **易于使用**: 简单的 API，易于集成

**建议**: 在训练开始时就启用对手池系统，这是达到顶级水平的关键。

