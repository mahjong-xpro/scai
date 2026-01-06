"""
自对弈 Worker (Ray Worker)

使用 Ray 实现分布式自对弈，支持数百个 Rust 实例同时生成轨迹。
"""

import ray
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple
import time

# 注意：需要先安装 Ray: pip install ray

# 导入 Rust 引擎绑定
try:
    import scai_engine
except ImportError:
    raise ImportError(
        "scai_engine module not found. Please build the Rust extension first. "
        "Run: cd rust && maturin develop"
    )

from ..models import DualResNet
from ..training.reward_shaping import RewardShaping


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
        device: str = 'cpu',
    ):
        """
        参数：
        - worker_id: Worker ID
        - num_games: 每个 Worker 运行的游戏数量（默认 10）
        - use_oracle: 是否使用 Oracle 特征（默认 True）
        - device: 设备（'cpu' 或 'cuda'，默认 'cpu'）
        """
        self.worker_id = worker_id
        self.num_games = num_games
        self.use_oracle = use_oracle
        self.device = device
        
        # 初始化 Rust 引擎
        self.engine = scai_engine.PyGameEngine()
        
        # 初始化奖励函数
        self.reward_shaping = RewardShaping()
    
    def play_game(
        self,
        model: DualResNet,
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
        # 初始化游戏引擎
        engine = scai_engine.PyGameEngine()
        engine.initialize()
        
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
        
        # 游戏主循环
        max_turns = 200
        turn_count = 0
        
        while not engine.is_game_over() and turn_count < max_turns:
            turn_count += 1
            
            # 获取当前游戏状态
            state = engine.state
            current_player = state.current_player
            
            # 检查玩家是否已离场
            if state.is_player_out(current_player):
                # 跳过已离场的玩家
                continue
            
            # 获取游戏状态张量
            remaining_tiles = engine.remaining_tiles()
            wall_dist = None  # 如果需要 Oracle 特征，需要计算牌堆余牌分布
            
            state_tensor = scai_engine.state_to_tensor(
                state,
                player_id=current_player,
                remaining_tiles=remaining_tiles,
                use_oracle=self.use_oracle,
                wall_tile_distribution=wall_dist,
            )
            
            # 获取动作掩码
            is_own_turn = True  # 自己的回合
            action_mask = scai_engine.PyActionMask.get_action_mask(
                current_player,
                state,
                is_own_turn,
                None,  # 没有别人打出的牌
            )
            
            # 转换为 PyTorch 张量
            state_tensor_torch = torch.from_numpy(state_tensor).float().unsqueeze(0).to(self.device)
            action_mask_torch = torch.from_numpy(np.array(action_mask, dtype=np.float32)).float().unsqueeze(0).to(self.device)
            
            # 模型推理
            model.eval()
            with torch.no_grad():
                policy, value = model(state_tensor_torch, action_mask_torch)
            
            # 采样动作
            policy_np = policy.cpu().numpy()[0]
            action_mask_np = action_mask_torch.cpu().numpy()[0]
            
            # 应用动作掩码
            masked_policy = policy_np * action_mask_np
            masked_policy_sum = masked_policy.sum()
            if masked_policy_sum > 1e-8:
                masked_policy = masked_policy / masked_policy_sum
            else:
                # 如果没有合法动作，使用均匀分布
                masked_policy = action_mask_np / (action_mask_np.sum() + 1e-8)
            
            # 采样动作
            action_index = np.random.choice(len(masked_policy), p=masked_policy)
            log_prob = np.log(masked_policy[action_index] + 1e-8)
            value_np = value.cpu().numpy()[0, 0]
            
            # 记录轨迹
            trajectory['states'].append(state_tensor)
            trajectory['actions'].append(int(action_index))
            trajectory['values'].append(float(value_np))
            trajectory['log_probs'].append(float(log_prob))
            trajectory['action_masks'].append(action_mask)
            trajectory['dones'].append(False)
            
            # 将动作索引转换为动作类型和参数
            action_type, tile_index, is_concealed = self._index_to_action_params(
                action_index, state, current_player
            )
            
            # 执行动作
            try:
                result = engine.process_action(
                    current_player,
                    action_type,
                    tile_index,
                    is_concealed,
                )
                
                # 检查是否胡牌
                if isinstance(result, dict) and result.get('type') == 'won':
                    # 游戏结束
                    trajectory['dones'][-1] = True
                    # 计算最终得分（简化处理）
                    final_score = 0.0  # 需要从结算结果中提取
                    trajectory['final_score'] = final_score
                    break
                
            except Exception as e:
                print(f"Worker {self.worker_id}, Game {game_id}, Turn {turn_count} error: {e}")
                # 如果动作失败，跳过这个回合
                continue
        
        # 如果游戏正常结束，设置最后一个时间步的 done 标志
        if len(trajectory['dones']) > 0 and not trajectory['dones'][-1]:
            trajectory['dones'][-1] = True
        
        # 计算每步奖励
        for i in range(len(trajectory['states'])):
            # 简化处理：根据游戏状态计算奖励
            # 实际应该从游戏状态中获取听牌、胡牌等信息
            reward = self.reward_shaping.compute_step_reward(
                is_ready=False,
                is_hu=False,
                is_flower_pig=False,
            )
            trajectory['rewards'].append(reward)
        
        # 添加最终奖励
        if trajectory['final_score'] != 0.0:
            final_reward = self.reward_shaping.compute_final_reward(
                trajectory['final_score'],
                is_winner=False,  # 需要从结算结果中判断
            )
            if len(trajectory['rewards']) > 0:
                trajectory['rewards'][-1] += final_reward
        
        return trajectory
    
    def _index_to_action_params(
        self,
        action_index: int,
        state,
        player_id: int,
    ) -> Tuple[str, Optional[int], Optional[bool]]:
        """
        将动作索引转换为动作类型和参数
        
        返回：
        - (action_type, tile_index, is_concealed)
        """
        # 动作空间编码：434 个动作
        # 0-107: 出牌（108 种牌）
        # 108-215: 碰（108 种牌）
        # 216-323: 杠（108 种牌）
        # 324-431: 胡（108 种牌）
        # 432: 过
        # 433: 摸牌（Draw）
        
        if action_index < 108:
            # 出牌
            return "discard", action_index, None
        elif action_index < 216:
            # 碰
            tile_index = action_index - 108
            return "pong", tile_index, None
        elif action_index < 324:
            # 杠
            tile_index = action_index - 216
            return "gang", tile_index, False  # 默认明杠
        elif action_index < 432:
            # 胡
            return "win", None, None
        elif action_index == 432:
            # 过
            return "pass", None, None
        else:
            # 摸牌（Draw）
            return "draw", None, None
    
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
        model_config: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        运行 Worker
        
        参数：
        - model_state_dict: 模型状态字典
        - model_config: 模型配置（可选，如果提供则创建新模型）
        
        返回：
        - 轨迹列表
        """
        # 加载模型
        if model_config is None:
            # 使用默认配置
            model_config = {
                'input_channels': 64,
                'num_blocks': 20,
                'base_channels': 128,
                'feature_dim': 512,
                'action_space_size': 434,
                'hidden_dim': 256,
            }
        
        model = DualResNet(**model_config)
        model.load_state_dict(model_state_dict)
        model.to(self.device)
        model.eval()
        
        # 收集轨迹
        trajectories = self.collect_trajectories(model)
        
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

