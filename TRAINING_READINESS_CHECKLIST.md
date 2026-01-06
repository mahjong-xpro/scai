# 训练准备检查清单

## 执行时间
2024年（当前）

## 检查项目

### ✅ 已修复的关键问题

1. **MetricsLogger.get_recent_metrics() 方法**
   - ✅ 已实现 `get_recent_metrics()` 方法
   - ✅ 支持获取最近的损失、评估和性能指标

2. **Ray Worker 失败处理**
   - ✅ 使用 `ray.wait()` 处理部分 worker 失败
   - ✅ 添加超时机制（5分钟）
   - ✅ 失败 worker 不会中断整个数据收集过程

3. **Checkpoint 保存原子性**
   - ✅ 使用临时文件 + 原子性重命名
   - ✅ 添加时间戳避免文件名冲突
   - ✅ 错误处理和清理机制

4. **训练循环异常处理**
   - ✅ 添加信号处理（SIGINT, SIGTERM）
   - ✅ 优雅中断和自动保存
   - ✅ 定期自动保存（每10次迭代）
   - ✅ 错误分类处理（严重错误退出，其他继续）

5. **Evaluator 除零风险**
   - ✅ 使用实际成功游戏数计算胜率
   - ✅ 所有除法操作都有除零检查

6. **OpponentPool 错误处理**
   - ✅ Checkpoint 文件存在性检查
   - ✅ 加载失败时从池中移除对手
   - ✅ 加权采样边界检查

7. **Collector 轨迹验证统计**
   - ✅ 修复统计逻辑，确保准确性
   - ✅ 区分严格模式和非严格模式

---

### 📋 系统组件检查

#### 1. 核心模块
- ✅ `scai.models` - Dual-ResNet 模型
- ✅ `scai.training` - PPO, Buffer, Trainer, Evaluator
- ✅ `scai.selfplay` - Worker, Collector, Feeding Games
- ✅ `scai.search` - ISMCTS
- ✅ `scai.utils` - Logger, Checkpoint, Data Validator
- ✅ `scai.coach` - Curriculum Learning, Dashboard

#### 2. 配置文件
- ✅ `config.yaml` - 完整的训练配置
- ✅ 所有必需参数已定义
- ✅ 可选功能配置完整

#### 3. 依赖项
- ✅ `requirements.txt` - 所有依赖已列出
- ✅ PyTorch >= 2.0.0
- ✅ Ray >= 2.0.0
- ✅ 其他工具库（tqdm, pyyaml, flask等）

#### 4. Rust 绑定
- ⚠️ 需要构建 Rust 扩展：`cd rust && maturin develop`
- ⚠️ 确保 `scai_engine` 模块可用

---

### 🔍 训练流程检查

#### 1. 初始化阶段
- ✅ 配置文件加载
- ✅ 日志系统初始化
- ✅ Ray 初始化（如果启用）
- ✅ 模型创建
- ✅ 训练器初始化
- ✅ 数据收集器初始化
- ✅ 评估器初始化
- ✅ 课程学习初始化（如果启用）

#### 2. 训练循环
- ✅ 迭代循环
- ✅ 数据收集（每 N 次迭代）
- ✅ 模型训练（PPO 更新）
- ✅ 模型评估（每 N 次迭代）
- ✅ Checkpoint 保存（每 N 次迭代）
- ✅ 定期自动保存（每 10 次迭代）
- ✅ 课程学习阶段调整
- ✅ 仪表板状态更新

#### 3. 错误处理
- ✅ 信号处理（Ctrl+C 优雅中断）
- ✅ 异常捕获和分类
- ✅ 自动保存机制
- ✅ 错误日志记录

#### 4. 完成阶段
- ✅ 最终评估
- ✅ 最终 Checkpoint 保存
- ✅ 指标保存

---

### ⚠️ 训练前必须完成的事项

#### 1. Rust 扩展构建
```bash
cd rust
maturin develop
# 或
maturin build
pip install target/wheels/scai_engine-*.whl
```

