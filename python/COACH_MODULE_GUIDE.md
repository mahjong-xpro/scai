# Coach 模块使用指南

## 概述

Coach 模块用于生成训练分析文档，供手动提交给大模型进行分析。**不直接调用大模型 API**，而是生成结构化的 Markdown 文档，您可以手动复制这些文档并提交给大模型（如 ChatGPT、Claude、Gemini 等）进行分析。

## 功能

Coach 模块提供以下三种文档生成功能：

1. **策略分析文档** - 分析 AI 的策略合理性
2. **奖励函数评价文档** - 评价当前奖励函数配置
3. **课程学习规划文档** - 设计下一阶段的训练课程

## 使用方法

### 1. 在训练脚本中启用

在 `config.yaml` 中启用课程学习：

```yaml
curriculum_learning:
  enabled: true
  initial_stage: basic
  llm_coach_frequency: 100  # 每 100 次迭代生成一次文档
  document_output_dir: ./coach_documents
```

### 2. 自动生成文档

训练过程中，系统会在指定频率自动生成文档：

- **策略分析文档**: `strategy_analysis_{iteration}.md`
- **奖励函数评价文档**: `reward_evaluation_{iteration}.md`
- **课程学习规划文档**: `curriculum_design_{iteration}.md`

### 3. 手动提交给大模型

1. 打开生成的文档文件
2. 复制文档内容
3. 提交给大模型（ChatGPT、Claude、Gemini 等）
4. 获取分析结果

### 4. 应用分析结果

根据大模型的分析结果，您可以：

- **调整奖励函数参数** - 修改 `config.yaml` 中的奖励配置
- **调整训练参数** - 修改学习率、批次大小等
- **推进训练阶段** - 根据课程规划推进到下一阶段

## 文档格式

### 策略分析文档

包含：
- 性能指标概览
- 详细游戏日志
- 分析任务（策略合理性、风险控制、机会把握、规则理解）
- 请求的分析结果格式

### 奖励函数评价文档

包含：
- 当前奖励函数配置
- 训练数据（损失曲线、Elo 评分）
- 行为问题描述
- 分析任务（奖励机制问题、行为偏差、参数调整）
- 请求的评价结果格式

### 课程学习规划文档

包含：
- 当前阶段性能指标
- 当前阶段问题
- 设计任务（训练目标、课程步骤、评估标准）
- 请求的课程规划格式

## 示例工作流

1. **训练开始** - 系统自动生成初始文档
2. **定期生成** - 每 N 次迭代生成新的文档
3. **手动分析** - 将文档提交给大模型
4. **获取建议** - 大模型提供分析结果和建议
5. **应用调整** - 根据建议调整训练参数
6. **继续训练** - 继续训练并观察效果

## 注意事项

1. **文档生成频率** - 建议设置为 50-200 次迭代，避免过于频繁
2. **文档大小** - 系统会自动限制游戏日志数量，避免文档过大
3. **手动处理** - 需要手动将文档提交给大模型，系统不会自动调用 API
4. **结果应用** - 分析结果需要手动应用到配置文件中

## 高级用法

### 自定义文档生成

您也可以手动调用文档生成器：

```python
from scai.coach.document_generator import TrainingDocumentGenerator

generator = TrainingDocumentGenerator(output_dir='./my_documents')

# 生成策略分析文档
doc_path = generator.generate_strategy_analysis_document(
    game_logs=game_logs,
    performance_metrics=metrics,
    iteration=1000,
)

# 生成奖励函数评价文档
doc_path = generator.generate_reward_evaluation_document(
    reward_config=config,
    loss_curve=losses,
    elo_scores=elos,
    iteration=1000,
)

# 生成课程学习规划文档
doc_path = generator.generate_curriculum_design_document(
    current_stage='基础阶段',
    performance_metrics=metrics,
    issues=['问题1', '问题2'],
    iteration=1000,
)
```

## 文件结构

```
coach_documents/
├── strategy_analysis_100.md
├── strategy_analysis_200.md
├── reward_evaluation_100.md
├── reward_evaluation_200.md
├── curriculum_design_100.md
└── curriculum_design_200.md
```

## 总结

Coach 模块采用"生成文档 + 手动分析"的方式，避免了 API 调用的复杂性和成本，同时保持了灵活性和可控性。您可以根据需要选择合适的大模型进行分析，并根据分析结果灵活调整训练策略。

