# Coach 模块

生成训练分析文档，供手动提交给大模型进行分析。

## 功能模块

### 1. 游戏日志记录器 (GameLogger)

将关键决策点序列化为结构化JSON，用于生成分析文档。

**使用示例**:
```python
from scai.coach import GameLogger

logger = GameLogger(log_dir='./logs')

# 记录决策
logger.log_decision(
    state={'hand': '1W 2W 3W', 'declared_suit': 'Tong'},
    action='Discard 3W',
    reward=-5.0,
    was_winning_tile=True,
    is_ready=True,
)

# 结束游戏
logger.finish_game(game_id=0)
```

### 2. 训练文档生成器 (TrainingDocumentGenerator)

生成结构化的训练分析文档，包括策略分析、奖励函数评价和课程学习规划。

**使用示例**:
```python
from scai.coach import TrainingDocumentGenerator

generator = TrainingDocumentGenerator(output_dir='./coach_documents')

# 生成策略分析文档
strategy_doc = generator.generate_strategy_analysis_document(
    game_logs=game_logs,
    performance_metrics={'win_rate': 0.5, 'avg_score': 10.0},
    iteration=1000,
)

# 生成奖励函数评价文档
reward_doc = generator.generate_reward_evaluation_document(
    reward_config={'ready_reward': 0.1, 'hu_reward': 1.0},
    loss_curve=[...],
    elo_scores=[...],
    iteration=1000,
)

# 生成课程学习规划文档
curriculum_doc = generator.generate_curriculum_design_document(
    current_stage='基础阶段',
    performance_metrics={'win_rate': 0.5},
    issues=['过度保守', '不敢博清一色'],
    iteration=1000,
)
```

### 3. 自动化反馈机制 (TrainingMonitor)

定期生成训练报告和分析文档。

**使用示例**:
```python
from scai.coach import TrainingMonitor, ReportGenerator, TrainingDocumentGenerator

document_generator = TrainingDocumentGenerator(output_dir='./coach_documents')

monitor = TrainingMonitor(
    logger=logger,
    document_generator=document_generator,
    report_generator=ReportGenerator(),
    check_interval=1000,  # 每1000个epoch检查一次
)

# 在训练循环中
for iteration in range(num_iterations):
    # ... 训练代码 ...
    
    # 更新指标
    monitor.update_metrics(loss=current_loss, elo_score=current_elo)
    
    # 检查并生成文档
    doc_paths = monitor.check_and_generate_documents(
        iteration=iteration,
        training_stats=stats,
        reward_config=reward_config,
    )
    
    if doc_paths:
        # 文档已生成，可以手动提交给大模型分析
        print(f"策略分析文档: {doc_paths['strategy_analysis']}")
        print(f"奖励函数评价文档: {doc_paths['reward_evaluation']}")
```

### 4. 课程学习规划 (CurriculumLearning)

设计分阶段的训练课程，生成课程规划文档。

**使用示例**:
```python
from scai.coach import CurriculumLearning, TrainingDocumentGenerator, TrainingStage

document_generator = TrainingDocumentGenerator(output_dir='./coach_documents')
curriculum = CurriculumLearning(document_generator=document_generator)

# 获取当前课程
current = curriculum.get_current_curriculum()
print(f"当前阶段: {current.name}")
print(f"训练目标: {current.objectives}")

# 检查是否应该进入下一阶段
if curriculum.should_advance_stage(performance_metrics):
    # 生成课程规划文档（供手动提交给大模型）
    doc_path = curriculum.design_next_stage(
        performance_metrics=metrics,
        current_issues=['过度保守', '不敢博清一色'],
        iteration=1000,
    )
    
    # 进入下一阶段
    curriculum.advance_to_next_stage()
```

## 训练阶段

1. **基础阶段 (BASIC)**: 学习定缺和基本胡牌
2. **防御阶段 (DEFENSIVE)**: 学习避炮策略
3. **高级阶段 (ADVANCED)**: 学习博弈高阶策略
4. **专家阶段 (EXPERT)**: 学习复杂策略组合

## 工作流程

1. **训练过程中** - 系统自动生成分析文档
2. **手动提交** - 将文档复制并提交给大模型（ChatGPT、Claude、Gemini等）
3. **获取分析** - 大模型提供分析结果和建议
4. **应用调整** - 根据分析结果手动调整训练参数

## 文档格式

生成的文档为 Markdown 格式，包含：
- 性能指标概览
- 详细游戏日志
- 分析任务说明
- 请求的分析结果格式

## 注意事项

1. **文档生成频率** - 建议设置为 50-200 次迭代，避免过于频繁
2. **文档大小** - 系统会自动限制游戏日志数量，避免文档过大
3. **手动处理** - 需要手动将文档提交给大模型，系统不会自动调用 API
4. **结果应用** - 分析结果需要手动应用到配置文件中

## 详细使用指南

请参考 `python/COACH_MODULE_GUIDE.md` 获取详细的使用指南。
