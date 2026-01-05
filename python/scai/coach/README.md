# 大模型总教练 (LLM Coach)

使用大模型监督和指导AI训练的系统。

## 功能模块

### 1. 游戏日志记录器 (GameLogger)

将关键决策点序列化为结构化JSON，用于大模型分析。

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

### 2. 大模型监督接口 (LLMCoach)

调用大模型API进行策略分析、奖励函数评价和课程学习规划。

**配置**:
```python
from scai.coach import LLMCoach, LLMCoachConfig

# 配置（支持OpenAI、Anthropic等）
config = LLMCoachConfig(
    api_type='openai',
    model_name='gpt-4',
    api_key=os.getenv('OPENAI_API_KEY'),
)

coach = LLMCoach(config)
```

**策略分析**:
```python
# 分析策略合理性
analysis = coach.analyze_strategy(game_logs, focus_anomalies=True)
print(analysis['issues'])  # 发现的问题
print(analysis['suggestions'])  # 改进建议
```

**奖励函数评价**:
```python
# 评价奖励函数
evaluation = coach.evaluate_reward_function(
    reward_config={'ready_reward': 0.1, 'hu_reward': 1.0},
    loss_curve=[...],
    elo_scores=[...],
    behavior_issues=['过度保守', '不敢博清一色'],
)
```

### 3. 自动化反馈机制 (TrainingMonitor)

定期生成训练报告并调用大模型进行分析。

**使用示例**:
```python
from scai.coach import TrainingMonitor, ReportGenerator

monitor = TrainingMonitor(
    logger=logger,
    llm_coach=coach,
    report_generator=ReportGenerator(),
    check_interval=1000,  # 每1000个epoch检查一次
)

# 在训练循环中
for iteration in range(num_iterations):
    # ... 训练代码 ...
    
    # 更新指标
    monitor.update_metrics(loss=current_loss, elo_score=current_elo)
    
    # 检查并分析
    analysis = monitor.check_and_analyze(
        iteration=iteration,
        training_stats=stats,
        reward_config=reward_config,
    )
    
    if analysis:
        # 根据分析结果调整训练参数
        suggestions = analysis['strategy_analysis']['suggestions']
        # ... 应用建议 ...
```

### 4. 课程学习规划 (CurriculumLearning)

根据大模型的建议，设计分阶段的训练课程。

**使用示例**:
```python
from scai.coach import CurriculumLearning

curriculum = CurriculumLearning(llm_coach=coach)

# 获取当前课程
current = curriculum.get_current_curriculum()
print(f"当前阶段: {current.name}")
print(f"训练目标: {current.objectives}")

# 检查是否应该进入下一阶段
if curriculum.should_advance_stage(performance_metrics):
    # 设计下一阶段
    next_stage = curriculum.design_next_stage(
        performance_metrics=metrics,
        current_issues=['过度保守', '不敢博清一色'],
    )
    
    # 进入下一阶段
    curriculum.advance_to_next_stage()
```

## 训练阶段

1. **基础阶段 (BASIC)**: 学习定缺和基本胡牌
2. **防御阶段 (DEFENSIVE)**: 学习避炮策略
3. **高级阶段 (ADVANCED)**: 学习博弈高阶策略
4. **专家阶段 (EXPERT)**: 学习复杂策略组合

## 环境变量

设置API密钥：
```bash
export OPENAI_API_KEY="your-api-key"
# 或
export ANTHROPIC_API_KEY="your-api-key"
```

## 注意事项

1. **数据抽样**: 不要发原始Tensor，要发人类可读的"牌谱"
2. **关注异常值**: 专门把那些Loss极高或Elo分数突然下降的对局发给大模型分析
3. **对抗性测试**: 让大模型出一些"死局"或"诱导局"给Rust引擎，看AI在这种特殊环境下的胜率

