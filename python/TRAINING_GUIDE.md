# 训练指南 (Training Guide)

## 快速开始

### 1. 环境准备

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 构建 Rust 扩展（如果尚未构建）
cd ../rust
maturin develop
cd ../python
```

### 2. 配置训练参数

编辑 `config.yaml` 文件，调整以下关键参数：

- **模型配置**: 网络架构、层数、通道数
- **训练配置**: 学习率、批次大小、迭代次数
- **自对弈配置**: Worker 数量、每 Worker 游戏数
- **评估配置**: 评估间隔、评估游戏数

### 3. 启动训练

```bash
# 从头开始训练
python train.py --config config.yaml

# 从 Checkpoint 恢复训练
python train.py --config config.yaml --resume checkpoints/latest.pt

# 仅评估模型（不训练）
python train.py --config config.yaml --eval-only --resume checkpoints/latest.pt

# 指定设备（CPU/GPU）
python train.py --config config.yaml --device cuda
```

## 训练流程

训练脚本会自动执行以下循环：

1. **数据收集**: 使用 Ray 分布式收集自对弈轨迹
2. **策略更新**: 使用 PPO 算法更新模型
3. **模型评估**: 定期评估模型性能（Elo 评分）
4. **Checkpoint 保存**: 定期保存模型和优化器状态

## 输出文件

- **Checkpoints**: `./checkpoints/checkpoint_iter_*.pt`
- **日志文件**: `training_YYYYMMDD_HHMMSS.log`
- **最新模型**: `./checkpoints/latest.pt`

## 配置说明

### 模型配置

```yaml
model:
  input_channels: 64          # 特征平面数
  action_space_size: 434      # 动作空间大小
  backbone:
    num_blocks: 20            # ResNet 残差块数量
    channels: 128             # 基础通道数
```

### 训练配置

```yaml
training:
  learning_rate: 3e-4         # 学习率
  batch_size: 4096           # 批次大小
  num_epochs: 10             # 每次更新的轮数
  num_iterations: 1000       # 训练迭代次数
  collect_interval: 1        # 每 N 次迭代收集一次数据
  save_interval: 100         # 每 N 次迭代保存一次
```

### 自对弈配置

```yaml
selfplay:
  num_workers: 100           # Ray Worker 数量
  games_per_worker: 10       # 每个 Worker 运行的游戏数量
  oracle_enabled: true       # 是否启用 Oracle 特征
```

### 评估配置

```yaml
evaluation:
  elo_threshold: 0.55        # Elo 胜率阈值
  num_eval_games: 100        # 评估时运行的游戏数量
  eval_interval: 100         # 每 N 次迭代评估一次
```

## 常见问题

### Q: Ray 初始化失败

**A**: 确保已安装 Ray：
```bash
pip install ray[default]
```

### Q: 内存不足

**A**: 减少以下参数：
- `batch_size`: 减小批次大小
- `num_workers`: 减少 Worker 数量
- `buffer_capacity`: 减小缓冲区容量

### Q: 训练速度慢

**A**: 
- 使用 GPU: `--device cuda`
- 增加 `num_workers` 以并行收集更多数据
- 减少 `num_eval_games` 以加快评估速度

### Q: 如何监控训练进度

**A**: 
- 查看日志文件: `tail -f training_*.log`
- 检查 Checkpoint 目录: `ls -lh checkpoints/`
- 使用 TensorBoard（如果配置了）: `tensorboard --logdir=./logs`

## 高级功能

### 对抗训练

在 `config.yaml` 中启用：

```yaml
adversarial:
  enabled: true
  frequency: 10
  scenarios_per_iteration: 5
```

### LLM 教练

在 `config.yaml` 中启用课程学习（文档生成模式）：

```yaml
curriculum_learning:
  enabled: true
  initial_stage: basic
  llm_coach_frequency: 100  # 每 N 次迭代生成一次文档
  document_output_dir: ./coach_documents
```

系统会自动生成分析文档，您可以手动将这些文档提交给大模型进行分析。

### 超参数搜索

在 `config.yaml` 中启用：

```yaml
hyperparameter_search:
  enabled: true
  method: bayesian  # grid/random/bayesian
  num_trials: 20
```

## 性能优化建议

1. **使用 GPU**: 训练速度可提升 10-100 倍
2. **增加 Worker**: 更多 Worker 可并行收集更多数据
3. **调整批次大小**: 根据 GPU 内存调整 `batch_size`
4. **减少评估频率**: 增加 `eval_interval` 以加快训练速度

## 下一步

训练完成后，可以：

1. **评估模型**: 使用 `--eval-only` 模式评估模型性能
2. **模型对比**: 使用 `Evaluator.compare_models()` 对比不同版本
3. **部署模型**: 将最佳模型导出用于推理
4. **继续训练**: 从 Checkpoint 恢复，继续训练以提升性能

