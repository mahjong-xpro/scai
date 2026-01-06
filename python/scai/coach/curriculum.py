"""
课程学习规划 (Curriculum Learning)

根据大模型的建议，设计分阶段的训练课程。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
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
    feeding_rate: float = 0.0  # 喂牌比例（0.0-1.0）
    enable_win: bool = True  # 是否允许胡牌（所有阶段都允许，通过奖励函数引导是否追求）
    reward_config: Optional[Dict[str, float]] = field(default_factory=dict)  # 奖励权重配置
    entropy_coef: float = 0.01  # Entropy系数（用于探索）
    use_search_enhanced: bool = False  # 是否使用搜索增强推理
    use_adversarial: bool = False  # 是否使用对抗训练


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
                name="阶段1：定缺与生存（弃牌逻辑初探）",
                description="解决Action Mask报错，让AI意识到手牌花色的物理分类",
                objectives=[
                    "理解定缺规则",
                    "学会选择定缺花色",
                    "避免成为花猪",
                    "掌握弃牌逻辑（优先打缺门牌）",
                ],
                evaluation_criteria={
                    'flower_pig_rate': 0.50,  # 花猪率低于50%（初期非常宽松）
                    'declare_suit_correct_rate': 0.60,  # 定缺选择正确率至少60%
                    'games_played': 500,  # 至少完成500局游戏
                },
                estimated_iterations=5000,
                min_iterations=2000,  # 至少训练2000次迭代
                max_iterations=8000,  # 最多8000次迭代后强制推进
                use_feeding_games=False,  # 100%随机发牌
                feeding_rate=0.0,  # 不喂牌
                enable_win=True,  # 允许胡牌，但不追求（通过奖励引导）
                reward_config={
                    'lack_color_discard': 5.0,  # 打出一张缺门牌
                    'illegal_action_attempt': -10.0,  # 试图在有缺门时打出其他牌
                    'shanten_reward': 0.0,  # 暂不开启向听数奖励
                    'base_win': 0.0,  # 不给胡牌奖励（让AI自然学习到不追求胡牌）
                    'ready_reward': 0.0,  # 不给听牌奖励
                },
                entropy_coef=0.05,  # 高熵，鼓励探索
            )
        elif self.current_stage == TrainingStage.LEARN_WIN:
            return CurriculumStep(
                stage=TrainingStage.LEARN_WIN,
                name="阶段2：学胡基础（向听数驱动）",
                description="解决0数据无法胡牌的困境，利用向听数作为引导信号",
                objectives=[
                    "识别基本胡牌类型（平胡、七对等）",
                    "理解听牌概念",
                    "学会主动胡牌",
                    "利用向听数改善手牌质量",
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
                feeding_rate=0.2,  # 20%比例喂牌（2:8比例）
                enable_win=True,  # 开启胡牌功能
                reward_config={
                    'shanten_decrease': 2.0,  # 向听数减少（进张）
                    'shanten_increase': -1.5,  # 拆搭子导致向听数增加
                    'ready_hand': 10.0,  # 听牌一次性重奖
                    'lack_color_discard': 2.0,  # 保留定缺奖励（降低权重）
                },
                entropy_coef=0.03,  # 中等熵，平衡探索和利用
            )
        elif self.current_stage == TrainingStage.BASIC:
            return CurriculumStep(
                stage=TrainingStage.BASIC,
                name="阶段3：价值收割（番型感知）",
                description="AI开始胡牌，并学会识别高收益牌型",
                objectives=[
                    "学会识别高收益牌型",
                    "理解番数计算",
                    "学会识别根（Gen）",
                    "理解查大叫和查花猪的罚分",
                ],
                evaluation_criteria={
                    'win_rate': 0.15,  # 胜率至少15%
                    'average_fan': 2.0,  # 平均番数至少2番
                    'gen_count': 0.3,  # 平均每局至少0.3个根
                    'games_played': 1500,  # 至少完成1500局游戏
                },
                estimated_iterations=15000,
                min_iterations=8000,  # 至少训练8000次迭代
                max_iterations=20000,  # 最多20000次迭代后强制推进
                use_feeding_games=True,  # 保留少量喂牌
                feeding_rate=0.1,  # 降低到10%（快速降低喂牌比例）
                enable_win=True,  # 开启胡牌功能
                reward_config={
                    'base_win': 20.0,  # 基础胡牌奖励
                    'fan_multiplier': 1.5,  # 番数倍数（根据最终结算金额）
                    'gen_reward': 5.0,  # 每多一个根，额外给奖
                    'shouting_penalty': -30.0,  # 查大叫罚分（1.5倍胡牌奖励）
                    'flower_pig_penalty': -30.0,  # 查花猪罚分（1.5倍胡牌奖励）
                    'shanten_reward': 0.5,  # 向听数奖励衰减
                },
                entropy_coef=0.02,  # 降低熵，开始收敛
            )
        elif self.current_stage == TrainingStage.DEFENSIVE:
            return CurriculumStep(
                stage=TrainingStage.DEFENSIVE,
                name="阶段4：防御初阶（避炮与危险感知）",
                description="顶级水平的分水岭——学会不再送死",
                objectives=[
                    "识别危险牌",
                    "避免在关键时刻点炮",
                    "学会安全弃牌（打熟张）",
                    "理解残局压力",
                ],
                evaluation_criteria={
                    'discard_win_rate': 0.15,  # 点炮率低于15%
                    'win_rate': 0.20,  # 胜率至少20%
                    'ready_rate': 0.25,  # 听牌率至少25%
                    'safe_discard_rate': 0.60,  # 安全弃牌率至少60%
                },
                estimated_iterations=25000,
                min_iterations=12000,  # 至少训练12000次迭代
                max_iterations=35000,  # 最多35000次迭代后强制推进
                use_feeding_games=False,  # 不使用喂牌
                feeding_rate=0.0,  # 完全随机牌局
                enable_win=True,  # 开启胡牌功能
                reward_config={
                    'point_loss': -30.0,  # 点炮重罚
                    'safe_discard_bonus': 0.5,  # 在对手听牌时，打出场上已现的熟张
                    'shanten_reward': 0.5,  # 向听数奖励衰减（防止AI为了快胡而无视风险）
                    'base_win': 15.0,  # 降低基础胡牌奖励
                    'fan_multiplier': 1.2,  # 降低番数倍数
                },
                entropy_coef=0.01,  # 低熵，专注策略优化
                use_adversarial=False,  # 使用对手池中的阶段3镜像
            )
        elif self.current_stage == TrainingStage.ADVANCED:
            return CurriculumStep(
                stage=TrainingStage.ADVANCED,
                name="阶段5：高级博弈（过胡与杠的博弈）",
                description="学会钓鱼和风险对冲",
                objectives=[
                    "学会过胡策略（钓鱼）",
                    "理解杠牌的风险和收益",
                    "学会呼叫转移的规避",
                    "优化期望收益计算",
                ],
                evaluation_criteria={
                    'elo_score': 1400,  # Elo分数至少1400
                    'average_score': 5.0,  # 平均得分至少5分
                    'win_rate': 0.30,  # 胜率至少30%
                    'pass_hu_success_rate': 0.20,  # 过胡成功率至少20%
                },
                estimated_iterations=40000,
                min_iterations=25000,  # 至少训练25000次迭代
                max_iterations=60000,  # 最多60000次迭代后强制推进
                use_feeding_games=False,  # 不使用喂牌
                feeding_rate=0.0,  # 完全随机牌局
                enable_win=True,  # 开启胡牌功能
                reward_config={
                    'pass_hu_success': 15.0,  # 过胡后胡了更大的番数
                    'call_transfer_loss': -40.0,  # 杠上炮导致的呼叫转移，极重罚
                    'base_win': 10.0,  # 进一步降低基础奖励
                    'fan_multiplier': 1.0,  # 番数倍数回归正常
                    'shanten_reward': 0.0,  # 完全关闭向听数奖励
                },
                entropy_coef=0.005,  # 极低熵，精细策略
                use_search_enhanced=True,  # 开启ISMCTS搜索增强
                use_adversarial=False,  # 使用对手池
            )
        else:  # EXPERT
            return CurriculumStep(
                stage=TrainingStage.EXPERT,
                name="阶段6：专家进化（期望收益最大化）",
                description="抹除所有人工痕迹，回归血战到底的本源——金币收益",
                objectives=[
                    "纯金币收益驱动",
                    "掌握所有高级策略",
                    "优化策略组合",
                    "达到专家水平",
                ],
                evaluation_criteria={
                    'elo_score': 1800,  # Elo分数至少1800
                    'win_rate': 0.45,  # 胜率至少45%
                    'average_score': 8.0,  # 平均得分至少8分
                },
                estimated_iterations=100000,
                min_iterations=60000,  # 至少训练60000次迭代
                max_iterations=0,  # 专家阶段不设上限
                use_feeding_games=False,  # 不使用喂牌
                feeding_rate=0.0,  # 完全随机牌局
                enable_win=True,  # 开启胡牌功能
                reward_config={
                    # 纯金币收益，取消所有人工Reward
                    'raw_score_only': True,  # 仅使用原始得分
                    'base_win': 0.0,  # 取消基础胡牌奖励
                    'fan_multiplier': 0.0,  # 取消番数倍数
                    'gen_reward': 0.0,  # 取消根奖励
                    'shanten_reward': 0.0,  # 取消向听数奖励
                    'ready_reward': 0.0,  # 取消听牌奖励
                    # 只保留惩罚（避免极端行为）
                    'point_loss': -1.0,  # 点炮惩罚（仅作为约束）
                    'call_transfer_loss': -1.0,  # 呼叫转移惩罚（仅作为约束）
                },
                entropy_coef=0.001,  # 极低熵，完全收敛
                use_search_enhanced=True,  # 开启ISMCTS搜索增强
                use_adversarial=True,  # 开启对抗训练（面对极端风格对手）
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
    
    def get_current_reward_config(self) -> Dict[str, float]:
        """获取当前阶段的奖励配置"""
        current_curriculum = self.get_current_curriculum()
        return current_curriculum.reward_config
    
    def get_current_entropy_coef(self) -> float:
        """获取当前阶段的熵系数"""
        current_curriculum = self.get_current_curriculum()
        return current_curriculum.entropy_coef
    
    def should_use_search_enhanced(self) -> bool:
        """判断当前阶段是否应该使用搜索增强推理"""
        current_curriculum = self.get_current_curriculum()
        return current_curriculum.use_search_enhanced
    
    def should_use_adversarial(self) -> bool:
        """判断当前阶段是否应该使用对抗训练"""
        current_curriculum = self.get_current_curriculum()
        return current_curriculum.use_adversarial
    
    def get_current_enable_win(self) -> bool:
        """获取当前阶段是否开启胡牌功能"""
        current_curriculum = self.get_current_curriculum()
        return current_curriculum.enable_win
    
    def get_current_feeding_rate(self) -> float:
        """获取当前阶段的喂牌比例"""
        current_curriculum = self.get_current_curriculum()
        return current_curriculum.feeding_rate if current_curriculum.use_feeding_games else 0.0

