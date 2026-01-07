# 阶段一训练检查指南

## 阶段一训练目标

**阶段1：定缺与生存（弃牌逻辑初探）**

**目标**：
- ✅ 理解定缺规则
- ✅ 学会选择定缺花色
- ✅ 避免成为花猪
- ✅ 掌握弃牌逻辑（优先打缺门牌）

**评估标准**：
- 花猪率 < 50%（初期非常宽松）
- 定缺选择正确率 > 60%
- 至少完成500局游戏

## 检查方法

### 1. 查看Web仪表板（推荐）

访问：`http://localhost:5000`（或通过SSH隧道访问）

**查看内容**：

1. **当前阶段**：
   - 应该显示：`阶段1：定缺与生存（弃牌逻辑初探）`
   - 阶段进度：显示当前迭代次数和预计完成时间

2. **奖励配置**：
   - `lack_color_discard: 5.0`（打缺门牌奖励）
   - `illegal_action_attempt: -10.0`（非法动作惩罚）
   - `base_win: 0.0`（不给胡牌奖励）
   - `ready_reward: 0.0`（不给听牌奖励）

3. **训练指标**：
   - 查看花猪率（应该逐渐下降）
   - 查看定缺选择正确率（应该逐渐上升）
   - 查看游戏完成数量

### 2. 查看训练日志

#### 2.1 检查阶段信息

```bash
# 查看日志文件
tail -f logs/training_*.log

# 或查看最新日志
ls -lt logs/ | head -5
```

**应该看到**：
```
Curriculum learning enabled, initial stage: 定缺阶段
Reward config for stage 定缺阶段: {'lack_color_discard': 5.0, 'illegal_action_attempt': -10.0, ...}
```

#### 2.2 检查奖励配置

**应该看到**：
```
Updated collector config: enable_win=True, use_feeding=False, feeding_rate=0.0
```

**说明**：
- ✅ `use_feeding=False`：阶段1不使用喂牌（正确）
- ✅ `feeding_rate=0.0`：喂牌率为0（正确）

#### 2.3 检查数据收集

**应该看到**：
```
Collecting trajectories...
Collection complete: 2000 trajectories collected
Data collection at iteration X (num_trajectories=2000, ...)
```

**检查点**：
- ✅ 轨迹数量 > 0
- ✅ 验证通过率 > 90%（如果启用验证）
- ✅ 没有大量错误日志

#### 2.4 检查训练损失

**应该看到**：
```
Training step X (iteration=X, policy_loss=..., value_loss=..., entropy_loss=..., total_loss=...)
```

**检查点**：
- ✅ `policy_loss` 应该逐渐下降（绝对值减小）
- ✅ `value_loss` 应该逐渐下降
- ✅ `entropy_loss` 应该保持合理范围（阶段1应该较高，因为 `entropy_coef=0.05`）
- ✅ `total_loss` 应该总体下降

### 3. 检查训练数据统计

#### 3.1 验证统计

**应该看到**：
```
Validation Summary:
  Valid trajectories: X
  Invalid trajectories: Y
  Valid rate: Z%
```

**检查点**：
- ✅ 有效轨迹率 > 90%
- ✅ 无效轨迹数量应该很少
- ⚠️ 如果看到大量 "All rewards are zero" 警告，这是正常的（阶段1不给胡牌奖励）

#### 3.2 奖励统计

**检查奖励分布**：

```python
# 可以在日志中搜索奖励相关的信息
grep -i "reward" logs/training_*.log | tail -20
```

**预期**：
- 大部分奖励应该来自 `lack_color_discard`（打缺门牌）
- 如果看到 `illegal_action_attempt` 的惩罚，说明AI在尝试非法动作（这是学习过程的一部分）

### 4. 检查关键指标

#### 4.1 花猪率

**如何检查**：
- Web仪表板中查看（如果有统计）
- 日志中搜索 "flower_pig" 或 "花猪"
- 评估脚本输出

**预期**：
- 初期可能较高（>50%）
- 随着训练进行，应该逐渐下降
- 目标：< 50%（阶段1的评估标准）

#### 4.2 定缺选择正确率

**如何检查**：
- Web仪表板中查看
- 评估脚本输出
- 日志中搜索 "declare_suit" 或 "定缺"

**预期**：
- 初期可能较低（<60%）
- 随着训练进行，应该逐渐上升
- 目标：> 60%（阶段1的评估标准）

#### 4.3 游戏完成数量

**如何检查**：
- 日志中查看 "games_played" 或 "trajectories collected"
- Web仪表板中查看

**预期**：
- 应该持续增长
- 目标：至少完成500局游戏（阶段1的评估标准）

### 5. 检查训练进度

#### 5.1 迭代次数

**检查点**：
- 当前迭代次数应该在 2000-8000 之间（阶段1的范围）
- 如果超过 8000 次迭代，应该自动推进到阶段2

**查看方法**：
```bash
# 查看最新日志中的迭代信息
grep "iteration=" logs/training_*.log | tail -5
```

