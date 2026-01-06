# 课程学习使用指南

## 概述

课程学习（Curriculum Learning）是一种分阶段训练策略，让 AI 从简单到复杂逐步学习。系统会自动判断是否应该进入下一阶段，并生成课程规划文档供您手动提交给大模型进行分析。

## 快速开始

### 1. 启用课程学习

在 `config.yaml` 中启用：

```yaml
curriculum_learning:
  enabled: true                # 启用课程学习
  initial_stage: basic         # 初始阶段（basic/defensive/advanced/expert）
  llm_coach_frequency: 100     # 每 100 次迭代生成一次课程规划文档
  document_output_dir: ./coach_documents  # 文档输出目录
```

### 2. 运行训练

```bash
python train.py --config config.yaml
```

系统会自动：
- 根据当前阶段设置训练目标
- 定期检查是否满足进入下一阶段的条件
- 生成课程规划文档

## 训练阶段

系统定义了 4 个训练阶段，从简单到复杂：

### 阶段 1: 基础阶段 (BASIC)

**目标**: 学习定缺和基本胡牌

**训练内容**:
- 正确选择定缺花色
- 识别基本胡牌类型（平胡、七对等）
- 理解缺一门规则

**评估标准**:
- 胜率 ≥ 30%
- 花猪率 < 5%

**预计迭代次数**: 10,000

### 阶段 2: 防御阶段 (DEFENSIVE)

**目标**: 学习避炮策略

**训练内容**:
- 识别危险牌
- 避免在关键时刻点炮
- 学会过胡策略

**评估标准**:
- 点炮率 < 10%
- 防御得分 ≥ 70%

**预计迭代次数**: 20,000

### 阶段 3: 高级阶段 (ADVANCED)

**目标**: 学习博弈高阶策略

**训练内容**:
- 学会杠牌时机选择
- 优化听牌选择
- 理解期望收益计算

**评估标准**:
- Elo 分数 ≥ 1500
- 平均得分 ≥ 10.0

**预计迭代次数**: 30,000

### 阶段 4: 专家阶段 (EXPERT)

**目标**: 学习复杂策略组合

**训练内容**:
- 掌握所有高级策略
- 优化策略组合
- 达到专家水平

**评估标准**:
- Elo 分数 ≥ 2000
- 胜率 ≥ 50%

**预计迭代次数**: 50,000

## 工作流程

### 自动阶段推进

系统会在每个迭代周期检查是否满足进入下一阶段的条件：

```python
# 在训练循环中（train.py 已自动实现）
if curriculum.should_advance_stage(performance_metrics):
    curriculum.advance_to_next_stage()
    logger.info(f"进入下一阶段: {curriculum.current_stage.value}")
```

**检查逻辑**:
1. 获取当前阶段的评估标准
2. 检查性能指标是否满足所有标准
3. 如果满足，自动推进到下一阶段

### 课程规划文档生成

系统会定期生成课程规划文档（默认每 100 次迭代）：

```python
# 生成课程规划文档
doc_path = curriculum.design_next_stage(
    performance_metrics=current_metrics,
    current_issues=['过度保守', '不敢博清一色'],
    iteration=iteration + 1,
)
```

**文档内容**:
- 当前阶段性能指标
- 当前阶段问题
- 设计任务（训练目标、课程步骤、评估标准）
- 请求的课程规划格式

**文档位置**: `./coach_documents/curriculum_design_{iteration}.md`

## 使用示例

### 示例 1: 基础使用

```python
from scai.coach import CurriculumLearning, TrainingDocumentGenerator, TrainingStage

# 创建文档生成器
document_generator = TrainingDocumentGenerator(output_dir='./coach_documents')

# 创建课程学习规划器
curriculum = CurriculumLearning(document_generator=document_generator)

# 获取当前课程
current = curriculum.get_current_curriculum()
print(f"当前阶段: {current.name}")
print(f"训练目标: {current.objectives}")
print(f"评估标准: {current.evaluation_criteria}")

# 检查性能指标
performance_metrics = {
    'win_rate': 0.35,      # 胜率 35%
    'flower_pig_rate': 0.03,  # 花猪率 3%
}

# 判断是否应该进入下一阶段
if curriculum.should_advance_stage(performance_metrics):
    print("满足进入下一阶段的条件！")
    curriculum.advance_to_next_stage()
else:
    print("尚未满足进入下一阶段的条件")
    print("需要满足的标准:", current.evaluation_criteria)
```

### 示例 2: 在训练循环中使用

