# 训练卡住问题排查指南

## 问题描述

训练开始时，`nvidia-smi` 命令卡住，日志也不动。

---

## 可能的原因和解决方案

### 1. Ray Workers 初始化卡住 ⚠️ **最可能**

**症状**：
- 日志停在 "Collecting trajectories..."
- `nvidia-smi` 卡住
- 没有进一步的日志输出

**原因**：
- 创建大量 Ray workers（默认 100 个）需要时间
- 每个 worker 需要初始化 Rust 引擎和模型
- 如果 worker 数量过多，可能导致资源竞争

**解决方案**：

#### 方案 A: 减少 Worker 数量（推荐）

修改 `config.yaml`：

```yaml
selfplay:
  num_workers: 10  # 从 100 减少到 10（或更少）
  games_per_worker: 100  # 相应增加每个 worker 的游戏数量
```

**原理**：
- 减少并发 worker 数量，降低资源竞争
- 增加每个 worker 的游戏数量，保持总游戏数不变

#### 方案 B: 添加进度日志

在 `collector.py` 的 `initialize_workers` 中添加日志：

```python
def initialize_workers(self, use_feeding: bool = False, enable_win: bool = True):
    logger.info(f"Initializing {self.num_workers} workers...")
    if self.workers is None:
        # 分批创建 workers，避免一次性创建太多
        batch_size = 10
        workers = []
        for i in range(0, self.num_workers, batch_size):
            batch_workers = create_workers(
                num_workers=min(batch_size, self.num_workers - i),
                ...
            )
            workers.extend(batch_workers)
            logger.info(f"Created {len(workers)}/{self.num_workers} workers...")
        self.workers = workers
```

---

### 2. 模型加载到 GPU 卡住

**症状**：
- 日志停在模型创建后
- GPU 使用率突然上升然后卡住

**原因**：
- 模型太大（54M 参数）
- 多个 workers 同时加载模型到 GPU
- GPU 内存不足

**解决方案**：

#### 方案 A: 使用 CPU 进行数据收集

修改 `worker.py`，让 workers 使用 CPU：

```python
# 在 create_workers 中
device = 'cpu'  # 数据收集使用 CPU，训练使用 GPU
```

**原理**：
- 数据收集不需要 GPU（推理速度足够快）
- 只有训练步骤需要 GPU
- 可以大幅减少 GPU 内存使用

#### 方案 B: 减少并发 Workers

减少 `num_workers`，避免同时加载太多模型。

---

### 3. Rust 引擎初始化卡住

**症状**：
- 日志停在 "Collecting trajectories..." 之前
- 没有错误信息

**原因**：
- Rust 引擎初始化需要时间
- 多个 workers 同时初始化可能导致资源竞争
- PyO3 绑定可能有问题

**解决方案**：

#### 方案 A: 添加超时和重试

在 `worker.py` 的 `__init__` 中添加超时：

```python
def __init__(self, ...):
    try:
        self.engine = scai_engine.PyGameEngine()
        self.engine.initialize()
    except Exception as e:
        # 记录错误并重试
        print(f"Worker {worker_id} engine init failed: {e}")
        raise
```

#### 方案 B: 检查 Rust 扩展是否正确编译

```bash
cd rust
cargo build --release --features python
python -c "import scai_engine; print('OK')"
```

---

### 4. 数据收集阻塞

**症状**：
- 日志显示 "Collecting trajectories..."
- 但没有任何 worker 完成

**原因**：
- `ray.wait` 超时设置过长（5分钟）
- Workers 可能卡在某个操作上
- 没有进度日志

**解决方案**：

#### 方案 A: 添加进度日志

修改 `collect_trajectories_parallel`：

```python
def collect_trajectories_parallel(...):
    futures = [worker.run.remote(model_state_dict) for worker in workers]
    logger.info(f"Started {len(futures)} workers, waiting for results...")
    
    all_trajectories = []
    remaining_futures = futures
    start_time = time.time()
    
    while remaining_futures:
        elapsed = time.time() - start_time
        logger.info(f"Waiting for {len(remaining_futures)} workers... (elapsed: {elapsed:.1f}s)")
        
        ready, remaining_futures = ray.wait(
            remaining_futures,
            num_returns=1,
            timeout=60.0,  # 减少超时时间，更频繁检查
        )
        # ...
```

