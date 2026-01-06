"""
对手池系统 (Opponent Pool)

管理历史模型，实现多样化的对手策略，防止过拟合，提升训练稳定性。
这是达到人类顶级水平的关键组件（AlphaZero/Suphx 核心特性）。
"""

import torch
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import random
import numpy as np

from ..models import DualResNet
from ..utils.checkpoint import CheckpointManager


@dataclass
class OpponentModel:
    """对手模型信息"""
    model_id: str
    iteration: int
    elo_rating: float
    checkpoint_path: str
    model_state_dict: Optional[Dict] = None
    metadata: Optional[Dict] = None


class OpponentPool:
    """对手池管理器
    
    管理历史模型，支持多种采样策略，实现多样化的对手。
    """
    
    def __init__(
        self,
        checkpoint_dir: str = './checkpoints',
        pool_size: int = 10,
        selection_strategy: str = 'uniform',
        min_elo_diff: float = 100.0,
    ):
        """
        参数：
        - checkpoint_dir: Checkpoint 目录
        - pool_size: 池大小（保留的模型数量，默认 10）
        - selection_strategy: 选择策略
          - 'uniform': 均匀随机选择
          - 'weighted_by_elo': 按 Elo 评分加权
          - 'recent': 优先选择最近的模型
          - 'diverse': 选择 Elo 差异较大的模型
        - min_elo_diff: 最小 Elo 差异（用于多样性选择，默认 100.0）
        """
        self.checkpoint_dir = checkpoint_dir
        self.pool_size = pool_size
        self.selection_strategy = selection_strategy
        self.min_elo_diff = min_elo_diff
        
        # 对手模型池（按迭代顺序）
        self.opponents: deque[OpponentModel] = deque(maxlen=pool_size)
        
        # Checkpoint 管理器
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        
        # 统计信息
        self.stats = {
            'total_models_added': 0,
            'total_models_removed': 0,
            'total_selections': 0,
        }
    
    def add_model(
        self,
        model: DualResNet,
        iteration: int,
        elo_rating: float = 1500.0,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        添加模型到对手池
        
        参数：
        - model: 模型实例
        - iteration: 迭代次数
        - elo_rating: Elo 评分（默认 1500.0）
        - metadata: 元数据（可选）
        
        返回：
        - 模型 ID
        """
        model_id = f"iteration_{iteration}"
        
        # 创建对手模型
        opponent = OpponentModel(
            model_id=model_id,
            iteration=iteration,
            elo_rating=elo_rating,
            checkpoint_path=f"{self.checkpoint_dir}/checkpoint_iter_{iteration}.pt",
            model_state_dict=model.state_dict(),
            metadata=metadata or {},
        )
        
        # 添加到池中
        self.opponents.append(opponent)
        self.stats['total_models_added'] += 1
        
        # 如果超过池大小，移除最旧的
        if len(self.opponents) > self.pool_size:
            removed = self.opponents.popleft()
            self.stats['total_models_removed'] += 1
        
        return model_id
    
    def load_from_checkpoints(
        self,
        max_models: Optional[int] = None,
        min_elo: Optional[float] = None,
    ):
        """
        从 Checkpoint 目录加载历史模型
        
        参数：
        - max_models: 最大加载数量（默认 None，加载所有）
        - min_elo: 最小 Elo 评分（默认 None，不筛选）
        """
        checkpoints = self.checkpoint_manager.list_checkpoints()
        
        # 按迭代次数排序
        checkpoints.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
        
        # 限制数量
        if max_models:
            checkpoints = checkpoints[-max_models:]
        
        for checkpoint_path in checkpoints:
            try:
                checkpoint = torch.load(checkpoint_path, map_location='cpu')
                iteration = checkpoint.get('iteration', 0)
                metadata = checkpoint.get('metadata', {})
                elo_rating = metadata.get('elo_rating', 1500.0)
                
                # Elo 筛选
                if min_elo and elo_rating < min_elo:
                    continue
                
                model_id = f"iteration_{iteration}"
                opponent = OpponentModel(
                    model_id=model_id,
                    iteration=iteration,
                    elo_rating=elo_rating,
                    checkpoint_path=checkpoint_path,
                    metadata=metadata,
                )
                
                self.opponents.append(opponent)
            except Exception as e:
                print(f"Warning: Failed to load checkpoint {checkpoint_path}: {e}")
                continue
        
        # 限制池大小
        while len(self.opponents) > self.pool_size:
            self.opponents.popleft()
    
    def sample_opponents(
        self,
        num_opponents: int = 3,
        exclude_model_id: Optional[str] = None,
    ) -> List[OpponentModel]:
        """
        采样对手模型
        
        参数：
        - num_opponents: 需要的对手数量（默认 3）
        - exclude_model_id: 排除的模型 ID（通常是当前模型）
        
        返回：
        - 对手模型列表
        """
        if len(self.opponents) == 0:
            return []
        
        # 过滤排除的模型
        available = [
            opp for opp in self.opponents
            if opp.model_id != exclude_model_id
        ]
        
        if len(available) == 0:
            available = list(self.opponents)
        
        if len(available) == 0:
            return []
        
        # 根据策略选择
        if self.selection_strategy == 'uniform':
            selected = self._uniform_sample(available, num_opponents)
        elif self.selection_strategy == 'weighted_by_elo':
            selected = self._weighted_sample(available, num_opponents)
        elif self.selection_strategy == 'recent':
            selected = self._recent_sample(available, num_opponents)
        elif self.selection_strategy == 'diverse':
            selected = self._diverse_sample(available, num_opponents)
        else:
            selected = self._uniform_sample(available, num_opponents)
        
        self.stats['total_selections'] += 1
        
        return selected
    
    def _uniform_sample(
        self,
        available: List[OpponentModel],
        num_opponents: int,
    ) -> List[OpponentModel]:
        """均匀随机采样"""
        if len(available) <= num_opponents:
            return available.copy()
        return random.sample(available, num_opponents)
    
    def _weighted_sample(
        self,
        available: List[OpponentModel],
        num_opponents: int,
    ) -> List[OpponentModel]:
        """按 Elo 评分加权采样（Elo 越高，被选中概率越大）"""
        if len(available) <= num_opponents:
            return available.copy()
        
        # 计算权重（Elo 越高，权重越大）
        weights = [opp.elo_rating for opp in available]
        min_weight = min(weights)
        weights = [w - min_weight + 1.0 for w in weights]  # 确保权重为正
        
        # 加权采样
        selected = []
        available_copy = available.copy()
        weights_copy = weights.copy()
        
        for _ in range(min(num_opponents, len(available_copy))):
            total_weight = sum(weights_copy)
            r = random.uniform(0, total_weight)
            cumsum = 0
            
            for i, weight in enumerate(weights_copy):
                cumsum += weight
                if r <= cumsum:
                    selected.append(available_copy[i])
                    available_copy.pop(i)
                    weights_copy.pop(i)
                    break
        
        return selected
    
    def _recent_sample(
        self,
        available: List[OpponentModel],
        num_opponents: int,
    ) -> List[OpponentModel]:
        """优先选择最近的模型"""
        if len(available) <= num_opponents:
            return available.copy()
        
        # 按迭代次数排序，选择最近的
        sorted_opponents = sorted(available, key=lambda x: x.iteration, reverse=True)
        return sorted_opponents[:num_opponents]
    
    def _diverse_sample(
        self,
        available: List[OpponentModel],
        num_opponents: int,
    ) -> List[OpponentModel]:
        """选择 Elo 差异较大的模型（多样性）"""
        if len(available) <= num_opponents:
            return available.copy()
        
        # 按 Elo 排序
        sorted_opponents = sorted(available, key=lambda x: x.elo_rating)
        
        # 选择 Elo 差异较大的模型
        selected = []
        selected.append(sorted_opponents[0])  # 最低 Elo
        selected.append(sorted_opponents[-1])  # 最高 Elo
        
        # 如果还需要更多，选择中间差异大的
        if num_opponents > 2:
            remaining = [opp for opp in sorted_opponents[1:-1]]
            if remaining:
                # 选择 Elo 差异最大的
                for _ in range(min(num_opponents - 2, len(remaining))):
                    best_opp = None
                    max_diff = 0
                    
                    for opp in remaining:
                        min_diff = min(
                            abs(opp.elo_rating - sel.elo_rating)
                            for sel in selected
                        )
                        if min_diff > max_diff:
                            max_diff = min_diff
                            best_opp = opp
                    
                    if best_opp:
                        selected.append(best_opp)
                        remaining.remove(best_opp)
        
        return selected[:num_opponents]
    
    def get_model_state_dict(
        self,
        opponent: OpponentModel,
    ) -> Dict:
        """
        获取对手模型的状态字典
        
        参数：
        - opponent: 对手模型
        
        返回：
        - 模型状态字典
        
        抛出：
        - RuntimeError: 如果加载失败
        """
        if opponent.model_state_dict is not None:
            return opponent.model_state_dict
        
        # 从 Checkpoint 加载
        import os
        if not os.path.exists(opponent.checkpoint_path):
            raise RuntimeError(
                f"Checkpoint file not found for opponent {opponent.model_id}: {opponent.checkpoint_path}"
            )
        
        try:
            checkpoint = torch.load(opponent.checkpoint_path, map_location='cpu')
            if 'model_state_dict' not in checkpoint:
                raise RuntimeError(
                    f"Checkpoint file missing 'model_state_dict' for opponent {opponent.model_id}"
                )
            return checkpoint['model_state_dict']
        except Exception as e:
            # 如果加载失败，尝试从池中移除该对手
            if opponent in self.opponents:
                self.opponents.remove(opponent)
                self.stats['total_models_removed'] += 1
            raise RuntimeError(f"Failed to load opponent model {opponent.model_id}: {e}") from e
    
    def get_best_opponent(self) -> Optional[OpponentModel]:
        """获取 Elo 评分最高的对手"""
        if len(self.opponents) == 0:
            return None
        
        return max(self.opponents, key=lambda x: x.elo_rating)
    
    def get_recent_opponent(self) -> Optional[OpponentModel]:
        """获取最近的对手"""
        if len(self.opponents) == 0:
            return None
        
        return max(self.opponents, key=lambda x: x.iteration)
    
    def update_elo_ratings(
        self,
        elo_ratings: Dict[str, float],
    ):
        """
        更新对手的 Elo 评分
        
        参数：
        - elo_ratings: 模型 ID 到 Elo 评分的映射
        """
        for opponent in self.opponents:
            if opponent.model_id in elo_ratings:
                opponent.elo_rating = elo_ratings[opponent.model_id]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'pool_size': len(self.opponents),
            'max_pool_size': self.pool_size,
            'avg_elo': (
                sum(opp.elo_rating for opp in self.opponents) / len(self.opponents)
                if len(self.opponents) > 0
                else 0.0
            ),
            'min_elo': (
                min(opp.elo_rating for opp in self.opponents)
                if len(self.opponents) > 0
                else 0.0
            ),
            'max_elo': (
                max(opp.elo_rating for opp in self.opponents)
                if len(self.opponents) > 0
                else 0.0
            ),
        }
    
    def clear(self):
        """清空对手池"""
        self.opponents.clear()
        self.stats = {
            'total_models_added': 0,
            'total_models_removed': 0,
            'total_selections': 0,
        }

