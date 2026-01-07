# 仪表板启动问题修复

## 问题描述

仪表板（Dashboard）无法启动，即使配置正确也没有看到启动日志。

## 根本原因

**Bug**：仪表板启动代码被错误地放在了数据增强（Data Augmentation）块内，导致：
1. 如果数据增强未启用，仪表板就不会启动
2. 即使课程学习启用了，仪表板也不会启动

## 修复内容

已将仪表板启动代码移到正确的位置：

**修复前**（错误）：
```python
if HAS_DATA_AUG:
    if aug_config.get('enabled', False):
        # ... 数据增强代码 ...
        # 启动 Web 仪表板（错误位置！）
        dashboard_config = curriculum_config.get('dashboard', {})
        if dashboard_config.get('enabled', False):
            # ... 启动仪表板 ...
```

**修复后**（正确）：
```python
# 数据增强（如果启用）
if HAS_DATA_AUG:
    if aug_config.get('enabled', False):
        # ... 数据增强代码 ...

# 启动 Web 仪表板（如果启用课程学习）- 独立于数据增强
if HAS_COACH and curriculum is not None:
    curriculum_config = config.get('curriculum_learning', {})
    dashboard_config = curriculum_config.get('dashboard', {})
    if dashboard_config.get('enabled', False):
        # ... 启动仪表板 ...
```

## 验证修复

修复后，重新启动训练脚本，应该看到：

```
Curriculum learning enabled, initial stage: 定缺阶段
课程学习中心 Web 仪表板已启动: http://0.0.0.0:5000
```

然后可以访问：`http://localhost:5000`

## 其他改进

1. **添加了错误处理**：如果仪表板启动失败，会记录错误但不会中断训练
2. **添加了启动等待**：等待0.5秒确保线程启动
3. **更清晰的日志**：明确显示仪表板启动状态

## 检查清单

修复后，确保：

- [x] 仪表板启动代码在正确位置（独立于数据增强）
- [x] `HAS_COACH = True`（课程学习模块可导入）
- [x] `curriculum_learning.enabled: true`
- [x] `curriculum_learning.dashboard.enabled: true`
- [x] 训练脚本重新启动

## 如果仍然无法启动

如果修复后仍然无法启动，检查：

1. **模块导入**：
   ```bash
   python -c "from scai.coach.web_server import start_server; print('OK')"
   ```

2. **依赖安装**：
   ```bash
   pip install flask flask-cors
   ```

3. **端口占用**：
   ```bash
   lsof -i :5000
   ```

4. **查看完整日志**：
   ```bash
   tail -f logs/training_*.log | grep -i dashboard
   ```

