"""
评估器 (Evaluator)

实现 Elo 评分机制、模型评估和历史版本对弈。
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple
import os
from collections import defaultdict

from ..models import DualResNet
from ..utils.checkpoint import CheckpointManager


class EloRating:
    """Elo 评分系统
    
    用于评估模型强度，支持模型之间的对弈评分。
    """
    
    def __init__(self, initial_rating: float = 1500.0, k_factor: float = 32.0):
        """
        参数：
        - initial_rating: 初始评分（默认 1500.0）
        - k_factor: K 因子（默认 32.0）
        """
        self.initial_rating = initial_rating
        self.k_factor = k_factor
        self.ratings = defaultdict(lambda: initial_rating)
    
    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        计算期望得分
        
        参数：
        - rating_a: 玩家 A 的评分
        - rating_b: 玩家 B 的评分
        
        返回：
        - 玩家 A 的期望得分（0-1）
        """
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
    
    def update_rating(
        self,
        player_id: str,
        opponent_id: str,
        actual_score: float,
    ):
        """
        更新评分
        
        参数：
        - player_id: 玩家 ID
        - opponent_id: 对手 ID
        - actual_score: 实际得分（0-1，1 表示胜利）
        """
        rating_a = self.ratings[player_id]
        rating_b = self.ratings[opponent_id]
        
        expected = self.expected_score(rating_a, rating_b)
        new_rating = rating_a + self.k_factor * (actual_score - expected)
        
        self.ratings[player_id] = new_rating
    
    def get_rating(self, player_id: str) -> float:
        """获取评分"""
        return self.ratings[player_id]
    
    def get_ratings(self) -> Dict[str, float]:
        """获取所有评分"""
        return dict(self.ratings)


class Evaluator:
    """评估器
    
    实现模型评估、Elo 评分和历史版本对弈。
    """
    
    def __init__(
        self,
        checkpoint_dir: str = './checkpoints',
        elo_threshold: float = 0.55,
        device: str = 'cpu',
    ):
        """
        参数：
        - checkpoint_dir: Checkpoint 目录
        - elo_threshold: Elo 胜率阈值（默认 0.55，即 55%）
        - device: 设备（'cpu' 或 'cuda'）
        """
        self.checkpoint_dir = checkpoint_dir
        self.elo_threshold = elo_threshold
        self.device = device
        
        # Elo 评分系统
        self.elo = EloRating()
        
        # Checkpoint 管理器
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        
        # 评估历史
        self.evaluation_history = []
    
    def evaluate_model(
        self,
        model: DualResNet,
        model_id: str,
        num_games: int = 100,
    ) -> Dict[str, float]:
        """
        评估模型
        
        参数：
        - model: 要评估的模型
        - model_id: 模型 ID
        - num_games: 评估游戏数量（默认 100）
        
        返回：
        - 包含评估指标的字典
        """
        model.eval()
        
        # 这里应该实现实际的游戏对弈逻辑
        # 目前返回占位符数据
        wins = 0
        total_score = 0.0
        
        for _ in range(num_games):
            # TODO: 实现实际的对弈逻辑
            # 目前使用随机数据作为占位符
            is_win = np.random.random() > 0.5
            score = np.random.normal(0, 10)
            
            if is_win:
                wins += 1
            total_score += score
        
        win_rate = wins / num_games
        avg_score = total_score / num_games
        
        return {
            'win_rate': win_rate,
            'avg_score': avg_score,
            'wins': wins,
            'total_games': num_games,
        }
    
    def compare_models(
        self,
        model_a: DualResNet,
        model_b: DualResNet,
        model_a_id: str,
        model_b_id: str,
        num_games: int = 100,
    ) -> Dict[str, float]:
        """
        比较两个模型
        
        参数：
        - model_a: 模型 A
        - model_b: 模型 B
        - model_a_id: 模型 A 的 ID
        - model_b_id: 模型 B 的 ID
        - num_games: 对弈游戏数量（默认 100）
        
        返回：
        - 包含比较结果的字典
        """
        model_a.eval()
        model_b.eval()
        
        # 这里应该实现实际的对弈逻辑
        # 目前返回占位符数据
        wins_a = 0
        total_score_a = 0.0
        total_score_b = 0.0
        
        for _ in range(num_games):
            # TODO: 实现实际的对弈逻辑
            # 目前使用随机数据作为占位符
            is_win_a = np.random.random() > 0.5
            score_a = np.random.normal(0, 10)
            score_b = -score_a  # 零和游戏
            
            if is_win_a:
                wins_a += 1
            total_score_a += score_a
            total_score_b += score_b
        
        win_rate_a = wins_a / num_games
        
        # 更新 Elo 评分
        actual_score = 1.0 if win_rate_a >= 0.5 else 0.0
        self.elo.update_rating(model_a_id, model_b_id, actual_score)
        self.elo.update_rating(model_b_id, model_a_id, 1.0 - actual_score)
        
        return {
            'model_a_win_rate': win_rate_a,
            'model_b_win_rate': 1.0 - win_rate_a,
            'model_a_avg_score': total_score_a / num_games,
            'model_b_avg_score': total_score_b / num_games,
            'model_a_elo': self.elo.get_rating(model_a_id),
            'model_b_elo': self.elo.get_rating(model_b_id),
        }
    
    def should_keep_model(self, win_rate: float) -> bool:
        """
        判断是否应该保留模型
        
        参数：
        - win_rate: 胜率
        
        返回：
        - 是否应该保留模型
        """
        return win_rate >= self.elo_threshold
    
    def get_best_model_id(self) -> Optional[str]:
        """
        获取最佳模型 ID
        
        返回：
        - 最佳模型的 ID，如果没有则返回 None
        """
        if len(self.elo.ratings) == 0:
            return None
        
        best_id = max(self.elo.ratings.items(), key=lambda x: x[1])[0]
        return best_id
    
    def get_model_elo(self, model_id: str) -> float:
        """获取模型的 Elo 评分"""
        return self.elo.get_rating(model_id)

