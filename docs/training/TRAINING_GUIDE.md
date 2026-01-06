# 训练完整指南

## 快速开始

### 步骤 1: 环境准备（10-30分钟）

#### 1.1 安装 Python 依赖

```bash
cd python
pip install -r requirements.txt
```

**必需依赖**:
- `torch>=2.0.0` - PyTorch 深度学习框架
- `numpy>=1.24.0` - 数值计算
- `ray>=2.0.0` - 分布式训练框架
- `pyyaml>=6.0` - YAML 配置文件解析
- `tqdm>=4.65.0` - 进度条

#### 1.2 编译 Rust 扩展模块

```bash
# 安装 maturin（如果还没有）
pip install maturin

# 编译并安装 Rust 扩展
cd rust
maturin develop

# 返回 Python 目录
cd ../python
```

#### 1.3 验证安装

```python
# 测试导入
python -c "import scai_engine; import scai; from scai.models import DualResNet; print('✅ All imports successful')"
```

如果出现错误，检查：
- Rust 扩展是否编译成功
- Python 路径是否正确
- 依赖是否完整安装

---

### 步骤 2: 配置检查（5分钟）

编辑 `config.yaml` 文件，检查关键配置：

```yaml
# 模型配置
model:
  architecture: dual_resnet
  num_blocks: 10
  channels: 256

# 训练配置
training:
  learning_rate: 0.0001
  batch_size: 512
  num_iterations: 100000

# 自对弈配置
selfplay:
  num_workers: 100
  num_games_per_worker: 10

# 评估配置
evaluation:
  eval_interval: 10
  num_eval_games: 100
```

---

### 步骤 3: 启动训练

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

---

## 训练流程详解

训练脚本会自动执行以下循环：

### 1. 数据收集阶段

使用 Ray 分布式收集自对弈轨迹：

```python
# 并行收集轨迹
trajectories = collect_trajectories_parallel(
    workers,
    model_state_dict,
)
```

**配置参数**:
- `num_workers`: Worker 数量（默认 100）
- `num_games_per_worker`: 每个 Worker 运行的游戏数量（默认 10）
- `use_oracle`: 是否使用 Oracle 特征（默认 True）

### 2. 策略更新阶段

使用 PPO 算法更新模型：

```python
# PPO 更新
loss = ppo.update(
    states,
    actions,
    rewards,
    old_log_probs,
    advantages,
)
```

**配置参数**:
- `learning_rate`: 学习率（默认 0.0001）
- `batch_size`: 批次大小（默认 512）
- `ppo_epochs`: PPO 更新轮数（默认 4）
- `clip_epsilon`: PPO 裁剪参数（默认 0.2）

### 3. 模型评估阶段

定期评估模型性能（Elo 评分）：

```python
# 评估模型
elo_rating = evaluator.evaluate_model(
    model,
    model_id=iteration,
)
```

**配置参数**:
- `eval_interval`: 评估间隔（默认 10 次迭代）
- `num_eval_games`: 评估游戏数量（默认 100）
- `elo_threshold`: Elo 阈值（默认 0.55）

### 4. Checkpoint 保存阶段

定期保存模型和优化器状态：

```python
# 保存 Checkpoint
checkpoint.save(
    model,
    optimizer,
    iteration,
    metrics,
)
```

**配置参数**:
- `save_interval`: 保存间隔（默认 100 次迭代）
- `checkpoint_dir`: Checkpoint 目录（默认 `./checkpoints`）
- `keep_last_n`: 保留最近 N 个 Checkpoint（默认 10）

---

## 训练配置详解

### 模型配置

```yaml
model:
  architecture: dual_resnet      # 模型架构
  num_blocks: 10                 # ResNet 块数量
  channels: 256                  # 通道数
  policy_head_size: 512          # Policy Head 大小
  value_head_size: 512           # Value Head 大小
```

### 训练配置

