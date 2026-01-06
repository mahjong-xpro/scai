# 开始训练指南 (Start Training Guide)

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

#### 2.1 检查配置文件

确认 `python/config.yaml` 存在且配置合理：

```yaml
# 关键配置项
model:
  input_channels: 64
  action_space_size: 434

training:
  num_iterations: 1000  # 测试时可以设置为 1-10
  batch_size: 4096
  learning_rate: 3e-4

selfplay:
  num_workers: 100  # 根据 CPU 核心数调整
  games_per_worker: 10
```

#### 2.2 创建必要目录

```bash
mkdir -p checkpoints logs
```

---

### 步骤 3: 小规模测试（5-10分钟）

#### 3.1 修改配置进行测试

在 `config.yaml` 中设置：

```yaml
training:
  num_iterations: 1  # 只运行 1 次迭代
  collect_interval: 1
  save_interval: 1

selfplay:
  num_workers: 2  # 使用少量 Worker
  games_per_worker: 1  # 每个 Worker 只运行 1 局
```

#### 3.2 运行测试

```bash
cd python
python train.py --config config.yaml
```

#### 3.3 检查输出

应该看到：
- ✅ 配置加载成功
- ✅ 模型创建成功
- ✅ Ray 初始化成功（如果使用）
- ✅ 数据收集开始
- ✅ 训练步骤执行
- ✅ 日志文件生成

如果出现错误，查看错误信息并参考故障排查部分。

---

### 步骤 4: 正式训练

#### 4.1 恢复正常配置

在 `config.yaml` 中设置正常参数：

```yaml
training:
  num_iterations: 1000  # 或更多
  collect_interval: 1
  save_interval: 100

selfplay:
  num_workers: 100  # 根据硬件调整
  games_per_worker: 10
```

#### 4.2 启动训练

```bash
python train.py --config config.yaml
```

#### 4.3 监控训练

- **日志文件**: `logs/training_*.log`
- **指标文件**: `logs/metrics_*.json`
- **Checkpoint**: `checkpoints/checkpoint_iter_*.pt`

---

## 故障排查

### 问题 1: 模块导入失败

**错误**: `ModuleNotFoundError: No module named 'scai_engine'`

**解决方案**:
```bash
cd rust
maturin develop
```

### 问题 2: Ray 初始化失败

**错误**: `Ray initialization failed`

**解决方案**:
```bash
pip install ray[default]
# 或
ray start --head
```

### 问题 3: CUDA 不可用

**错误**: `CUDA not available`

**解决方案**:
- 使用 CPU: `python train.py --config config.yaml --device cpu`
- 或安装 PyTorch CUDA 版本

### 问题 4: 内存不足

**错误**: `Out of memory`

**解决方案**:
- 减少 `batch_size`
- 减少 `num_workers`
- 减少 `buffer_capacity`

### 问题 5: 配置文件加载失败

**错误**: `No module named 'yaml'`

**解决方案**:
```bash
pip install pyyaml
```

---

## 训练参数调优建议

### 硬件配置建议

| 硬件 | 推荐配置 |
|------|---------|
| **CPU 训练** | `num_workers: 4-8`, `batch_size: 1024` |
| **GPU 训练** | `num_workers: 50-100`, `batch_size: 4096` |
| **多 GPU** | `num_workers: 100+`, `batch_size: 8192` |

### 训练阶段建议

#### 初期（前 100 次迭代）
- `num_workers: 10-20`
- `games_per_worker: 5`
- `batch_size: 2048`
- `learning_rate: 3e-4`

#### 中期（100-1000 次迭代）
- `num_workers: 50-100`
- `games_per_worker: 10`
- `batch_size: 4096`
- `learning_rate: 1e-4`

#### 后期（1000+ 次迭代）
- `num_workers: 100+`
- `games_per_worker: 10-20`
- `batch_size: 4096-8192`
- `learning_rate: 5e-5`

---

## 训练监控

### 关键指标

1. **训练损失**
   - `policy_loss`: 策略损失
   - `value_loss`: 价值损失
   - `entropy_loss`: 熵损失（鼓励探索）

2. **评估指标**
   - `win_rate`: 胜率
   - `avg_score`: 平均得分
   - `elo_rating`: Elo 评分

3. **数据质量**
   - `valid_rate`: 数据有效率
   - `num_errors`: 验证错误数

### 查看日志

```bash
# 实时查看训练日志
tail -f logs/training_*.log

# 查看错误日志
tail -f logs/errors_*.log

# 查看指标
cat logs/metrics_*.json | jq
```

---

## 恢复训练

### 从 Checkpoint 恢复

```bash
python train.py --config config.yaml --resume checkpoints/latest.pt
```

### 从指定迭代恢复

```bash
python train.py --config config.yaml --resume checkpoints/checkpoint_iter_100.pt
```

---

## 性能优化

### 提高数据收集速度

1. 增加 `num_workers`
2. 使用更多 CPU 核心
3. 优化 Rust 代码（已优化）

### 提高训练速度

1. 使用 GPU
2. 增加 `batch_size`（如果内存允许）
3. 减少 `num_epochs`（如果收敛快）

### 减少内存使用

1. 减少 `buffer_capacity`
2. 减少 `batch_size`
3. 减少 `num_workers`

---

## 总结

**项目已就绪，可以开始训练！**

**快速检查清单**:
- [x] Python 依赖已安装
- [x] Rust 扩展已编译
- [x] 配置文件已准备
- [x] 目录已创建
- [ ] 小规模测试已通过
- [ ] 正式训练已启动

**预计时间**:
- 环境准备: 10-30分钟
- 小规模测试: 5-10分钟
- 正式训练: 根据配置而定

**如有问题，请参考故障排查部分或查看日志文件。**