#### 方案 B: 减少超时时间

将 `ray.wait` 的超时从 300 秒减少到 60 秒，更早发现问题。

---

## 快速诊断步骤

### 1. 检查进程状态

```bash
# 查看 Python 进程
ps aux | grep train.py

# 查看 Ray 进程
ps aux | grep ray

# 查看 GPU 进程
nvidia-smi
```

### 2. 检查日志

```bash
# 查看最新日志
tail -f logs/training_*.log

# 查看是否有错误
grep -i error logs/training_*.log
```

### 3. 检查资源使用

```bash
# CPU 使用率
top

# 内存使用
free -h

# GPU 使用（如果 nvidia-smi 不卡）
watch -n 1 nvidia-smi
```

### 4. 测试单个 Worker

创建一个测试脚本：

```python
# test_worker.py
import ray
ray.init()

from scai.selfplay.worker import SelfPlayWorker
from scai.models import DualResNet
import torch

# 创建单个 worker
worker = SelfPlayWorker.remote(
    worker_id=0,
    num_games=1,
    use_oracle=True,
    device='cpu',  # 使用 CPU 测试
)

# 创建简单模型
model = DualResNet(...)
model_state_dict = model.state_dict()

# 运行单个游戏
result = ray.get(worker.run.remote(model_state_dict))
print(f"Result: {len(result)} trajectories")
```

---

## 推荐的配置（避免卡住）

### 最小配置（测试用）

```yaml
selfplay:
  num_workers: 4  # 少量 workers
  games_per_worker: 10
```

### 生产配置（稳定）

```yaml
selfplay:
  num_workers: 20  # 中等数量
  games_per_worker: 50
```

### 高性能配置（需要足够资源）

```yaml
selfplay:
  num_workers: 100  # 大量 workers
  games_per_worker: 10
```

**注意**：worker 数量应该根据 CPU 核心数和内存调整。

---

## 调试技巧

### 1. 添加详细日志

在 `train.py` 中添加：

```python
logger.info("About to initialize workers...")
collector.initialize_workers(...)
logger.info("Workers initialized, starting collection...")
trajectories = collector.collect(...)
logger.info(f"Collection complete: {len(trajectories)} trajectories")
```

### 2. 使用 Ray Dashboard

```bash
# 启动 Ray Dashboard
ray dashboard

# 访问 http://localhost:8265
# 查看 workers 状态和资源使用
```

### 3. 逐步增加复杂度

1. 先测试 1 个 worker
2. 然后测试 4 个 workers
3. 逐步增加到目标数量

---

## 常见问题

### Q: 为什么 nvidia-smi 会卡住？

**A**: 可能是因为：
- 大量进程同时访问 GPU
- GPU 驱动被锁定
- 系统资源耗尽

**解决**：
- 减少 worker 数量
- 使用 CPU 进行数据收集
- 检查系统资源

### Q: 训练卡住但没有错误？

**A**: 可能是：
- Workers 正在初始化（需要时间）
- 等待 GPU 资源
- 网络或文件系统问题

**解决**：
- 添加进度日志
- 检查系统资源
- 减少并发度

### Q: 如何知道训练是否真的卡住了？

**A**: 检查：
1. 日志是否有新输出（等待 1-2 分钟）
2. CPU 使用率是否在变化
3. 是否有新的检查点文件生成
4. Ray Dashboard 中 workers 的状态

---

## 紧急恢复

如果训练完全卡住：

1. **强制终止**：
   ```bash
   pkill -f train.py
   pkill -f ray
   ```

2. **清理 Ray**：
   ```bash
   ray stop
   ```

3. **检查资源**：
   ```bash
   # 检查是否有僵尸进程
   ps aux | grep defunct
   
   # 检查 GPU
   nvidia-smi
   ```

4. **重新启动**（使用更少的 workers）：
   ```bash
   # 修改 config.yaml，减少 num_workers
   python train.py --config config.yaml
   ```

---

*最后更新: 2024年*

