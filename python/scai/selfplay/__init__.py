"""
自对弈模块

包含：
- Worker：Ray worker，用于分布式自对弈
- Collector：数据收集器
- OpponentPool：对手池系统（关键组件）
- Oracle：Oracle 引导实现
"""

from .worker import SelfPlayWorker
from .collector import DataCollector
from .opponent_pool import OpponentPool, OpponentModel
from .feeding_games import FeedingGameGenerator, FeedingGameConfig

__all__ = [
    "SelfPlayWorker",
    "DataCollector",
    "OpponentPool",
    "OpponentModel",
    "FeedingGameGenerator",
    "FeedingGameConfig",
]

