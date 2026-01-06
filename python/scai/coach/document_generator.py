"""
训练文档生成器 (Training Document Generator)

生成训练分析文档，供手动提交给大模型进行分析。
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


class TrainingDocumentGenerator:
    """训练文档生成器
    
    生成结构化的训练分析文档，包括：
    - 策略分析文档
    - 奖励函数评价文档
    - 课程学习规划文档
    """
    
    def __init__(self, output_dir: str = './coach_documents'):
        """
        参数：
        - output_dir: 文档输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_strategy_analysis_document(
        self,
        game_logs: List[Dict[str, Any]],
        performance_metrics: Dict[str, float],
        focus_anomalies: bool = True,
        iteration: Optional[int] = None,
    ) -> str:
        """
        生成策略分析文档
        
        参数：
        - game_logs: 游戏日志列表
        - performance_metrics: 性能指标
        - focus_anomalies: 是否重点关注异常决策
        - iteration: 当前迭代次数
        
        返回：
        - 文档文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'strategy_analysis_{iteration or timestamp}.md'
        filepath = self.output_dir / filename
        
        # 构建文档内容
        content = self._build_strategy_analysis_content(
            game_logs,
            performance_metrics,
            focus_anomalies,
            iteration,
        )
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"策略分析文档已生成: {filepath}")
        return str(filepath)
    
    def generate_reward_evaluation_document(
        self,
        reward_config: Dict[str, Any],
        loss_curve: List[float],
        elo_scores: List[float],
        behavior_issues: Optional[List[str]] = None,
        iteration: Optional[int] = None,
    ) -> str:
        """
        生成奖励函数评价文档
        
        参数：
        - reward_config: 当前奖励函数配置
        - loss_curve: 损失曲线数据
        - elo_scores: Elo分数历史
        - behavior_issues: 行为问题描述
        - iteration: 当前迭代次数
        
        返回：
        - 文档文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'reward_evaluation_{iteration or timestamp}.md'
        filepath = self.output_dir / filename
        
        # 构建文档内容
        content = self._build_reward_evaluation_content(
            reward_config,
            loss_curve,
            elo_scores,
            behavior_issues,
            iteration,
        )
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"奖励函数评价文档已生成: {filepath}")
        return str(filepath)
    
    def generate_curriculum_design_document(
        self,
        current_stage: str,
        performance_metrics: Dict[str, float],
        issues: List[str],
        iteration: Optional[int] = None,
    ) -> str:
        """
        生成课程学习规划文档
        
        参数：
        - current_stage: 当前训练阶段
        - performance_metrics: 性能指标
        - issues: 当前阶段的问题列表
        - iteration: 当前迭代次数
        
        返回：
        - 文档文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'curriculum_design_{iteration or timestamp}.md'
        filepath = self.output_dir / filename
        
        # 构建文档内容
        content = self._build_curriculum_design_content(
            current_stage,
            performance_metrics,
            issues,
            iteration,
        )
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"课程学习规划文档已生成: {filepath}")
        return str(filepath)
    
    def _build_strategy_analysis_content(
        self,
        game_logs: List[Dict[str, Any]],
        performance_metrics: Dict[str, float],
        focus_anomalies: bool,
        iteration: Optional[int],
    ) -> str:
        """构建策略分析文档内容"""
        content = f"""# 策略分析文档

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**迭代次数**: {iteration or 'N/A'}
**重点关注**: {'异常决策' if focus_anomalies else '整体策略'}

---

## 一、性能指标概览

```json
{json.dumps(performance_metrics, ensure_ascii=False, indent=2)}
```

---

## 二、游戏日志

### 2.1 日志统计

- **总游戏数**: {len(game_logs)}
- **平均得分**: {performance_metrics.get('avg_score', 0.0):.2f}
- **胜率**: {performance_metrics.get('win_rate', 0.0):.2%}
- **Elo评分**: {performance_metrics.get('elo_rating', 0.0):.2f}

### 2.2 详细游戏日志

"""
        
        # 添加游戏日志（限制数量，避免文档过长）
        max_logs = 10
        for i, log in enumerate(game_logs[:max_logs]):
            content += f"""
#### 游戏 {i + 1}

