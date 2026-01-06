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

## SIGSEGV (Segmentation Fault) 问题

### 问题描述

训练过程中出现 SIGSEGV 错误，导致 Ray workers 崩溃：

```
(SelfPlayWorker pid=1484676) *** SIGSEGV received at time=1767731500 on cpu 6 ***
(SelfPlayWorker pid=1484676) PC: @     0x7f26a0476541  (unknown)  
_$LT$hashbrown..map..HashMap$LT$K$C$V$C$S$C$A$GT$$u20$as$u20$core..clone..Clone$GT$::clone
```

同时可能伴随 `WallEmpty` 错误：
```
(SelfPlayWorker pid=1484719) Worker 4, Game 28, Turn 44 error: Action failed: WallEmpty
```

### 原因分析

1. **频繁的状态克隆**：每次访问 `engine.state` 都会克隆整个 `GameState`，包括 4 个玩家的手牌（每个手牌包含 HashMap）
2. **内存压力**：在高并发 Ray workers 环境下，频繁克隆大型结构可能导致内存压力
3. **状态损坏**：如果游戏状态已损坏，克隆 HashMap 时可能触发 SIGSEGV
4. **WallEmpty 未处理**：在牌墙为空时继续尝试摸牌，导致状态不一致

### 解决方案

#### 已实施的修复

1. **状态验证**：在克隆 `GameState` 前添加验证，提前发现损坏的状态
   - 位置：`rust/src/python/game_engine.rs` 的 `state()` getter
   - 验证玩家 ID、牌数守恒、状态一致性等

2. **错误处理**：在 Python worker 中添加 try-catch，优雅处理状态获取失败
   - 位置：`python/scai/selfplay/worker.py`
   - 在访问 `engine.state` 时捕获异常

3. **WallEmpty 检查**：在摸牌前检查牌墙是否为空
   - 使用 `engine.remaining_tiles()` 检查剩余牌数
   - 如果为 0，提前结束游戏，避免 `WallEmpty` 错误

#### 预防措施

1. **减少状态克隆频率**：
   - 缓存状态对象（如果可能）
   - 只在必要时克隆状态
   - 考虑使用引用计数（`Arc`/`Rc`）共享状态

2. **监控内存使用**：
   ```bash
   # 监控内存使用
   watch -n 1 'free -h'
   
   # 检查是否有 OOM killer 活动
   dmesg | grep -i "out of memory"
   ```

3. **调整 Worker 配置**：
   - 减少并发 worker 数量
   - 增加每个 worker 的游戏数量
   - 在 `config.yaml` 中调整：
     ```yaml
     selfplay:
       num_workers: 50  # 减少并发数
       games_per_worker: 20  # 增加每 worker 游戏数
     ```

4. **重建 Rust 扩展**：
   修复后需要重新编译 Rust 扩展：
   ```bash
   cd rust
   maturin develop --release
   ```

### 诊断步骤

1. **检查日志**：
   ```bash
   grep -i "SIGSEGV\|WallEmpty\|validation failed" logs/training_*.log
   ```

2. **检查内存**：
   ```bash
   # 查看内存使用
   free -h
   
   # 查看 OOM killer 日志
   dmesg | tail -50 | grep -i oom
   ```

3. **测试单个 Worker**：
   创建测试脚本验证修复是否有效

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