#### 5.2 阶段推进

**应该看到**（当满足条件时）：
```
Advanced from 定缺阶段 to 学胡阶段
Updated reward config: {...}
Updated collector config: use_feeding=True, feeding_rate=0.2
```

**检查点**：
- ✅ 如果训练超过 8000 次迭代，应该自动推进
- ✅ 如果满足评估标准，应该提前推进

### 6. 检查常见问题

#### 6.1 所有奖励都是0

**症状**：
```
Warning: Trajectory X: All rewards are zero
```

**原因**：
- 阶段1不给胡牌奖励（`base_win: 0.0`）
- 如果AI没有打缺门牌，奖励就是0

**检查**：
- 查看是否有 `lack_color_discard` 奖励
- 如果完全没有奖励，可能是：
  1. AI没有打缺门牌（需要更多训练）
  2. 奖励配置未正确传递（检查日志中的奖励配置）

#### 6.2 训练损失不下降

**症状**：
- `policy_loss` 不下降或上升
- `value_loss` 不下降或上升

**可能原因**：
1. 学习率过高或过低
2. 批次大小不合适
3. 数据质量问题

**检查**：
- 查看学习率：`learning_rate: 3e-4`
- 查看批次大小：`batch_size: 8192`
- 检查数据验证统计

#### 6.3 花猪率不下降

**症状**：
- 花猪率一直很高（>50%）
- 训练很久没有改善

**可能原因**：
1. 奖励配置未生效
2. 训练时间不够
3. 模型容量不足

**检查**：
- 确认奖励配置正确（`lack_color_discard: 5.0`）
- 确认训练迭代次数足够（至少2000次）
- 查看模型参数（`num_blocks: 20`）

## 快速检查清单

### ✅ 基础检查

- [ ] Web仪表板可以访问
- [ ] 当前阶段显示为"阶段1：定缺与生存"
- [ ] 奖励配置正确（`lack_color_discard: 5.0`）
- [ ] 数据收集正常（轨迹数量 > 0）
- [ ] 训练损失在下降

### ✅ 指标检查

- [ ] 花猪率 < 50%（或逐渐下降）
- [ ] 定缺选择正确率 > 60%（或逐渐上升）
- [ ] 游戏完成数量 > 500
- [ ] 有效轨迹率 > 90%

### ✅ 配置检查

- [ ] `use_feeding=False`（阶段1不使用喂牌）
- [ ] `feeding_rate=0.0`（喂牌率为0）
- [ ] `entropy_coef=0.05`（高熵，鼓励探索）
- [ ] 奖励配置包含 `lack_color_discard: 5.0`

## 评估脚本（可选）

可以创建一个简单的评估脚本来检查阶段1的训练效果：

```python
# scripts/check_stage1.py
import json
import re
from pathlib import Path

def check_stage1_training(log_dir="./logs"):
    """检查阶段1训练效果"""
    log_files = sorted(Path(log_dir).glob("training_*.log"), reverse=True)
    
    if not log_files:
        print("❌ 未找到日志文件")
        return
    
    latest_log = log_files[0]
    print(f"📄 检查日志: {latest_log}")
    
    with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 检查阶段信息
    if "定缺阶段" in content or "DECLARE_SUIT" in content:
        print("✅ 当前阶段: 阶段1（定缺与生存）")
    else:
        print("⚠️  未找到阶段1信息")
    
    # 检查奖励配置
    if "lack_color_discard" in content:
        print("✅ 奖励配置: 包含 lack_color_discard（打缺门牌奖励）")
    else:
        print("⚠️  未找到 lack_color_discard 奖励配置")
    
    # 检查数据收集
    trajectories = re.findall(r'num_trajectories=(\d+)', content)
    if trajectories:
        latest = trajectories[-1]
        print(f"✅ 最新数据收集: {latest} 条轨迹")
    
    # 检查训练损失
    losses = re.findall(r'policy_loss=([-\d.]+)', content)
    if len(losses) >= 2:
        recent = float(losses[-1])
        earlier = float(losses[-10]) if len(losses) >= 10 else float(losses[0])
        if recent < earlier:
            print(f"✅ 策略损失在下降: {earlier:.4f} -> {recent:.4f}")
        else:
            print(f"⚠️  策略损失未下降: {earlier:.4f} -> {recent:.4f}")

if __name__ == "__main__":
    check_stage1_training()
```

## 总结

**阶段1训练正确的标志**：

1. ✅ **阶段信息正确**：显示"阶段1：定缺与生存"
2. ✅ **奖励配置正确**：`lack_color_discard: 5.0`
3. ✅ **数据收集正常**：轨迹数量持续增长
4. ✅ **训练损失下降**：policy_loss 和 value_loss 逐渐下降
5. ✅ **指标改善**：花猪率下降，定缺正确率上升
6. ✅ **配置正确**：`use_feeding=False`，`feeding_rate=0.0`

**如果以上都正常，说明阶段1训练正确！** 🎉

