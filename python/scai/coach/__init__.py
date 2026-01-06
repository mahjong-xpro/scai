"""
大模型总教练 (LLM Coach)

使用大模型监督和指导AI训练，包括：
- 策略合理性审计
- 奖励函数评价
- 课程学习规划
"""

from .logger import GameLogger, DecisionLog
from .llm_interface import LLMCoach, LLMCoachConfig
from .automation import TrainingMonitor, ReportGenerator
from .curriculum import CurriculumLearning
from .gemini_code_analyzer import GeminiCodeAnalyzer

__all__ = [
    'GameLogger',
    'DecisionLog',
    'LLMCoach',
    'LLMCoachConfig',
    'TrainingMonitor',
    'ReportGenerator',
    'CurriculumLearning',
    'GeminiCodeAnalyzer',
]