#### 2. Python 依赖安装
```bash
cd python
pip install -r requirements.txt
```

#### 3. 目录创建
```bash
mkdir -p checkpoints
mkdir -p logs
mkdir -p coach_documents
```

#### 4. 配置文件检查
- ✅ 检查 `config.yaml` 中的路径是否正确
- ✅ 检查 GPU/CPU 配置
- ✅ 检查 Ray worker 数量（根据系统资源调整）
- ✅ 检查课程学习配置（如果启用）

#### 5. 系统资源检查
- ⚠️ 确保有足够的磁盘空间（checkpoints 和 logs）
- ⚠️ 确保有足够的内存（Ray workers）
- ⚠️ 如果使用 GPU，确保 CUDA 可用

---

### 🚀 启动训练

#### 基本训练
```bash
cd python
python train.py --config config.yaml
```

#### 从 Checkpoint 恢复
```bash
python train.py --config config.yaml --resume checkpoints/latest.pt
```

#### 仅评估模式
```bash
python train.py --config config.yaml --eval-only --checkpoint checkpoints/checkpoint_iter_100.pt
```

---

### 📊 监控训练

#### 1. 日志文件
- 位置：`logs/` 目录
- 格式：文本或 JSON（根据配置）
- 包含：训练步骤、损失、评估结果、错误信息

#### 2. 指标文件
- 位置：`logs/metrics_*.json`
- 包含：损失历史、评估历史、性能指标

#### 3. Web 仪表板（如果启用）
- URL：`http://localhost:5000`
- 实时显示：训练进度、阶段信息、性能指标

#### 4. Checkpoint 文件
- 位置：`checkpoints/` 目录
- 格式：`checkpoint_iter_{iteration}_{timestamp}.pt`
- 最新：`checkpoints/latest.pt`

---

### 🔧 常见问题排查

#### 1. ImportError: No module named 'scai_engine'
- **原因**：Rust 扩展未构建
- **解决**：运行 `cd rust && maturin develop`

#### 2. Ray 初始化失败
- **原因**：端口被占用或资源不足
- **解决**：检查 Ray 配置，减少 worker 数量

#### 3. CUDA out of memory
- **原因**：批次大小或模型太大
- **解决**：减少 `batch_size` 或使用 CPU

#### 4. 数据收集失败
- **原因**：Worker 崩溃或 Rust 引擎错误
- **解决**：检查日志，减少 worker 数量，检查 Rust 代码

#### 5. Checkpoint 加载失败
- **原因**：文件损坏或模型结构不匹配
- **解决**：检查 checkpoint 文件，使用 `strict=False` 模式

---

### ✅ 训练准备状态

**核心功能**: ✅ 就绪
- 所有关键组件已实现
- 错误处理已完善
- 训练流程完整

**配置**: ✅ 就绪
- 配置文件完整
- 所有参数已定义

**依赖项**: ⚠️ 需要验证
- Python 依赖需要安装
- Rust 扩展需要构建

**系统资源**: ⚠️ 需要检查
- 磁盘空间
- 内存
- GPU（如果使用）

---

## 下一步行动

1. **构建 Rust 扩展**
   ```bash
   cd rust && maturin develop
   ```

2. **安装 Python 依赖**
   ```bash
   cd python && pip install -r requirements.txt
   ```

3. **创建必要目录**
   ```bash
   mkdir -p checkpoints logs coach_documents
   ```

4. **验证配置**
   - 检查 `config.yaml` 中的路径
   - 根据系统资源调整 worker 数量
   - 确认课程学习配置（如果需要）

5. **运行测试**
   - 可以先运行少量迭代测试
   - 检查日志输出
   - 验证 checkpoint 保存

6. **开始训练**
   ```bash
   python train.py --config config.yaml
   ```

---

*检查清单生成时间: 2024年*
*状态: 系统已就绪，等待依赖项安装和配置验证*

