# Ray 警告说明

## 概述

在运行训练时，可能会看到一些 Ray 相关的警告信息。这些警告大多数是**非关键的**，不会影响训练功能。

---

## 常见警告

### 1. Metrics Exporter 连接失败

**警告信息**：
```
Failed to establish connection to the metrics exporter agent.
Metrics will not be exported.
```

**原因**：
- Ray 尝试连接到外部监控系统（metrics exporter）失败
- 这通常发生在没有配置外部监控系统的情况下

**影响**：
- ✅ **不影响训练**：训练功能完全正常
- ⚠️ **仅影响监控**：无法导出指标到外部系统（如 Prometheus）
- ✅ **本地监控正常**：Ray Dashboard 和日志仍然可用

**解决方案**：
- **推荐**：忽略这些警告（训练不受影响）
- **可选**：如果需要外部监控，配置 Ray metrics exporter

---

### 2. Accelerator Visible Devices 警告

**警告信息**：
```
FutureWarning: Tip: In future versions of Ray, Ray will no longer override 
accelerator visible devices env var if num_gpus=0 or num_gpus=None (default).
```

**原因**：
- Ray 未来版本的行为变更警告
- 当 `num_gpus=0` 或 `num_gpus=None` 时，Ray 将不再覆盖 `CUDA_VISIBLE_DEVICES`

**影响**：
- ✅ **不影响训练**：当前版本仍然正常工作
- ⚠️ **未来兼容性**：可能需要调整配置

**解决方案**：
- **当前**：可以忽略（不影响功能）
- **未来**：如果使用 CPU 训练，设置环境变量：
  ```bash
  export RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0
  ```

---

## 如何抑制警告

### 方法 1: 设置环境变量（推荐）

在运行训练前设置：

```bash
# 抑制 metrics exporter 警告（如果不需要外部监控）
export RAY_DISABLE_IMPORT_WARNING=1

# 抑制 accelerator visible devices 警告（如果使用 CPU）
export RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0
```

### 方法 2: 在代码中设置

`train.py` 已经自动设置了这些环境变量（如果适用）。

### 方法 3: 重定向 stderr（临时方案）

如果只是想隐藏警告输出：

```bash
python train.py --config config.yaml 2>/dev/null
```

**注意**：这会隐藏所有错误信息，不推荐用于调试。

---

## 验证训练是否正常

即使看到这些警告，训练仍然正常进行。可以通过以下方式验证：

### 1. 检查日志输出

正常训练应该看到：
```
INFO - Collecting trajectories...
INFO - Training model...
INFO - Evaluating model...
```

### 2. 检查 GPU 使用

```bash
nvidia-smi
```

应该看到 Python 进程在使用 GPU。

### 3. 检查检查点文件

```bash
ls -lh checkpoints/
```

应该看到定期生成的检查点文件。

### 4. 检查 Ray Dashboard

```bash
# 访问 Ray Dashboard（如果启用）
http://localhost:8265
```

---

## 总结

| 警告类型 | 是否影响训练 | 建议操作 |
|---------|------------|---------|
| Metrics Exporter 连接失败 | ❌ 不影响 | 忽略 |
| Accelerator Visible Devices | ❌ 不影响 | 忽略或设置环境变量 |
| 其他 Ray 警告 | 视情况而定 | 查看具体错误信息 |

**重要**：只要看到 "Collecting trajectories..." 和 "Training model..." 等日志，说明训练正在正常进行。

---

*最后更新: 2024年*