```python
# 在训练循环中
for iteration in range(num_iterations):
    # ... 训练代码 ...
    
    # 收集性能指标
    performance_metrics = {
        'iteration': iteration + 1,
        'win_rate': evaluator.get_win_rate(),
        'elo_rating': evaluator.get_model_elo(model_id),
        'avg_score': evaluator.get_avg_score(),
    }
    
    # 课程学习阶段调整（每 N 次迭代）
    if curriculum and (iteration + 1) % 100 == 0:
        # 生成课程规划文档
        current_issues = []  # 可以从评估结果中提取
        doc_path = curriculum.design_next_stage(
            performance_metrics=performance_metrics,
            current_issues=current_issues,
            iteration=iteration + 1,
        )
        if doc_path:
            print(f"课程规划文档已生成: {doc_path}")
        
        # 检查是否应该推进阶段
        if curriculum.should_advance_stage(performance_metrics):
            curriculum.advance_to_next_stage()
            print(f"进入下一阶段: {curriculum.current_stage.value}")
```

### 示例 3: 手动推进阶段

```python
# 手动推进到指定阶段
curriculum.current_stage = TrainingStage.DEFENSIVE
print(f"当前阶段: {curriculum.current_stage.value}")

# 获取该阶段的课程
current = curriculum.get_current_curriculum()
print(f"课程名称: {current.name}")
print(f"课程描述: {current.description}")
```

## 自定义评估标准

您可以修改 `curriculum.py` 中的评估标准：

```python
# 在 get_current_curriculum() 方法中
evaluation_criteria={
    'win_rate': 0.3,           # 胜率至少 30%
    'flower_pig_rate': 0.05,   # 花猪率低于 5%
    'elo_score': 1200,         # Elo 分数至少 1200
    'avg_score': 5.0,          # 平均得分至少 5.0
}
```

## 与大模型分析结合

### 1. 生成课程规划文档

系统会自动生成文档，或手动生成：

```python
doc_path = curriculum.design_next_stage(
    performance_metrics=metrics,
    current_issues=['问题1', '问题2'],
    iteration=1000,
)
```

### 2. 提交给大模型

打开生成的文档 `curriculum_design_1000.md`，复制内容，提交给大模型（ChatGPT、Claude 等）进行分析。

### 3. 根据分析结果调整

大模型可能会建议：
- 调整评估标准
- 修改训练目标
- 调整阶段推进条件

您可以根据建议修改 `curriculum.py` 中的代码。

## 配置选项

### config.yaml

```yaml
curriculum_learning:
  enabled: true                # 是否启用课程学习
  initial_stage: basic         # 初始阶段
  llm_coach_frequency: 100    # 文档生成频率
  document_output_dir: ./coach_documents  # 文档输出目录
```

### 初始阶段选项

- `basic`: 基础阶段
- `defensive`: 防御阶段
- `advanced`: 高级阶段
- `expert`: 专家阶段

## 监控和调试

### 查看当前阶段

```python
print(f"当前阶段: {curriculum.current_stage.value}")
current = curriculum.get_current_curriculum()
print(f"课程名称: {current.name}")
print(f"评估标准: {current.evaluation_criteria}")
```

### 查看阶段历史

```python
for step in curriculum.curriculum_history:
    print(f"阶段: {step.stage.value}")
    print(f"名称: {step.name}")
    print(f"目标: {step.objectives}")
```

### 检查性能指标

```python
performance_metrics = {
    'win_rate': 0.35,
    'elo_score': 1500,
    'avg_score': 10.0,
}

# 检查是否满足当前阶段标准
current = curriculum.get_current_curriculum()
for criterion, threshold in current.evaluation_criteria.items():
    value = performance_metrics.get(criterion, 0)
    status = "✓" if value >= threshold else "✗"
    print(f"{status} {criterion}: {value} (需要 ≥ {threshold})")
```

## 常见问题

### Q1: 如何跳过某个阶段？

A: 手动设置阶段：

```python
curriculum.current_stage = TrainingStage.ADVANCED
```

### Q2: 如何自定义评估标准？

A: 修改 `curriculum.py` 中 `get_current_curriculum()` 方法的 `evaluation_criteria`。

### Q3: 阶段推进太慢怎么办？

A: 降低评估标准的阈值，或手动推进阶段。

### Q4: 如何查看是否满足进入下一阶段的条件？

A: 使用 `should_advance_stage()` 方法：

```python
if curriculum.should_advance_stage(performance_metrics):
    print("可以进入下一阶段")
else:
    print("尚未满足条件")
```

### Q5: 课程规划文档在哪里？

A: 默认在 `./coach_documents/` 目录下，文件名格式为 `curriculum_design_{iteration}.md`。

## 最佳实践

1. **合理设置评估标准**: 不要设置过高的标准，避免 AI 长时间停留在某个阶段
2. **定期检查性能**: 每 100-200 次迭代检查一次性能指标
3. **使用文档分析**: 定期生成课程规划文档，提交给大模型分析
4. **灵活调整**: 根据实际情况调整评估标准和阶段推进条件
5. **保存阶段历史**: 记录每个阶段的训练历史，便于分析

## 总结

课程学习通过分阶段训练，帮助 AI 从简单到复杂逐步学习。系统会自动判断阶段推进，并生成分析文档。您可以根据实际情况调整评估标准和训练目标，实现更高效的训练。

