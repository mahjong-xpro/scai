# 评估系统使用指南 (Evaluation System Guide)

## 概述

评估系统提供了完整的模型评估功能，包括单模型评估、模型对比、Elo 评分等。这对于监控训练进度、选择最佳模型、以及比较不同版本的模型非常重要。

## 快速开始

### 基本使用

```python
from scai.training.evaluator import Evaluator
from scai.models import DualResNet

# 创建评估器
evaluator = Evaluator(
    checkpoint_dir='./checkpoints',
    elo_threshold=0.55,
    device='cpu',
)

# 创建模型
model = DualResNet()

# 评估模型
results = evaluator.evaluate_model(
    model=model,
    model_id="iteration_100",
    num_games=100,
)

print(f"胜率: {results['win_rate']:.2f}")
print(f"平均得分: {results['avg_score']:.2f}")
```

## 核心功能

### 1. 单模型评估

评估模型对随机玩家的表现：

```python
results = evaluator.evaluate_model(
    model=model,
    model_id="model_v1",
    num_games=100,
)

# 返回结果包含：
# - win_rate: 胜率 (0-1)
# - avg_score: 平均得分
# - wins: 获胜次数
# - total_games: 总游戏数
```

### 2. 模型对比

两个模型直接对弈：

```python
model_a = DualResNet()
model_b = DualResNet()

results = evaluator.compare_models(
    model_a=model_a,
    model_b=model_b,
    model_a_id="model_v1",
    model_b_id="model_v2",
    num_games=100,
)

# 返回结果包含：
# - model_a_win_rate: 模型 A 的胜率
# - model_b_win_rate: 模型 B 的胜率
# - model_a_avg_score: 模型 A 的平均得分
# - model_b_avg_score: 模型 B 的平均得分
# - model_a_elo: 模型 A 的 Elo 评分
# - model_b_elo: 模型 B 的 Elo 评分
```

### 3. Elo 评分系统

自动跟踪模型的 Elo 评分：

```python
# 获取模型的 Elo 评分
elo_rating = evaluator.get_model_elo("model_v1")
print(f"Elo 评分: {elo_rating:.2f}")

# 获取所有模型的评分
all_ratings = evaluator.elo.get_ratings()
print(all_ratings)

# 获取最佳模型
best_model_id = evaluator.get_best_model_id()
print(f"最佳模型: {best_model_id}")
```

### 4. 模型保留判断

根据胜率阈值判断是否保留模型：

```python
should_keep = evaluator.should_keep_model(win_rate=0.6)
# 如果 win_rate >= elo_threshold (默认 0.55)，返回 True
```

## Elo 评分系统

### 原理

Elo 评分系统用于评估模型的相对强度：

- **初始评分**: 1500.0（默认）
- **K 因子**: 32.0（默认，控制评分变化幅度）
- **期望得分**: 基于两个模型的评分差计算
- **评分更新**: 根据实际结果更新评分

### 期望得分计算

```python
from scai.training.evaluator import EloRating

elo = EloRating(initial_rating=1500.0, k_factor=32.0)

# 计算期望得分
expected = elo.expected_score(rating_a=1500.0, rating_b=1500.0)
# 相同评分时，期望得分 = 0.5

expected = elo.expected_score(rating_a=1600.0, rating_b=1500.0)
# 评分高 100 分时，期望得分 ≈ 0.64
```

### 评分更新

```python
# 模型 A 获胜
elo.update_rating("model_a", "model_b", actual_score=1.0)

# 模型 B 获胜
elo.update_rating("model_a", "model_b", actual_score=0.0)

# 平局（如果支持）
elo.update_rating("model_a", "model_b", actual_score=0.5)
```

## 评估流程

### 单模型评估流程

1. **初始化游戏引擎**: 创建新的游戏实例
2. **定缺阶段**: 所有玩家选择定缺花色
3. **游戏主循环**:
   - 玩家 0 使用模型进行推理
   - 其他玩家使用随机策略
   - 执行动作直到游戏结束
4. **结算**: 提取最终得分
5. **统计**: 计算胜率、平均得分等

### 模型对比流程

