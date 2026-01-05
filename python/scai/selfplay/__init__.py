"""
自对弈模块

包含：
- Worker：Ray worker，用于分布式自对弈
- Collector：数据收集器
- Oracle：Oracle 引导实现
"""

from .worker import SelfPlayWorker
from .collector import DataCollector

__all__ = [
    "SelfPlayWorker",
    "DataCollector",
]

