"""
自对弈 Worker (Ray Worker)

使用 Ray 实现分布式自对弈，支持数百个 Rust 实例同时生成轨迹。
"""

import ray
import numpy as np
from typing import Dict, List, Optional, Tuple
import time

# 注意：需要先安装 Ray: pip install ray


@ray.remote
class SelfPlayWorker:
    """自对弈 Worker
    
    使用 Ray 实现分布式自对弈，每个 Worker 运行多个游戏实例。
    """
    
    def __init__(
        self,
        worker_id: int,
        num_games: int = 10,
        use_oracle: bool = True,
    ):
        """
        参数：
        - worker_id: Worker ID
        - num_games: 每个 Worker 运行的游戏数量（默认 10）
        - use_oracle: 是否使用 Oracle 特征（默认 True）
        """
        self.worker_id = worker_id
        self.num_games = num_games
        self.use_oracle = use_oracle
        
        # 这里应该初始化 Rust 引擎
        # 目前使用占位符
        self.engine = None  # TODO: 初始化 Rust 引擎
    
    def play_game(
        self,
        model,
        game_id: int,
    ) -> Dict:
        """
        运行一局游戏
        
        参数：
        - model: 神经网络模型
        - game_id: 游戏 ID
        
        返回：
        - 包含游戏轨迹的字典
        """
        # TODO: 实现实际游戏逻辑
        # 目前返回占位符数据
        
        trajectory = {
            'states': [],
            'actions': [],
            'rewards': [],
            'values': [],
            'log_probs': [],
            'dones': [],
            'action_masks': [],
            'final_score': 0.0,
        }
        
        # 模拟游戏过程
        num_steps = np.random.randint(50, 200)
        for step in range(num_steps):
            # 生成状态（占位符）
            state = np.random.randn(2412).astype(np.float32)
            action_mask = np.ones(434).astype(np.float32)
            
            # 模型选择动作
            # action, log_prob, value = model.get_action(state, action_mask)
            action = np.random.randint(0, 434)
            log_prob = np.random.uniform(-5, 0)
            value = np.random.uniform(-10, 10)
            
            # 计算奖励（占位符）
            reward = np.random.uniform(-1, 1)
            
            # 记录轨迹
            trajectory['states'].append(state)
            trajectory['actions'].append(action)
            trajectory['rewards'].append(reward)
            trajectory['values'].append(value)
            trajectory['log_probs'].append(log_prob)
            trajectory['dones'].append(False)
            trajectory['action_masks'].append(action_mask)
        
        # 最后一个时间步
        trajectory['dones'][-1] = True
        trajectory['final_score'] = np.random.normal(0, 10)
        
        return trajectory
    
    def collect_trajectories(
        self,
        model,
    ) -> List[Dict]:
        """
        收集轨迹数据
        
        参数：
        - model: 神经网络模型
        
        返回：
        - 轨迹列表
        """
        trajectories = []
        
        for game_id in range(self.num_games):
            trajectory = self.play_game(model, game_id)
            trajectories.append(trajectory)
        
        return trajectories
    
    def run(
        self,
        model_state_dict: Dict,
    ) -> List[Dict]:
        """
        运行 Worker
        
        参数：
        - model_state_dict: 模型状态字典
        
        返回：
        - 轨迹列表
        """
        # TODO: 加载模型
        # model = DualResNet(...)
        # model.load_state_dict(model_state_dict)
        
        # 收集轨迹
        trajectories = self.collect_trajectories(None)  # TODO: 传入模型
        
        return trajectories


def create_workers(
    num_workers: int = 100,
    num_games_per_worker: int = 10,
    use_oracle: bool = True,
) -> List:
    """
    创建多个 Worker
    
    参数：
    - num_workers: Worker 数量（默认 100）
    - num_games_per_worker: 每个 Worker 运行的游戏数量（默认 10）
    - use_oracle: 是否使用 Oracle 特征（默认 True）
    
    返回：
    - Worker 列表
    """
    workers = []
    for i in range(num_workers):
        worker = SelfPlayWorker.remote(
            worker_id=i,
            num_games=num_games_per_worker,
            use_oracle=use_oracle,
        )
        workers.append(worker)
    
    return workers


def collect_trajectories_parallel(
    workers: List,
    model_state_dict: Dict,
) -> List[Dict]:
    """
    并行收集轨迹
    
    参数：
    - workers: Worker 列表
    - model_state_dict: 模型状态字典
    
    返回：
    - 所有轨迹的列表
    """
    # 并行运行所有 Worker
    futures = [worker.run.remote(model_state_dict) for worker in workers]
    
    # 等待所有 Worker 完成
    results = ray.get(futures)
    
    # 合并所有轨迹
    all_trajectories = []
    for result in results:
        all_trajectories.extend(result)
    
    return all_trajectories

