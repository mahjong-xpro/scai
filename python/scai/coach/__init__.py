"""
Coach 模块

生成训练分析文档，供手动提交给大模型进行分析。
包括：
- 策略分析文档生成
- 奖励函数评价文档生成
- 课程学习规划文档生成
"""

from .logger import GameLogger, DecisionLog
from .document_generator import TrainingDocumentGenerator
from .curriculum import CurriculumLearning, TrainingStage, CurriculumStep

__all__ = [
    'GameLogger',
    'DecisionLog',
    'TrainingDocumentGenerator',
    'CurriculumLearning',
    'TrainingStage',
    'CurriculumStep',
]