```json
{json.dumps(log, ensure_ascii=False, indent=2)}
```
"""
        
        if len(game_logs) > max_logs:
            content += f"\n*（仅显示前 {max_logs} 局游戏，共 {len(game_logs)} 局）*\n"
        
        content += """
---

## 三、分析任务

请从以下角度分析AI的策略：

### 3.1 策略合理性
- AI的决策是否符合麻将策略？
- 是否存在明显的逻辑错误？
- 决策是否符合"最大化期望收益"原则？

### 3.2 风险控制
- AI是否过度保守（不敢博大牌）？
- AI是否过度冒险（频繁点炮）？
- 风险控制是否合理？

### 3.3 机会把握
- AI是否错过了高价值机会（如清一色、七对等）？
- AI是否在关键时刻选择了次优策略？
- 机会识别能力如何？

### 3.4 规则理解
- AI是否正确理解了游戏规则？
- 是否存在规则理解错误？
- 定缺、过胡、查大叫等规则是否被正确应用？

---

## 四、请提供分析结果

请提供以下内容：

1. **发现的主要问题**（3-5个）
   - 问题描述
   - 问题影响
   - 问题示例

2. **具体的改进建议**
   - 针对每个问题的改进方案
   - 可操作的建议

3. **策略评分**（0-100分）
   - 整体策略评分
   - 各维度评分（策略合理性、风险控制、机会把握、规则理解）

4. **优先级建议**
   - 哪些问题需要优先解决？
   - 改进的优先级排序

---

**请将分析结果保存为 `strategy_analysis_result_{timestamp}.md` 文件，或直接回复。**
"""
        
        return content
    
    def _build_reward_evaluation_content(
        self,
        reward_config: Dict[str, Any],
        loss_curve: List[float],
        elo_scores: List[float],
        behavior_issues: Optional[List[str]],
        iteration: Optional[int],
    ) -> str:
        """构建奖励函数评价文档内容"""
        
        # 计算趋势
        loss_trend = self._describe_trend(loss_curve)
        elo_trend = self._describe_trend(elo_scores)
        
        # 计算统计信息
        recent_loss = loss_curve[-10:] if len(loss_curve) > 10 else loss_curve
        recent_elo = elo_scores[-10:] if len(elo_scores) > 10 else elo_scores
        
        content = f"""# 奖励函数评价文档

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**迭代次数**: {iteration or 'N/A'}

---

## 一、当前奖励函数配置

```json
{json.dumps(reward_config, ensure_ascii=False, indent=2)}
```

---

## 二、训练数据

### 2.1 损失曲线

- **当前损失**: {loss_curve[-1] if loss_curve else 'N/A':.4f}
- **平均损失**: {sum(loss_curve) / len(loss_curve) if loss_curve else 'N/A':.4f}
- **最近10次平均**: {sum(recent_loss) / len(recent_loss) if recent_loss else 'N/A':.4f}
- **趋势**: {loss_trend}

**损失曲线数据**（最近20次）:
```
{', '.join([f'{x:.4f}' for x in loss_curve[-20:]]) if len(loss_curve) > 0 else 'N/A'}
```

### 2.2 Elo评分历史

- **当前Elo**: {elo_scores[-1] if elo_scores else 'N/A':.2f}
- **平均Elo**: {sum(elo_scores) / len(elo_scores) if elo_scores else 'N/A':.2f}
- **最近10次平均**: {sum(recent_elo) / len(recent_elo) if recent_elo else 'N/A':.2f}
- **趋势**: {elo_trend}

**Elo评分数据**（最近20次）:
```
{', '.join([f'{x:.2f}' for x in elo_scores[-20:]]) if len(elo_scores) > 0 else 'N/A'}
```

### 2.3 行为问题

"""
        
        if behavior_issues:
            for issue in behavior_issues:
                content += f"- {issue}\n"
        else:
            content += "- 未发现明显行为问题\n"
        
        content += """
---

## 三、分析任务

请从以下角度评价当前的奖励函数：

### 3.1 奖励机制问题诊断
- 当前奖励机制是否存在问题？
- 是否存在奖励稀疏或奖励过密的问题？
- 奖励是否与最终目标（得分）对齐？

