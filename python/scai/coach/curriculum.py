"""
课程学习规划 (Curriculum Learning)

根据大模型的建议，设计分阶段的训练课程。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .llm_interface import LLMCoach


class TrainingStage(Enum):
    """训练阶段"""
    BASIC = "基础阶段"  # 学习定缺和基本胡牌
    DEFENSIVE = "防御阶段"  # 学习避炮策略
    ADVANCED = "高级阶段"  # 学习博弈高阶策略
    EXPERT = "专家阶段"  # 学习复杂策略组合


@dataclass
class CurriculumStep:
    """课程步骤"""
    stage: TrainingStage
    name: str
    description: str
    objectives: List[str]
    evaluation_criteria: Dict[str, float]
    estimated_iterations: int


class CurriculumLearning:
    """课程学习规划器"""
    
    def __init__(self, llm_coach: LLMCoach):
        """
        参数：
        - llm_coach: 大模型教练
        """
        self.llm_coach = llm_coach
        self.current_stage = TrainingStage.BASIC
        self.curriculum_history: List[CurriculumStep] = []
    
    def get_current_curriculum(self) -> CurriculumStep:
        """获取当前课程步骤"""
        # 根据当前阶段返回对应的课程步骤
        if self.current_stage == TrainingStage.BASIC:
            return CurriculumStep(
                stage=TrainingStage.BASIC,
                name="基础阶段：定缺和基本胡牌",
                description="学习基本的定缺策略和常见胡牌类型",
                objectives=[
                    "正确选择定缺花色",
                    "识别基本胡牌类型（平胡、七对等）",
                    "理解缺一门规则",
                ],
                evaluation_criteria={
                    'win_rate': 0.3,  # 胜率至少30%
                    'flower_pig_rate': 0.05,  # 花猪率低于5%
                },
                estimated_iterations=10000,
            )
        elif self.current_stage == TrainingStage.DEFENSIVE:
            return CurriculumStep(
                stage=TrainingStage.DEFENSIVE,
                name="防御阶段：避炮策略",
                description="学习如何避免点炮，提高防御能力",
                objectives=[
                    "识别危险牌",
                    "避免在关键时刻点炮",
                    "学会过胡策略",
                ],
                evaluation_criteria={
                    'discard_win_rate': 0.1,  # 点炮率低于10%
                    'defensive_score': 0.7,  # 防御得分至少70%
                },
                estimated_iterations=20000,
            )
        elif self.current_stage == TrainingStage.ADVANCED:
            return CurriculumStep(
                stage=TrainingStage.ADVANCED,
                name="高级阶段：博弈策略",
                description="学习高级博弈策略，包括杠牌、听牌选择等",
                objectives=[
                    "学会杠牌时机选择",
                    "优化听牌选择",
                    "理解期望收益计算",
                ],
                evaluation_criteria={
                    'elo_score': 1500,  # Elo分数至少1500
                    'average_score': 10.0,  # 平均得分至少10分
                },
                estimated_iterations=30000,
            )
        else:  # EXPERT
            return CurriculumStep(
                stage=TrainingStage.EXPERT,
                name="专家阶段：复杂策略组合",
                description="学习复杂策略组合，达到专家水平",
                objectives=[
                    "掌握所有高级策略",
                    "优化策略组合",
                    "达到专家水平",
                ],
                evaluation_criteria={
                    'elo_score': 2000,  # Elo分数至少2000
                    'win_rate': 0.5,  # 胜率至少50%
                },
                estimated_iterations=50000,
            )
    
    def should_advance_stage(
        self,
        performance_metrics: Dict[str, float],
    ) -> bool:
        """
        判断是否应该进入下一阶段
        
        参数：
        - performance_metrics: 性能指标
        
        返回：
        - 是否应该进入下一阶段
        """
        current_curriculum = self.get_current_curriculum()
        
        # 检查是否满足当前阶段的评估标准
        for criterion, threshold in current_curriculum.evaluation_criteria.items():
            if criterion in performance_metrics:
                if performance_metrics[criterion] < threshold:
                    return False
            else:
                # 如果缺少关键指标，暂时不推进
                return False
        
        return True
    
    def design_next_stage(
        self,
        performance_metrics: Dict[str, float],
        current_issues: List[str],
    ) -> CurriculumStep:
        """
        设计下一阶段的课程（使用大模型）
        
        参数：
        - performance_metrics: 性能指标
        - current_issues: 当前阶段的问题列表
        
        返回：
        - 下一阶段的课程步骤
        """
        # 调用大模型设计课程
        curriculum_design = self.llm_coach.design_curriculum(
            current_stage=self.current_stage.value,
            performance_metrics=performance_metrics,
            issues=current_issues,
        )
        
        # 解析大模型的响应，创建课程步骤
        next_stage = self._get_next_stage()
        
        curriculum_step = CurriculumStep(
            stage=next_stage,
            name=curriculum_design.get('next_stage', next_stage.value),
            description=curriculum_design.get('raw_response', ''),
            objectives=curriculum_design.get('training_objectives', []),
            evaluation_criteria=self._extract_criteria(curriculum_design),
            estimated_iterations=self._estimate_iterations(next_stage),
        )
        
        self.curriculum_history.append(curriculum_step)
        
        return curriculum_step
    
    def advance_to_next_stage(self):
        """推进到下一阶段"""
        stages = list(TrainingStage)
        current_index = stages.index(self.current_stage)
        
        if current_index < len(stages) - 1:
            self.current_stage = stages[current_index + 1]
            print(f"[CurriculumLearning] 进入下一阶段: {self.current_stage.value}")
        else:
            print("[CurriculumLearning] 已达到最高阶段")
    
    def _get_next_stage(self) -> TrainingStage:
        """获取下一阶段"""
        stages = list(TrainingStage)
        current_index = stages.index(self.current_stage)
        
        if current_index < len(stages) - 1:
            return stages[current_index + 1]
        else:
            return self.current_stage
    
    def _extract_criteria(self, curriculum_design: Dict[str, Any]) -> Dict[str, float]:
        """从大模型响应中提取评估标准"""
        # 默认评估标准
        default_criteria = {
            'win_rate': 0.4,
            'elo_score': 1200,
        }
        
        # 尝试从响应中提取
        # 这里可以添加更复杂的解析逻辑
        
        return default_criteria
    
    def _estimate_iterations(self, stage: TrainingStage) -> int:
        """估算阶段所需的迭代次数"""
        estimates = {
            TrainingStage.BASIC: 10000,
            TrainingStage.DEFENSIVE: 20000,
            TrainingStage.ADVANCED: 30000,
            TrainingStage.EXPERT: 50000,
        }
        return estimates.get(stage, 20000)

