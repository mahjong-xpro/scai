# GPU 配置指南

## 概述

本指南介绍如何配置和使用 GPU 进行训练，特别是针对多 GPU 服务器的配置。

## 服务器配置

- **GPU 型号**: NVIDIA RTX 4090
- **GPU 数量**: 8 张
- **使用 GPU**: 前 4 张（GPU 0, 1, 2, 3）

## 配置方法

### 1. 配置文件设置

在 `config.yaml` 中配置 GPU：

```yaml
# GPU 配置
gpu:
  enabled: true                 # 是否启用 GPU
  device_ids: [0, 1, 2, 3]     # 使用的 GPU 设备 ID（8 卡服务器，使用前 4 张：0,1,2,3）

# Ray 配置
ray:
  init: true                    # 是否初始化 Ray
  num_cpus: null               # CPU 数量（null 表示自动检测）
  num_gpus: null               # GPU 数量（null 表示自动检测，会根据 gpu.device_ids 自动计算）
```

### 2. 工作原理

当设置 `gpu.device_ids` 时，系统会：

1. **设置环境变量**: 自动设置 `CUDA_VISIBLE_DEVICES=0,1,2,3`
   - 这样 PyTorch 和 Ray 只能看到这 4 张 GPU
   - PyTorch 会将它们识别为 `cuda:0`, `cuda:1`, `cuda:2`, `cuda:3`

2. **Ray GPU 分配**: Ray 会自动检测可见的 GPU 数量（4 张）

3. **模型设备**: 主模型会使用 `cuda:0`（第一张可见的 GPU）

### 3. 配置选项说明

#### `gpu.enabled`
- `true`: 启用 GPU
- `false`: 使用 CPU

#### `gpu.device_ids`
- 列表格式，指定要使用的 GPU 设备 ID
- 例如：`[0, 1, 2, 3]` 表示使用前 4 张 GPU
- 如果设置为 `null` 或空列表，会使用所有可用 GPU

#### `ray.num_gpus`
- `null`: 自动检测（推荐，会根据 `gpu.device_ids` 自动计算）
- 数字: 手动指定 GPU 数量
- `0`: 不使用 GPU

## 使用场景

### 场景 1: 使用前 4 张 GPU（当前配置）

```yaml
gpu:
  enabled: true
  device_ids: [0, 1, 2, 3]
```

**效果**:
- 只使用 GPU 0, 1, 2, 3
- GPU 4, 5, 6, 7 不会被使用
- 其他程序可以使用后 4 张 GPU

### 场景 2: 使用所有 GPU

```yaml
gpu:
  enabled: true
  device_ids: []  # 或 null
```

**效果**:
- 使用所有 8 张 GPU
- Ray 会分配 worker 到所有 GPU

### 场景 3: 使用特定 GPU

```yaml
gpu:
  enabled: true
  device_ids: [2, 3, 6, 7]  # 使用 GPU 2, 3, 6, 7
```

**效果**:
- 只使用指定的 GPU
- 其他 GPU 可以用于其他任务

### 场景 4: 仅使用 CPU

```yaml
gpu:
  enabled: false
```

**效果**:
- 完全不使用 GPU
- 所有计算在 CPU 上进行

## 验证配置

### 1. 检查 GPU 可见性

启动训练后，查看日志：

```
Using GPUs: [0, 1, 2, 3] (CUDA_VISIBLE_DEVICES=0,1,2,3)
PyTorch will see 4 GPU(s) as cuda:0 to cuda:3
Ray initialized with 4 GPU(s)
```

### 2. 检查 GPU 使用情况

在另一个终端运行：

```bash
# 查看所有 GPU 使用情况
nvidia-smi

# 或者持续监控
watch -n 1 nvidia-smi
```

**预期结果**:
- GPU 0, 1, 2, 3 应该有使用（内存、计算）
- GPU 4, 5, 6, 7 应该空闲（如果只使用前 4 张）

### 3. 验证环境变量

```bash
# 在训练脚本中，CUDA_VISIBLE_DEVICES 会被自动设置
echo $CUDA_VISIBLE_DEVICES
# 应该输出: 0,1,2,3
```

## 性能优化建议

### 1. Worker 分配

- **Ray Workers**: 每个 worker 可以分配一个 GPU
- **建议配置**: `num_workers` 应该与可用 GPU 数量匹配或略多
- **示例**: 4 张 GPU，可以设置 `num_workers: 40-80`（每个 GPU 10-20 个 worker）

### 2. 批次大小

- **单 GPU**: `batch_size: 4096`
- **多 GPU**: 可以适当增加批次大小
- **建议**: 每张 GPU 处理 `batch_size / num_gpus` 的数据

### 3. 内存管理

- **4090 GPU**: 24GB 显存
- **建议**: 监控显存使用，避免 OOM
- **如果 OOM**: 减少 `batch_size` 或 `num_workers`

## 故障排查

### 问题 1: CUDA out of memory

**原因**: 显存不足

**解决方案**:
1. 减少 `batch_size`
2. 减少 `num_workers`
3. 使用更少的 GPU（减少 `device_ids` 数量）

### 问题 2: GPU 未被使用

**检查**:
1. 确认 `gpu.enabled: true`
2. 确认 `device_ids` 配置正确
3. 检查日志中的 GPU 信息
4. 运行 `nvidia-smi` 查看 GPU 状态

### 问题 3: Ray 看不到 GPU

**检查**:
1. 确认 `CUDA_VISIBLE_DEVICES` 环境变量已设置
2. 确认 Ray 初始化时 `num_gpus` 正确
3. 检查 Ray dashboard: `http://localhost:8265`

### 问题 4: 其他程序占用 GPU

**解决方案**:
1. 使用 `nvidia-smi` 查看占用 GPU 的进程
2. 使用 `device_ids` 指定未占用的 GPU
3. 或者先停止其他程序

## 高级配置

### 多 GPU 训练（DataParallel）

如果需要使用多 GPU 进行模型训练（而不是仅用于数据收集），可以修改 `train.py`：

```python
if device.startswith('cuda') and torch.cuda.device_count() > 1:
    model = torch.nn.DataParallel(model, device_ids=list(range(torch.cuda.device_count())))
```

**注意**: 当前实现主要使用 GPU 进行数据收集（Ray workers），模型训练通常使用单 GPU。

### 分布式训练（DistributedDataParallel）

对于大规模训练，可以考虑使用 `DistributedDataParallel`：

```python
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

# 初始化分布式环境
dist.init_process_group(backend='nccl')
model = DDP(model, device_ids=[local_rank])
```

这需要更复杂的配置，通常用于多机多卡训练。

## 示例配置

### 8 卡服务器，使用前 4 张（推荐）

```yaml
gpu:
  enabled: true
  device_ids: [0, 1, 2, 3]

ray:
  init: true
  num_cpus: null
  num_gpus: null  # 自动检测为 4

selfplay:
  num_workers: 80  # 每张 GPU 约 20 个 worker
```

### 8 卡服务器，使用所有 GPU

```yaml
gpu:
  enabled: true
  device_ids: []  # 使用所有 GPU

ray:
  init: true
  num_cpus: null
  num_gpus: null  # 自动检测为 8

selfplay:
  num_workers: 160  # 每张 GPU 约 20 个 worker
```

## 相关文档

- [训练指南](../training/TRAINING_GUIDE.md)
- [配置文件说明](../config/CONFIG_GUIDE.md)
- [性能优化](../optimization/PERFORMANCE_TUNING.md)

---

*最后更新: 2024年*

