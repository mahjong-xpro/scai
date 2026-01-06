"""
课程学习规划 (Curriculum Learning)

根据大模型的建议，设计分阶段的训练课程。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class TrainingStage(Enum):
    """训练阶段"""
    # 初期阶段（0基础数据）
    DECLARE_SUIT = "定缺阶段"  # 学习定缺规则和选择
    LEARN_WIN = "学胡阶段"  # 学习基本胡牌（使用喂牌）
    BASIC = "基础阶段"  # 学习定缺和基本胡牌（正常牌局）
    
    # 进阶阶段
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
    min_iterations: int = 0  # 最小迭代次数（达到此值后才考虑推进）
    max_iterations: int = 0  # 最大迭代次数（达到此值后强制推进，0表示不限制）
    use_feeding_games: bool = False  # 是否使用喂牌模式（生成更容易学习的牌局）


class CurriculumLearning:
    """课程学习规划器"""
    
    def __init__(self, document_generator=None):
        """
        参数：
        - document_generator: 文档生成器（可选）
        """
        self.document_generator = document_generator
        self.current_stage = TrainingStage.DECLARE_SUIT  # 从定缺阶段开始
        self.curriculum_history: List[CurriculumStep] = []
        self.use_feeding_games = False  # 是否使用喂牌模式
    
    def get_current_curriculum(self) -> CurriculumStep:
        """获取当前课程步骤"""
        # 根据当前阶段返回对应的课程步骤
        if self.current_stage == TrainingStage.DECLARE_SUIT:
            return CurriculumStep(
                stage=TrainingStage.DECLARE_SUIT,
                name="定缺阶段：学习定缺规则",
                description="学习定缺规则，理解缺一门的概念",
                objectives=[
                    "理解定缺规则",
                    "学会选择定缺花色",
                    "避免成为花猪",
                ],
                evaluation_criteria={
                    'flower_pig_rate': 0.50,  # 花猪率低于50%（初期非常宽松）
                    'declare_suit_correct_rate': 0.60,  # 定缺选择正确率至少60%
                    'games_played': 500,  # 至少完成500局游戏
                },
                estimated_iterations=5000,
                min_iterations=2000,  # 至少训练2000次迭代
                max_iterations=8000,  # 最多8000次迭代后强制推进
            )
        elif self.current_stage == TrainingStage.LEARN_WIN:
            return CurriculumStep(
                stage=TrainingStage.LEARN_WIN,
                name="学胡阶段：学习基本胡牌（喂牌模式）",
                description="使用喂牌机制，学习基本胡牌类型",
                objectives=[
                    "识别基本胡牌类型（平胡、七对等）",
                    "理解听牌概念",
                    "学会主动胡牌",
                ],
                evaluation_criteria={
                    'win_rate': 0.20,  # 胜率至少20%（喂牌模式下更容易达到）
                    'ready_rate': 0.30,  # 听牌率至少30%
                    'hu_types_learned': 2,  # 至少学会2种胡牌类型
                    'games_played': 1000,  # 至少完成1000局游戏
                },
                estimated_iterations=8000,
                min_iterations=4000,  # 至少训练4000次迭代
                max_iterations=12000,  # 最多12000次迭代后强制推进
                use_feeding_games=True,  # 启用喂牌模式
            )
        elif self.current_stage == TrainingStage.BASIC:
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
                    # 0基础数据下，初期主要依赖迭代次数推进，不强制要求胜率
                    # 'win_rate': 0.05,  # 移除胜率要求（随机打牌很难达到）
                    'flower_pig_rate': 0.30,  # 花猪率低于30%（初期允许很高，只要有改善即可）
                    'ready_rate': 0.05,  # 听牌率至少5%（更容易达到，只要有进步即可）
                    # 或者使用其他更容易达到的指标
                    'games_played': 1000,  # 至少完成1000局游戏（确保有足够训练）
                },
                estimated_iterations=10000,
                min_iterations=3000,  # 至少训练3000次迭代（降低门槛）
                max_iterations=12000,  # 最多12000次迭代后强制推进（更激进）
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
                    'discard_win_rate': 0.20,  # 点炮率低于20%（初期允许较高）
                    # 'defensive_score': 0.5,  # 防御得分（如果难以计算，可以移除）
                    'win_rate': 0.10,  # 胜率至少10%（降低要求）
                    'ready_rate': 0.15,  # 听牌率至少15%
                },
                estimated_iterations=20000,
                min_iterations=8000,  # 至少训练8000次迭代
                max_iterations=25000,  # 最多25000次迭代后强制推进
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
                    'elo_score': 1100,  # Elo分数至少1100（进一步降低）
                    'average_score': 3.0,  # 平均得分至少3分（进一步降低）
                    'win_rate': 0.20,  # 胜率至少20%（降低要求）
                },
                estimated_iterations=30000,
                min_iterations=15000,  # 至少训练15000次迭代
                max_iterations=40000,  # 最多40000次迭代后强制推进
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
                    'elo_score': 1800,  # Elo分数至少1800
                    'win_rate': 0.45,  # 胜率至少45%
                },
                estimated_iterations=50000,
                min_iterations=40000,  # 至少训练40000次迭代
                max_iterations=0,  # 专家阶段不设上限
            )
    
    def should_advance_stage(
        self,
        performance_metrics: Dict[str, float],
        current_iteration: Optional[int] = None,
        min_iterations: Optional[int] = None,
        max_iterations: Optional[int] = None,
    ) -> bool:
        """
        判断是否应该进入下一阶段
        
        参数：
        - performance_metrics: 性能指标
        - current_iteration: 当前迭代次数（可选）
        - min_iterations: 最小迭代次数（可选，达到此值后才考虑推进）
        - max_iterations: 最大迭代次数（可选，达到此值后强制推进）
        
        返回：
        - 是否应该进入下一阶段
        """
        current_curriculum = self.get_current_curriculum()
        
        # 使用课程步骤中定义的最小/最大迭代次数（如果未提供参数）
        if min_iterations is None:
            min_iterations = current_curriculum.min_iterations
        if max_iterations is None:
            max_iterations = current_curriculum.max_iterations if current_curriculum.max_iterations > 0 else None
        
        # 如果提供了迭代次数，检查最小/最大迭代次数
        if current_iteration is not None:
            # 检查是否达到最小迭代次数
            if min_iterations is not None and min_iterations > 0 and current_iteration < min_iterations:
                return False
            
            # 检查是否超过最大迭代次数（强制推进）
            if max_iterations is not None and max_iterations > 0 and current_iteration >= max_iterations:
                return True  # 超过最大迭代次数，强制推进
        
        # 如果缺少所有关键指标，且没有达到最大迭代次数，不推进
        has_any_metric = any(
            criterion in performance_metrics 
            for criterion in current_curriculum.evaluation_criteria.keys()
        )
        if not has_any_metric:
            # 如果没有指标，但达到最大迭代次数，可以推进
            if current_iteration is not None and max_iterations is not None:
                return current_iteration >= max_iterations
            return False
        
        # 检查是否满足当前阶段的评估标准
        # 对于0基础数据，使用更宽松的标准
        met_criteria = 0
        total_criteria = len(current_curriculum.evaluation_criteria)
        
        # 如果没有任何评估标准，直接基于迭代次数判断
        if total_criteria == 0:
            if current_iteration is not None and max_iterations is not None and max_iterations > 0:
                return current_iteration >= max_iterations
            return False
        
        for criterion, threshold in current_curriculum.evaluation_criteria.items():
            if criterion in performance_metrics:
                value = performance_metrics[criterion]
                # 对于花猪率等"越低越好"的指标，使用 <= 判断
                if criterion.endswith('_rate') and 'pig' in criterion:
                    if value <= threshold:
                        met_criteria += 1
                    elif value <= threshold * 2.0:  # 允许100%的误差（初期非常宽松）
                        met_criteria += 0.5
                # 对于 games_played 等"越多越好"的指标
                elif criterion == 'games_played':
                    if value >= threshold:
                        met_criteria += 1
                    elif value >= threshold * 0.5:  # 达到50%即可
                        met_criteria += 0.5
                else:
                    # 对于"越高越好"的指标（如 ready_rate）
                    if value >= threshold:
                        met_criteria += 1
                    elif value >= threshold * 0.3:  # 允许达到30%即可（初期非常宽松）
                        met_criteria += 0.5
        
        # 对于初期阶段（定缺、学胡、基础），使用更宽松的标准
        if current_curriculum.stage in [TrainingStage.DECLARE_SUIT, TrainingStage.LEARN_WIN, TrainingStage.BASIC]:
            if current_iteration is not None and min_iterations is not None:
                if current_iteration >= min_iterations and met_criteria > 0:
                    return True  # 初期阶段：达到最小迭代次数且有任意进步即可
            if met_criteria >= total_criteria * 0.3:  # 满足30%标准即可
                return True
        else:
            # 其他阶段：满足50%标准
            if met_criteria >= total_criteria * 0.5:
                return True
        
        # 如果达到最大迭代次数，强制推进
        if current_iteration is not None and max_iterations is not None:
            return current_iteration >= max_iterations
        
        return False
    
    def design_next_stage(
        self,
        performance_metrics: Dict[str, float],
        current_issues: List[str],
        iteration: Optional[int] = None,
    ) -> Optional[str]:
        """
        生成课程学习规划文档（供手动提交给大模型）
        
        参数：
        - performance_metrics: 性能指标
        - current_issues: 当前阶段的问题列表
        - iteration: 当前迭代次数
        
        返回：
        - 文档文件路径（如果文档生成器可用）
        """
        if self.document_generator is None:
            print("警告: 文档生成器未设置，无法生成课程规划文档")
            return None
        
        # 生成文档
        doc_path = self.document_generator.generate_curriculum_design_document(
            current_stage=self.current_stage.value,
            performance_metrics=performance_metrics,
            issues=current_issues,
            iteration=iteration,
        )
        
        return doc_path
    
    def advance_to_next_stage(self):
        """推进到下一阶段"""
        stages = list(TrainingStage)
        current_index = stages.index(self.current_stage)
        
        if current_index < len(stages) - 1:
            self.current_stage = stages[current_index + 1]
            # 更新是否使用喂牌模式
            current_curriculum = self.get_current_curriculum()
            self.use_feeding_games = current_curriculum.use_feeding_games
            print(f"[CurriculumLearning] 进入下一阶段: {self.current_stage.value}")
            if self.use_feeding_games:
                print(f"[CurriculumLearning] 启用喂牌模式")
        else:
            print("[CurriculumLearning] 已达到最高阶段")
    
    def should_use_feeding_games(self) -> bool:
        """判断当前是否应该使用喂牌模式"""
        return self.use_feeding_games
    
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

