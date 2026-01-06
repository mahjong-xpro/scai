"""
超参数自动化搜索 (Hyperparameter Search)

实现学习率、探索因子、搜索深度等超参数的自动化调优。
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import itertools
from dataclasses import dataclass

from ..models import DualResNet
from .ppo import PPO
from .evaluator import Evaluator


@dataclass
class HyperparameterConfig:
    """超参数配置"""
    learning_rate: float
    entropy_coef: float
    search_depth: int  # ISMCTS 搜索深度（num_simulations）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'learning_rate': self.learning_rate,
            'entropy_coef': self.entropy_coef,
            'search_depth': self.search_depth,
        }


class HyperparameterSearch:
    """超参数自动化搜索
    
    实现学习率、探索因子、搜索深度等超参数的自动化调优。
    """
    
    def __init__(
        self,
        model_template: DualResNet,
        evaluator: Evaluator,
        learning_rates: List[float] = None,
        entropy_coefs: List[float] = None,
        search_depths: List[int] = None,
    ):
        """
        参数：
        - model_template: 模型模板
        - evaluator: 评估器
        - learning_rates: 学习率候选列表
        - entropy_coefs: 探索因子候选列表
        - search_depths: 搜索深度候选列表
        """
        self.model_template = model_template
        self.evaluator = evaluator
        
        # 默认候选值
        if learning_rates is None:
            learning_rates = [1e-4, 3e-4, 1e-3, 3e-3]
        if entropy_coefs is None:
            entropy_coefs = [0.001, 0.01, 0.1, 0.5]
        if search_depths is None:
            search_depths = [50, 100, 200, 500]
        
        self.learning_rates = learning_rates
        self.entropy_coefs = entropy_coefs
        self.search_depths = search_depths
        
        # 搜索结果
        self.search_results: List[Tuple[HyperparameterConfig, float]] = []
    
    def grid_search(
        self,
        num_eval_games: int = 50,
    ) -> HyperparameterConfig:
        """
        网格搜索（Grid Search）
        
        参数：
        - num_eval_games: 每个配置的评估游戏数量
        
        返回：
        - 最佳超参数配置
        """
        # 生成所有超参数组合
        configs = []
        for lr, entropy, depth in itertools.product(
            self.learning_rates,
            self.entropy_coefs,
            self.search_depths,
        ):
            configs.append(HyperparameterConfig(
                learning_rate=lr,
                entropy_coef=entropy,
                search_depth=depth,
            ))
        
        # 评估每个配置
        best_config = None
        best_score = float('-inf')
        
        for config in configs:
            score = self._evaluate_config(config, num_eval_games)
            self.search_results.append((config, score))
            
            if score > best_score:
                best_score = score
                best_config = config
        
        return best_config
    
    def random_search(
        self,
        num_samples: int = 20,
        num_eval_games: int = 50,
    ) -> HyperparameterConfig:
        """
        随机搜索（Random Search）
        
        参数：
        - num_samples: 采样数量
        - num_eval_games: 每个配置的评估游戏数量
        
        返回：
        - 最佳超参数配置
        """
        best_config = None
        best_score = float('-inf')
        
        for _ in range(num_samples):
            # 随机选择超参数
            config = HyperparameterConfig(
                learning_rate=np.random.choice(self.learning_rates),
                entropy_coef=np.random.choice(self.entropy_coefs),
                search_depth=np.random.choice(self.search_depths),
            )
            
            # 评估配置
            score = self._evaluate_config(config, num_eval_games)
            self.search_results.append((config, score))
            
            if score > best_score:
                best_score = score
                best_config = config
        
        return best_config
    
    def bayesian_optimization(
        self,
        num_iterations: int = 20,
        num_eval_games: int = 50,
    ) -> HyperparameterConfig:
        """
        贝叶斯优化（Bayesian Optimization）
        
        参数：
        - num_iterations: 迭代次数
        - num_eval_games: 每个配置的评估游戏数量
        
        返回：
        - 最佳超参数配置
        """
        # 简化版：使用随机搜索作为占位符
        # 实际实现需要使用 GPyOpt 或 scikit-optimize
        return self.random_search(num_iterations, num_eval_games)
    
    def _evaluate_config(
        self,
        config: HyperparameterConfig,
        num_eval_games: int,
    ) -> float:
        """
        评估超参数配置
        
        参数：
        - config: 超参数配置
        - num_eval_games: 评估游戏数量
        
        返回：
        - 评估分数（平均胜率或平均得分）
        """
        # 从模板复制模型
        model = self._copy_model_from_template()
        
        # 创建 PPO
        ppo = PPO(
            model=model,
            learning_rate=config.learning_rate,
            entropy_coef=config.entropy_coef,
        )
        
        # 评估模型
        stats = self.evaluator.evaluate_model(
            model=model,
            model_id=f"config_{len(self.search_results)}",
            num_games=num_eval_games,
        )
        
        # 返回评估分数（使用平均得分）
        return stats.get('avg_score', 0.0)
    
    def _copy_model_from_template(self) -> DualResNet:
        """
        从模板模型复制一个新模型
        
        返回：
        - 新模型实例（与模板具有相同的结构和参数）
        """
        import torch
        import copy
        
        # 方法1：尝试使用 deepcopy（最简单，但可能在某些情况下失败）
        try:
            model = copy.deepcopy(self.model_template)
            return model
        except Exception as e:
            # 如果 deepcopy 失败，使用方法2：创建新模型并复制 state_dict
            pass
        
        # 方法2：创建新模型并复制参数
        # 获取模板模型的配置信息
        template_info = self.model_template.get_model_info()
        
        # 创建新模型（使用相同的架构参数）
        model = DualResNet(
            input_channels=64,  # 默认值
            num_blocks=template_info.get('num_blocks', 20),
            base_channels=128,  # 默认值
            feature_dim=template_info.get('feature_dim', 512),
            action_space_size=template_info.get('action_space_size', 434),
            hidden_dim=256,  # 默认值
        )
        
        # 复制模板模型的参数（state_dict）
        # 注意：这要求新模型和模板模型具有相同的架构
        try:
            model.load_state_dict(self.model_template.state_dict(), strict=False)
        except Exception as e:
            # 如果复制失败（例如架构不匹配），使用随机初始化的模型
            print(f"Warning: Failed to copy model state_dict: {e}. Using randomly initialized model.")
        
        # 确保模型处于评估模式（与模板一致）
        if hasattr(self.model_template, 'training'):
            model.train(self.model_template.training)
        else:
            model.eval()
        
        return model
    
    def get_best_config(self) -> Optional[HyperparameterConfig]:
        """
        获取最佳超参数配置
        
        返回：
        - 最佳配置，如果没有结果则返回 None
        """
        if not self.search_results:
            return None
        
        best_config, _ = max(self.search_results, key=lambda x: x[1])
        return best_config
    
    def get_search_results(self) -> List[Tuple[HyperparameterConfig, float]]:
        """
        获取搜索结果
        
        返回：
        - 搜索结果列表（配置，分数）
        """
        return self.search_results.copy()