1. **初始化游戏引擎**: 创建新的游戏实例
2. **定缺阶段**: 所有玩家选择定缺花色
3. **游戏主循环**:
   - 玩家 0 和 2 使用模型 A
   - 玩家 1 和 3 使用模型 B
   - 执行动作直到游戏结束
4. **结算**: 计算两个模型的总得分
5. **更新 Elo**: 根据结果更新两个模型的 Elo 评分

## 配置

在 `config.yaml` 中配置评估参数：

```yaml
evaluation:
  elo_threshold: 0.55          # Elo 胜率阈值（55%）
  num_eval_games: 100         # 评估时运行的游戏数量
  eval_interval: 100         # 每 N 次迭代评估一次
```

## 在训练中使用

训练脚本会自动调用评估系统：

```python
# 在训练循环中
if (iteration + 1) % eval_interval == 0:
    model_id = f"iteration_{iteration + 1}"
    results = evaluator.evaluate_model(model, model_id, num_games=100)
    elo_rating = evaluator.get_model_elo(model_id)
    
    # 判断是否保留模型
    if evaluator.should_keep_model(results['win_rate']):
        print("模型表现良好，保留")
    else:
        print("模型表现不佳，考虑调整")
```

## 最佳实践

### 1. 评估游戏数量

- **太少**（< 50）: 结果不稳定，随机性大
- **适中**（50-200）: 平衡准确性和速度
- **太多**（> 500）: 评估时间过长

建议：根据训练阶段调整，初期可以少一些，后期需要更准确。

### 2. 评估频率

- **太频繁**: 影响训练速度
- **太稀疏**: 可能错过重要的模型改进

建议：每 50-200 次迭代评估一次。

### 3. Elo 阈值

- **太低**（< 0.5）: 可能保留表现不佳的模型
- **适中**（0.55-0.6）: 平衡严格性和灵活性
- **太高**（> 0.7）: 可能过于严格，难以保留模型

建议：根据训练阶段调整，初期可以低一些，后期提高。

### 4. 模型对比

定期对比不同版本的模型：

```python
# 对比当前模型和最佳模型
best_model_id = evaluator.get_best_model_id()
if best_model_id:
    results = evaluator.compare_models(
        model_a=current_model,
        model_b=best_model,
        model_a_id="current",
        model_b_id=best_model_id,
        num_games=100,
    )
    
    if results['model_a_win_rate'] > 0.5:
        print("当前模型优于最佳模型，更新最佳模型")
```

## 故障排查

### 问题：评估结果不稳定

**可能原因**:
1. 评估游戏数量太少
2. 模型策略随机性太大

**解决方案**:
- 增加 `num_games` 参数
- 使用确定性策略（`deterministic=True`）进行评估

### 问题：Elo 评分不更新

**可能原因**:
1. 只使用了 `evaluate_model`，没有使用 `compare_models`
2. Elo 评分系统未正确初始化

**解决方案**:
- `evaluate_model` 不会自动更新 Elo，需要使用 `compare_models`
- 或者手动更新 Elo 评分

### 问题：评估速度慢

**可能原因**:
1. 游戏数量太多
2. 模型推理速度慢
3. 游戏引擎性能问题

**解决方案**:
- 减少评估游戏数量
- 使用 GPU 加速模型推理
- 优化游戏引擎性能

## 高级功能

### 自定义评估策略

可以修改评估逻辑以使用不同的对手策略：

```python
# 在 _play_game_with_model 中修改
# 将随机策略替换为其他策略（例如固定策略、其他模型等）
```

### 批量评估

评估多个模型：

```python
models = {
    "model_v1": model_v1,
    "model_v2": model_v2,
    "model_v3": model_v3,
}

results = {}
for model_id, model in models.items():
    results[model_id] = evaluator.evaluate_model(
        model=model,
        model_id=model_id,
        num_games=100,
    )

# 找出最佳模型
best_model_id = max(results.items(), key=lambda x: x[1]['win_rate'])[0]
```

## 总结

评估系统提供了完整的模型评估功能：

- ✅ Elo 评分系统
- ✅ 单模型评估
- ✅ 模型对比
- ✅ 最佳模型选择
- ✅ 模型保留判断
- ✅ 游戏引擎集成

通过合理使用评估系统，可以有效地监控训练进度、选择最佳模型、以及比较不同版本的模型。

