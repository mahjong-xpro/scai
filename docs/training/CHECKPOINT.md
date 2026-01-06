# 检查点管理指南 (Checkpoint Management Guide)

## 概述

检查点系统允许您保存和恢复训练状态，包括模型参数、优化器状态、训练统计等信息。这对于长时间训练、恢复中断的训练、以及模型版本管理非常重要。

## 快速开始

### 基本使用

```python
from scai.training.trainer import Trainer
from scai.utils.checkpoint import CheckpointManager

# 在训练脚本中，检查点会自动保存
# 每 save_interval 次迭代保存一次（在 config.yaml 中配置）

# 手动保存
checkpoint_path = trainer.save_checkpoint(iteration=100)

# 加载检查点
checkpoint = trainer.load_checkpoint(checkpoint_path)
```

## 检查点内容

每个检查点包含以下信息：

1. **模型状态** (`model_state_dict`): 所有模型参数的完整状态
2. **优化器状态** (`optimizer_state_dict`): 优化器的状态（学习率、动量等）
3. **训练统计** (`training_stats`): 训练过程中的统计信息
   - `total_iterations`: 总迭代次数
   - `total_games`: 总游戏数
   - `total_steps`: 总步数
4. **元数据** (`metadata`): 额外的元数据（可选）
5. **时间戳** (`timestamp`): 保存时间
6. **迭代次数** (`iteration`): 当前迭代次数

## 保存检查点

### 自动保存

训练脚本会自动保存检查点：

```python
# 在 config.yaml 中配置
training:
  save_interval: 100  # 每 100 次迭代保存一次
```

### 手动保存

```python
# 使用 Trainer
checkpoint_path = trainer.save_checkpoint(iteration=100)

# 使用 CheckpointManager（更底层）
from scai.utils.checkpoint import CheckpointManager

manager = CheckpointManager(checkpoint_dir='./checkpoints')
checkpoint_path = manager.save_checkpoint(
    model=model,
    optimizer=optimizer,
    iteration=100,
    training_stats={'total_iterations': 100},
    metadata={'config': 'config.yaml'},
)
```

## 加载检查点

### 从训练脚本恢复

```bash
# 从指定检查点恢复
python train.py --config config.yaml --resume checkpoints/checkpoint_iter_100.pt

# 从最新检查点恢复（交互式）
python train.py --config config.yaml
# 脚本会提示是否从最新检查点恢复
```

### 在代码中加载

```python
# 使用 Trainer（推荐）
checkpoint = trainer.load_checkpoint('checkpoints/checkpoint_iter_100.pt')
iteration = checkpoint['iteration']
training_stats = checkpoint['training_stats']

# 使用 CheckpointManager
from scai.utils.checkpoint import CheckpointManager

manager = CheckpointManager(checkpoint_dir='./checkpoints')
checkpoint = manager.load_checkpoint(
    checkpoint_path='checkpoints/checkpoint_iter_100.pt',
    model=model,
    optimizer=optimizer,
    device='cuda',  # 或 'cpu'
)
```

### 非严格模式加载

如果模型架构发生了变化（例如添加了新层），可以使用非严格模式：

```python
checkpoint = trainer.load_checkpoint(
    'checkpoints/checkpoint_iter_100.pt',
    strict=False  # 只加载匹配的参数
)
```

## 检查点管理

### 列出所有检查点

```python
from scai.utils.checkpoint import CheckpointManager

manager = CheckpointManager(checkpoint_dir='./checkpoints')
checkpoints = manager.list_checkpoints()
# 返回: ['checkpoints/checkpoint_iter_100.pt', 'checkpoints/checkpoint_iter_200.pt', ...]
```

### 获取最新检查点

```python
latest = manager.get_latest_checkpoint()
# 返回: 'checkpoints/latest.pt' 或最新的 checkpoint_iter_*.pt
```

### 验证检查点

```python
# 验证检查点的完整性
verification = manager.verify_checkpoint('checkpoints/checkpoint_iter_100.pt')

print(verification)
# {
#     'exists': True,
#     'readable': True,
#     'has_required_fields': True,
#     'has_model_state': True,
#     'has_optimizer_state': True,
#     'has_training_stats': True,
#     'has_metadata': True,
#     'has_timestamp': True,
# }
```

## 文件结构

检查点保存在 `checkpoints/` 目录下：

```
checkpoints/
├── checkpoint_iter_100.pt    # 第 100 次迭代的检查点
├── checkpoint_iter_200.pt    # 第 200 次迭代的检查点
├── checkpoint_iter_300.pt    # 第 300 次迭代的检查点
└── latest.pt                  # 最新的检查点（自动更新）
```

## 最佳实践

### 1. 定期保存

