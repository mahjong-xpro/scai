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
    支持历史记录存储，方便查看趋势。
    支持游戏轨迹存储，用于牌局回放。
    """
    
    def __init__(self, max_history: int = 1000, max_games: int = 50):
        self._lock = threading.Lock()
        self._status = TrainingStatus()
        self._update_queue = queue.Queue()
        self._subscribers: List[queue.Queue] = []
        # 历史记录：存储每次更新的状态快照
        self._history: List[Dict[str, Any]] = []
        self._max_history = max_history  # 最多保存1000条历史记录
        # 游戏轨迹：存储最近完成的游戏，用于回放
        self._game_replays: List[Dict[str, Any]] = []
        self._max_games = max_games  # 最多保存50局游戏
    
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
            
            # 保存历史记录
            status_dict = asdict(self._status)
            self._history.append(status_dict.copy())
            
            # 限制历史记录数量
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            
            # 通知所有订阅者
            for subscriber in self._subscribers:
                try:
                    subscriber.put_nowait(status_dict)
                except queue.Full:
                    # 队列满时，移除最旧的数据，添加新数据
                    try:
                        subscriber.get_nowait()  # 移除最旧的数据
                        subscriber.put_nowait(status_dict)
                    except queue.Empty:
                        # 如果队列为空但仍报 Full，可能是并发问题，跳过
                        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        with self._lock:
            return asdict(self._status)
    
    def subscribe(self) -> queue.Queue:
        """订阅状态更新"""
        subscriber_queue = queue.Queue(maxsize=100)  # 增加容量以减少数据丢失
        with self._lock:
            self._subscribers.append(subscriber_queue)
        return subscriber_queue
    
    def unsubscribe(self, subscriber_queue: queue.Queue):
        """取消订阅"""
        with self._lock:
            if subscriber_queue in self._subscribers:
                self._subscribers.remove(subscriber_queue)
    
    def get_history(
        self,
        limit: Optional[int] = None,
        start_iteration: Optional[int] = None,
        end_iteration: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """获取历史记录
        
        参数：
        - limit: 最多返回的记录数（默认返回全部）
        - start_iteration: 起始迭代次数（可选）
        - end_iteration: 结束迭代次数（可选）
        
        返回：
        - 历史记录列表，按时间顺序排列
        """
        with self._lock:
            history = self._history.copy()
        
        # 按迭代次数过滤
        if start_iteration is not None:
            history = [h for h in history if h.get('current_iteration', 0) >= start_iteration]
        if end_iteration is not None:
            history = [h for h in history if h.get('current_iteration', 0) <= end_iteration]
        
        # 限制数量
        if limit is not None:
            history = history[-limit:]
        
        return history
    
    def get_history_summary(self) -> Dict[str, Any]:
        """获取历史记录摘要
        
        返回：
        - 包含历史记录统计信息的字典
        """
        with self._lock:
            history = self._history.copy()
        
        if not history:
            return {
                'total_records': 0,
                'first_iteration': 0,
                'last_iteration': 0,
                'time_span': None,
            }
        
        first = history[0]
        last = history[-1]
        
        try:
            first_time = datetime.fromisoformat(first.get('timestamp', ''))
            last_time = datetime.fromisoformat(last.get('timestamp', ''))
            time_span = (last_time - first_time).total_seconds()
        except:
            time_span = None
        
        return {
            'total_records': len(history),
            'first_iteration': first.get('current_iteration', 0),
            'last_iteration': last.get('current_iteration', 0),
            'time_span_seconds': time_span,
        }
    
    def add_game_replay(self, game_data: Dict[str, Any]):
        """添加游戏轨迹用于回放
        
        参数：
        - game_data: 游戏数据字典，包含：
            - game_id: 游戏ID
            - iteration: 训练迭代次数
            - trajectory: 游戏轨迹（states, actions, rewards等）
            - game_info: 游戏信息（定缺、胡牌类型、最终得分等）
            - timestamp: 时间戳
        """
        with self._lock:
            # 添加时间戳（如果没有）
            if 'timestamp' not in game_data:
                game_data['timestamp'] = datetime.now().isoformat()
            
            self._game_replays.append(game_data.copy())
            
            # 限制游戏数量
            if len(self._game_replays) > self._max_games:
                self._game_replays = self._game_replays[-self._max_games:]
    
    def get_game_replays(
        self,
        limit: Optional[int] = None,
        iteration: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """获取游戏轨迹列表
        
        参数：
        - limit: 最多返回的游戏数（默认返回全部）
        - iteration: 筛选特定迭代次数的游戏（可选）
        
        返回：
        - 游戏轨迹列表，按时间倒序排列（最新的在前）
        """
        with self._lock:
            replays = self._game_replays.copy()
        
        # 按迭代次数过滤
        if iteration is not None:
            replays = [r for r in replays if r.get('iteration') == iteration]
        
        # 限制数量
        if limit is not None:
            replays = replays[-limit:]
        
        # 倒序排列（最新的在前）
        replays.reverse()
        
        return replays
    
    def get_game_replay(self, game_id: int) -> Optional[Dict[str, Any]]:
        """获取单个游戏轨迹
        
        参数：
        - game_id: 游戏ID
        
        返回：
        - 游戏轨迹字典，如果不存在则返回None
        """
        with self._lock:
            for replay in self._game_replays:
                if replay.get('game_id') == game_id:
                    return replay.copy()
        return None


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
                # 添加边界检查，确保 current_iteration >= min_iter
                if current_iteration < min_iter:
                    stage_progress = 0.0
                else:
                    progress = (current_iteration - min_iter) / (max_iter - min_iter)
                    stage_progress = max(0.0, min(1.0, progress))
            else:
                stage_progress = 0.0
        else:
            # 基于评估标准计算进度
            if metrics:
                met_criteria = 0
                total_criteria = len(current_curriculum.evaluation_criteria)
                if total_criteria > 0:
                    for criterion, threshold in current_curriculum.evaluation_criteria.items():
                        # 使用 .get() 方法提供默认值，避免 KeyError
                        value = metrics.get(criterion, None)
                        if value is None:
                            continue
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