### 3.2 行为偏差分析
- 是否过度惩罚了点炮，导致AI不敢博清一色？
- 是否过度奖励了保守策略？
- 是否忽略了某些重要行为（如过胡、杠牌）？

### 3.3 参数调整建议
- 是否需要调整Entropy Loss系数？
- 是否需要调整Reward Scale？
- 是否需要调整各奖励项的权重？

### 3.4 奖励函数设计
- 当前奖励函数设计是否合理？
- 是否需要添加新的奖励项？
- 是否需要移除某些奖励项？

---

## 四、请提供评价结果

请提供以下内容：

1. **问题诊断**
   - 当前奖励机制存在的主要问题
   - 问题的影响和严重程度

2. **调整建议**
   - 具体的参数调整建议
   - 调整的预期效果

3. **建议的新配置**
   ```json
   {{
     "ready_reward": 0.1,
     "hu_reward": 1.0,
     "flower_pig_penalty": -5.0,
     "final_score_weight": 1.0,
     "entropy_coef": 0.01,
     "value_coef": 0.5,
     ...
   }}
   ```

4. **实施优先级**
   - 哪些调整需要优先实施？
   - 调整的优先级排序

---

**请将评价结果保存为 `reward_evaluation_result_{timestamp}.md` 文件，或直接回复。**
"""
        
        return content
    
    def _build_curriculum_design_content(
        self,
        current_stage: str,
        performance_metrics: Dict[str, float],
        issues: List[str],
        iteration: Optional[int],
    ) -> str:
        """构建课程学习规划文档内容"""
        
        content = f"""# 课程学习规划文档

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**迭代次数**: {iteration or 'N/A'}
**当前阶段**: {current_stage}

---

## 一、当前阶段性能指标

```json
{json.dumps(performance_metrics, ensure_ascii=False, indent=2)}
```

---

## 二、当前阶段问题

"""
        
        for i, issue in enumerate(issues, 1):
            content += f"{i}. {issue}\n"
        
        if not issues:
            content += "- 未发现明显问题\n"
        
        content += """
---

## 三、设计任务

请设计下一阶段的训练课程：

### 3.1 训练目标
- 下一阶段应该达到什么目标？
- 需要解决哪些问题？
- 需要学习哪些新技能？

### 3.2 课程步骤
- 分阶段的课程步骤（例如：第一阶段学定缺和基本胡牌，第二阶段引入避炮策略）
- 每个步骤的具体内容
- 步骤之间的递进关系

### 3.3 评估标准
- 每个阶段的评估标准
- 如何判断是否应该进入下一阶段？
- 评估指标和阈值

### 3.4 训练参数调整
- 是否需要调整学习率？
- 是否需要调整批次大小？
- 是否需要调整其他超参数？

---

## 四、请提供课程规划

请提供以下内容：

1. **下一阶段名称**
   - 阶段名称
   - 阶段描述

2. **训练目标**
   - 主要目标（3-5个）
   - 每个目标的具体描述

3. **课程步骤**
   ```json
   [
     {{
       "step": 1,
       "name": "步骤名称",
       "description": "步骤描述",
       "objectives": ["目标1", "目标2"],
       "estimated_iterations": 10000
     }},
     ...
   ]
   ```

4. **评估标准**
   ```json
   {{
     "win_rate": 0.4,
     "elo_score": 1200,
     "avg_score": 5.0,
     ...
   }}
   ```

5. **训练参数建议**
   ```json
   {{
     "learning_rate": 3e-4,
     "batch_size": 4096,
     "num_epochs": 10,
     ...
   }}
   ```

---

**请将课程规划保存为 `curriculum_design_result_{timestamp}.md` 文件，或直接回复。**
"""
        
        return content
    
    def _describe_trend(self, values: List[float]) -> str:
        """描述数值趋势"""
        if len(values) < 2:
            return "数据不足"
        
        recent = values[-10:] if len(values) > 10 else values
        if recent[-1] > recent[0] * 1.1:
            return "明显上升趋势"
        elif recent[-1] < recent[0] * 0.9:
            return "明显下降趋势"
        elif recent[-1] > recent[0]:
            return "轻微上升趋势"
        elif recent[-1] < recent[0]:
            return "轻微下降趋势"
        else:
            return "平稳"