```yaml
training:
  learning_rate: 0.0001          # 学习率
  batch_size: 512                # 批次大小
  num_iterations: 100000         # 总迭代次数
  ppo_epochs: 4                  # PPO 更新轮数
  clip_epsilon: 0.2              # PPO 裁剪参数
  value_loss_coef: 0.5           # Value Loss 系数
  entropy_coef: 0.01             # Entropy 系数
  max_grad_norm: 0.5             # 梯度裁剪
```

### 自对弈配置

```yaml
selfplay:
  num_workers: 100               # Worker 数量
  num_games_per_worker: 10       # 每个 Worker 游戏数
  use_oracle: true               # 使用 Oracle 特征
  collect_interval: 1            # 收集间隔
```

### 评估配置

```yaml
evaluation:
  eval_interval: 10              # 评估间隔
  num_eval_games: 100            # 评估游戏数
  elo_threshold: 0.55            # Elo 阈值
  use_opponent_pool: true        # 使用对手池
```

### 奖励函数配置

```yaml
reward_shaping:
  ready_reward: 0.1              # 听牌奖励
  hu_reward: 1.0                 # 胡牌奖励
  flower_pig_penalty: -5.0       # 花猪惩罚
  final_score_weight: 1.0        # 最终得分权重
  shanten_reward_weight: 0.05    # 向听数奖励权重（初期训练）
  use_shanten_reward: true       # 启用向听数奖励
```

---

## 高级功能

### 课程学习

详见 [课程学习指南](./CURRICULUM_LEARNING.md)

### 对手池系统

详见 [对手池指南](../features/OPPONENT_POOL.md)

### 数据增强

详见 [数据增强指南](../features/DATA_AUGMENTATION.md)

### 搜索增强推理

详见 [搜索增强推理指南](../features/SEARCH_ENHANCED.md)

---

## 监控和调试

### 日志系统

训练过程会生成详细的日志：

```python
# 日志文件位置
logs/
  ├── training.log          # 训练日志
  ├── metrics.json          # 指标日志
  └── errors.log            # 错误日志
```

### 指标监控

关键指标：
- **Loss**: Policy Loss, Value Loss, Total Loss
- **Reward**: 平均奖励、最终得分
- **Performance**: 胜率、听牌率、Elo 评分
- **Training**: 学习率、梯度范数

### 常见问题

#### 1. 训练不收敛

**可能原因**:
- 学习率过高或过低
- 批次大小不合适
- 奖励函数设计不合理

**解决方案**:
- 调整学习率（尝试 0.0001, 0.0005, 0.001）
- 增加批次大小
- 检查奖励函数权重

#### 2. 内存不足

**可能原因**:
- Worker 数量过多
- 批次大小过大
- 缓冲区大小过大

**解决方案**:
- 减少 Worker 数量
- 减小批次大小
- 减小缓冲区大小

#### 3. 训练速度慢

**可能原因**:
- Worker 数量过少
- 设备性能不足
- 网络架构过大

**解决方案**:
- 增加 Worker 数量
- 使用 GPU 训练
- 减小网络架构

---

## 最佳实践

### 1. 渐进式训练

从简单配置开始，逐步增加复杂度：
- 先使用小模型训练
- 逐步增加模型大小
- 逐步增加训练规模

### 2. 定期评估

定期评估模型性能，及时发现问题：
- 每 10 次迭代评估一次
- 保存最佳模型
- 记录训练曲线

### 3. 检查点管理

定期保存检查点，防止训练中断：
- 每 100 次迭代保存一次
- 保留最近 10 个检查点
- 定期备份重要检查点

### 4. 监控资源

监控系统资源使用情况：
- CPU/GPU 使用率
- 内存使用情况
- 磁盘空间

---

## 总结

训练系统提供了完整的训练流程和丰富的配置选项。通过合理配置和监控，可以高效地训练出高性能的麻将AI。

更多详细信息，请参考：
- [课程学习指南](./CURRICULUM_LEARNING.md)
- [检查点管理指南](./CHECKPOINT.md)
- [评估指南](./EVALUATION.md)
- [日志系统指南](./LOGGING.md)

