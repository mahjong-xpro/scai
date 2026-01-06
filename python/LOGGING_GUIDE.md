# 日志系统使用指南 (Logging System Guide)

## 概述

项目实现了完整的日志系统，支持多级别日志记录、结构化输出、训练指标追踪等功能。

## 快速开始

### 基本使用

```python
from scai.utils.logger import get_logger, get_metrics_logger

# 获取日志记录器
logger = get_logger(
    log_dir='./logs',
    log_level='INFO',
    use_json=False,
    console_output=True,
)

# 记录日志
logger.info("训练开始")
logger.debug("调试信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 在训练脚本中使用

训练脚本 (`train.py`) 已自动集成日志系统，无需额外配置。日志系统会：

1. **自动记录训练过程**：每次迭代的训练步骤、数据收集、评估结果
2. **记录训练指标**：损失值、评估结果、Elo 评分等
3. **保存到文件**：所有日志保存到 `logs/` 目录

## 配置

在 `config.yaml` 中配置日志系统：

```yaml
logging:
  log_dir: ./logs              # 日志文件保存目录
  log_level: INFO              # 日志级别
  use_json: false              # 是否使用 JSON 格式
  console_output: true         # 是否输出到控制台
  metrics_logging: true        # 是否记录训练指标
```

### 日志级别

- `DEBUG`: 详细的调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

## 功能特性

### 1. 多级别日志

```python
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告")
logger.error("错误")
logger.critical("严重错误")
```

### 2. 结构化日志

#### 文本格式（默认）

```
2024-01-01 12:00:00 - scai.training - INFO - Training step 100 (iteration=100, policy_loss=0.5, value_loss=0.3)
```

#### JSON 格式

在配置中设置 `use_json: true`：

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "level": "INFO",
  "logger": "scai.training",
  "message": "Training step 100",
  "iteration": 100,
  "policy_loss": 0.5,
  "value_loss": 0.3
}
```

### 3. 训练指标记录

```python
from scai.utils.logger import get_metrics_logger

metrics_logger = get_metrics_logger(log_dir='./logs')

# 记录损失
metrics_logger.log_loss(
    iteration=100,
    policy_loss=0.5,
    value_loss=0.3,
    entropy_loss=0.1,
    total_loss=0.9,
)

# 记录评估结果
metrics_logger.log_evaluation(
    iteration=100,
    win_rate=0.6,
    avg_score=10.5,
    elo_rating=1500.0,
)

# 保存指标
metrics_logger.save()
```

### 4. 专用日志方法

日志系统提供了专用的方法来记录训练过程中的关键事件：

```python
# 记录训练步骤
logger.log_training_step(iteration=100, losses={'policy_loss': 0.5, 'value_loss': 0.3})

# 记录评估结果
logger.log_evaluation(iteration=100, results={'win_rate': 0.6, 'avg_score': 10.5})

# 记录数据收集统计
logger.log_data_collection(iteration=100, stats={'num_trajectories': 1000, 'total_steps': 5000})

# 记录 Checkpoint 保存
logger.log_checkpoint(iteration=100, checkpoint_path='./checkpoints/checkpoint_iter_100.pt')

# 记录性能指标
logger.log_performance(metric='games_per_second', value=10.5, unit=' games/s')
```

## 日志文件

日志系统会创建以下文件：

1. **训练日志**: `logs/training_YYYYMMDD_HHMMSS.log`
   - 包含所有级别的日志（DEBUG 及以上）
   - 记录完整的训练过程

2. **错误日志**: `logs/errors_YYYYMMDD_HHMMSS.log`
   - 仅包含 ERROR 和 CRITICAL 级别的日志
   - 便于快速定位问题

3. **指标文件**: `logs/metrics_YYYYMMDD_HHMMSS.json`
   - JSON 格式的训练指标
   - 包含损失、评估结果、性能指标等
   - 便于后续分析和可视化

## 日志文件示例

### 训练日志 (training_*.log)

```
2024-01-01 12:00:00 - scai.training - INFO - Loaded config from config.yaml
2024-01-01 12:00:01 - scai.training - INFO - Using device: cuda
2024-01-01 12:00:02 - scai.training - INFO - Starting training loop...
2024-01-01 12:00:03 - scai.training - INFO - Training step 1 (iteration=1, policy_loss=0.5, value_loss=0.3)
2024-01-01 12:00:10 - scai.training - INFO - Evaluation at iteration 100 (iteration=100, win_rate=0.6, avg_score=10.5)
```

### 指标文件 (metrics_*.json)

```json
{
  "losses": [
    {
      "iteration": 1,
      "policy_loss": 0.5,
      "value_loss": 0.3,
      "entropy_loss": 0.1,
      "total_loss": 0.9,
      "timestamp": "2024-01-01T12:00:03"
    }
  ],
  "evaluations": [
    {
      "iteration": 100,
      "win_rate": 0.6,
      "avg_score": 10.5,
      "elo_rating": 1500.0,
      "timestamp": "2024-01-01T12:00:10"
    }
  ],
  "performance": []
}
```

## 最佳实践

### 1. 选择合适的日志级别

- **DEBUG**: 仅在调试时使用，记录详细的执行流程
- **INFO**: 记录关键操作和状态变化（推荐用于训练过程）
- **WARNING**: 记录可能的问题，但不影响训练
- **ERROR**: 记录错误，但程序可以继续运行
- **CRITICAL**: 记录严重错误，可能导致程序终止

### 2. 使用结构化日志

对于需要后续分析的数据，使用结构化日志方法：

```python
# 推荐：使用专用方法
logger.log_training_step(iteration=100, losses={'policy_loss': 0.5})

# 不推荐：使用普通日志
logger.info(f"Training step 100: losses={losses}")
```

### 3. 定期保存指标

在训练循环中定期保存指标，避免数据丢失：

```python
if (iteration + 1) % save_interval == 0:
    metrics_logger.save()
```

### 4. 使用 JSON 格式进行数据分析

如果需要后续分析，启用 JSON 格式：

```yaml
logging:
  use_json: true
```

然后可以使用 Python 脚本分析日志：

```python
import json

with open('logs/metrics_20240101_120000.json', 'r') as f:
    metrics = json.load(f)
    
# 分析损失趋势
losses = [m['total_loss'] for m in metrics['losses']]
```

## 故障排查

### 问题：日志文件未创建

**解决方案**：
- 检查 `log_dir` 目录是否存在写权限
- 确认日志系统已正确初始化

### 问题：日志过多，文件过大

**解决方案**：
- 提高日志级别（如从 DEBUG 改为 INFO）
- 减少日志输出频率
- 定期清理旧日志文件

### 问题：控制台输出过多

**解决方案**：
- 设置 `console_output: false`
- 或提高控制台日志级别

## 与 TensorBoard 集成

可以将指标文件转换为 TensorBoard 格式：

```python
from scai.utils.logger import MetricsLogger
import json

metrics_logger = MetricsLogger()
metrics_logger.load('logs/metrics_20240101_120000.json')

# 转换为 TensorBoard 格式（需要实现转换函数）
# convert_to_tensorboard(metrics_logger.metrics)
```

## 总结

日志系统提供了完整的训练过程记录功能，包括：

- ✅ 多级别日志支持
- ✅ 文件和控制台双重输出
- ✅ 结构化日志（JSON 格式）
- ✅ 训练指标自动记录
- ✅ 错误追踪
- ✅ 易于配置和使用

通过合理使用日志系统，可以更好地监控训练过程、分析模型性能、排查问题。

