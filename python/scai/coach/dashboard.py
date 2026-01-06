"""
课程学习中心 Web 可视化仪表板

提供实时训练进度监控和课程学习状态可视化。
"""

import json
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import queue


@dataclass
class TrainingStatus:
    """训练状态"""
    current_iteration: int = 0
    total_iterations: int = 0
    current_stage: str = ""
    stage_progress: float = 0.0  # 0.0-1.0
    metrics: Dict[str, float] = None
    reward_config: Dict[str, float] = None
    curriculum_info: Dict[str, Any] = None
    training_stats: Dict[str, Any] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if self.reward_config is None:
            self.reward_config = {}
        if self.curriculum_info is None:
            self.curriculum_info = {}
        if self.training_stats is None:
            self.training_stats = {}
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DashboardStateManager:
    """仪表板状态管理器
    
    线程安全的状态管理器，用于存储和更新训练状态。
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._status = TrainingStatus()
        self._update_queue = queue.Queue()
        self._subscribers: List[queue.Queue] = []
    
    def update_status(
        self,
        current_iteration: Optional[int] = None,
        total_iterations: Optional[int] = None,
        current_stage: Optional[str] = None,
        stage_progress: Optional[float] = None,
        metrics: Optional[Dict[str, float]] = None,
        reward_config: Optional[Dict[str, float]] = None,
        curriculum_info: Optional[Dict[str, Any]] = None,
        training_stats: Optional[Dict[str, Any]] = None,
    ):
        """更新训练状态"""
        with self._lock:
            if current_iteration is not None:
                self._status.current_iteration = current_iteration
            if total_iterations is not None:
                self._status.total_iterations = total_iterations
            if current_stage is not None:
                self._status.current_stage = current_stage
            if stage_progress is not None:
                self._status.stage_progress = stage_progress
            if metrics is not None:
                self._status.metrics.update(metrics)
            if reward_config is not None:
                self._status.reward_config = reward_config
            if curriculum_info is not None:
                self._status.curriculum_info = curriculum_info
            if training_stats is not None:
                self._status.training_stats.update(training_stats)
            
            self._status.timestamp = datetime.now().isoformat()
            
            # 通知所有订阅者
            status_dict = asdict(self._status)
            for subscriber in self._subscribers:
                try:
                    subscriber.put_nowait(status_dict)
                except queue.Full:
                    pass  # 跳过满队列
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        with self._lock:
            return asdict(self._status)
    
    def subscribe(self) -> queue.Queue:
        """订阅状态更新"""
        subscriber_queue = queue.Queue(maxsize=10)
        with self._lock:
            self._subscribers.append(subscriber_queue)
        return subscriber_queue
    
    def unsubscribe(self, subscriber_queue: queue.Queue):
        """取消订阅"""
        with self._lock:
            if subscriber_queue in self._subscribers:
                self._subscribers.remove(subscriber_queue)


# 全局状态管理器实例
_state_manager = DashboardStateManager()


def get_state_manager() -> DashboardStateManager:
    """获取全局状态管理器"""
    return _state_manager


def update_training_status(
    curriculum=None,
    current_iteration: int = 0,
    total_iterations: int = 0,
    metrics: Optional[Dict[str, float]] = None,
    training_stats: Optional[Dict[str, Any]] = None,
):
    """更新训练状态（从训练循环调用）"""
    state_manager = get_state_manager()
    
    # 计算阶段进度
    current_stage = ""
    stage_progress = 0.0
    reward_config = {}
    curriculum_info = {}
    
    if curriculum is not None:
        current_curriculum = curriculum.get_current_curriculum()
        current_stage = current_curriculum.name
        
        # 计算阶段进度
        if current_curriculum.max_iterations > 0:
            # 基于迭代次数计算进度
            min_iter = current_curriculum.min_iterations
            max_iter = current_curriculum.max_iterations
            if max_iter > min_iter:
                progress = (current_iteration - min_iter) / (max_iter - min_iter)
                stage_progress = max(0.0, min(1.0, progress))
        else:
            # 基于评估标准计算进度
            if metrics:
                met_criteria = 0
                total_criteria = len(current_curriculum.evaluation_criteria)
                if total_criteria > 0:
                    for criterion, threshold in current_curriculum.evaluation_criteria.items():
                        if criterion in metrics:
                            value = metrics[criterion]
                            if criterion.endswith('_rate') and 'pig' in criterion:
                                if value <= threshold:
                                    met_criteria += 1
                            elif criterion == 'games_played':
                                if value >= threshold:
                                    met_criteria += 1
                            else:
                                if value >= threshold:
                                    met_criteria += 1
                    stage_progress = met_criteria / total_criteria
        
        reward_config = curriculum.get_current_reward_config()
        curriculum_info = {
            'stage': current_curriculum.stage.value,
            'name': current_curriculum.name,
            'description': current_curriculum.description,
            'objectives': current_curriculum.objectives,
            'evaluation_criteria': current_curriculum.evaluation_criteria,
            'estimated_iterations': current_curriculum.estimated_iterations,
            'min_iterations': current_curriculum.min_iterations,
            'max_iterations': current_curriculum.max_iterations,
            'use_feeding_games': current_curriculum.use_feeding_games,
            'feeding_rate': current_curriculum.feeding_rate,
            'entropy_coef': current_curriculum.entropy_coef,
            'use_search_enhanced': current_curriculum.use_search_enhanced,
            'use_adversarial': current_curriculum.use_adversarial,
        }
    
    state_manager.update_status(
        current_iteration=current_iteration,
        total_iterations=total_iterations,
        current_stage=current_stage,
        stage_progress=stage_progress,
        metrics=metrics or {},
        reward_config=reward_config,
        curriculum_info=curriculum_info,
        training_stats=training_stats or {},
    )