在 `config.yaml` 中设置合理的保存间隔：

```yaml
training:
  save_interval: 100  # 根据训练速度调整
```

### 2. 保留重要检查点

定期备份重要的检查点（例如每 1000 次迭代）：

```bash
# 手动备份
cp checkpoints/checkpoint_iter_1000.pt backups/
```

### 3. 验证检查点

在加载检查点前，验证其完整性：

```python
verification = manager.verify_checkpoint(checkpoint_path)
if not all(verification.values()):
    print("警告: 检查点可能不完整")
```

### 4. 清理旧检查点

定期清理旧的检查点以节省空间：

```python
# 只保留最近的 N 个检查点
checkpoints = manager.list_checkpoints()
if len(checkpoints) > 10:
    for old_checkpoint in checkpoints[:-10]:
        os.remove(old_checkpoint)
```

### 5. 使用元数据

在保存检查点时添加有用的元数据：

```python
metadata = {
    'config_file': 'config.yaml',
    'git_commit': 'abc123',
    'training_time': '2024-01-01T12:00:00',
    'notes': 'Best model so far',
}
manager.save_checkpoint(
    model=model,
    optimizer=optimizer,
    iteration=100,
    metadata=metadata,
)
```

## 错误处理

检查点系统包含完整的错误处理：

### 文件不存在

```python
try:
    checkpoint = manager.load_checkpoint('nonexistent.pt')
except FileNotFoundError as e:
    print(f"检查点文件不存在: {e}")
```

### 字段缺失

```python
try:
    checkpoint = manager.load_checkpoint('corrupted.pt')
except KeyError as e:
    print(f"检查点缺少必需字段: {e}")
```

### 模型参数不匹配

```python
# 严格模式（默认）
try:
    checkpoint = manager.load_checkpoint('checkpoint.pt', model=model, strict=True)
except RuntimeError as e:
    print(f"模型参数不匹配: {e}")

# 非严格模式（只加载匹配的参数）
checkpoint = manager.load_checkpoint('checkpoint.pt', model=model, strict=False)
```

## 迁移学习场景

当模型架构发生变化时，可以使用非严格模式加载检查点：

```python
# 原始模型
old_model = DualResNet(num_blocks=20)

# 新模型（增加了层数）
new_model = DualResNet(num_blocks=25)

# 加载旧检查点（只加载匹配的参数）
checkpoint = manager.load_checkpoint(
    'checkpoints/checkpoint_iter_100.pt',
    model=new_model,
    strict=False,  # 非严格模式
)
```

## 检查点大小

检查点文件的大小取决于：

- **模型大小**: 参数量越大，文件越大
- **优化器状态**: Adam 等优化器会保存动量信息，增加文件大小
- **训练统计**: 通常很小，可以忽略

典型大小：
- 小型模型（< 1M 参数）: ~10-50 MB
- 中型模型（1-10M 参数）: ~50-500 MB
- 大型模型（> 10M 参数）: > 500 MB

## 性能考虑

### 保存频率

- **太频繁**: 影响训练速度，占用磁盘空间
- **太稀疏**: 可能丢失重要的训练状态

建议：根据训练速度调整，通常每 100-1000 次迭代保存一次。

### 磁盘空间

定期清理旧检查点：

```bash
# 只保留最新的 5 个检查点
ls -t checkpoints/checkpoint_iter_*.pt | tail -n +6 | xargs rm
```

## 故障排查

### 问题：检查点加载失败

**可能原因**:
1. 文件损坏
2. 模型架构不匹配
3. PyTorch 版本不兼容

**解决方案**:
```python
# 验证检查点
verification = manager.verify_checkpoint(checkpoint_path)
print(verification)

# 尝试非严格模式
checkpoint = manager.load_checkpoint(checkpoint_path, strict=False)
```

### 问题：训练统计未恢复

**解决方案**:
```python
# 确保在加载后更新训练统计
checkpoint = trainer.load_checkpoint(checkpoint_path)
trainer.training_stats = checkpoint.get('training_stats', {})
```

### 问题：优化器状态未恢复

**解决方案**:
```python
# 确保传递优化器参数
checkpoint = manager.load_checkpoint(
    checkpoint_path,
    model=model,
    optimizer=optimizer,  # 必须传递
)
```

## 总结

检查点系统提供了完整的训练状态保存和恢复功能：

- ✅ 完整保存：模型、优化器、统计、元数据
- ✅ 安全加载：错误处理、字段验证
- ✅ 灵活使用：严格/非严格模式
- ✅ 易于管理：列出、验证、获取最新
- ✅ 生产就绪：经过测试和验证

通过合理使用检查点系统，可以安全地进行长时间训练，并在需要时恢复训练状态。

