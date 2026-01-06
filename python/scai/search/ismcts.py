"""
ISMCTS (Information Set Monte Carlo Tree Search) 搜索算法

在推理端实现信息集蒙特卡洛树搜索，对未知牌墙进行 Determinization 采样。
"""

import numpy as np
import torch
from typing import Dict, List, Optional, Tuple
import random
from collections import defaultdict

from ..models import DualResNet
from ..training.ppo import PPO

# 导入 Rust 游戏引擎（如果可用）
try:
    import scai_engine
    HAS_SCAI_ENGINE = True
except ImportError:
    HAS_SCAI_ENGINE = False


class ISMCTSNode:
    """ISMCTS 节点
    
    表示信息集蒙特卡洛树搜索树中的一个节点。
    """
    
    def __init__(
        self,
        action: Optional[int] = None,
        parent: Optional['ISMCTSNode'] = None,
    ):
        """
        参数：
        - action: 到达此节点的动作（根节点为 None）
        - parent: 父节点（根节点为 None）
        """
        self.action = action
        self.parent = parent
        
        # 访问统计
        self.visits = 0
        self.total_value = 0.0
        
        # 子节点
        self.children: Dict[int, 'ISMCTSNode'] = {}
        
        # 未探索的动作
        self.untried_actions: List[int] = []
    
    def is_fully_expanded(self) -> bool:
        """检查是否完全展开"""
        return len(self.untried_actions) == 0
    
    def is_terminal(self) -> bool:
        """检查是否是终端节点（叶子节点）"""
        return len(self.children) == 0
    
    def ucb1_value(self, exploration_constant: float = 1.414) -> float:
        """
        计算 UCB1 值
        
        参数：
        - exploration_constant: 探索常数（默认 sqrt(2)）
        
        返回：
        - UCB1 值
        """
        if self.visits == 0:
            return float('inf')
        
        exploitation = self.total_value / self.visits
        exploration = exploration_constant * np.sqrt(
            np.log(self.parent.visits) / self.visits
        ) if self.parent else 0.0
        
        return exploitation + exploration
    
    def select_child(self, exploration_constant: float = 1.414) -> 'ISMCTSNode':
        """
        选择子节点（UCB1）
        
        参数：
        - exploration_constant: 探索常数
        
        返回：
        - 选择的子节点
        """
        if not self.children:
            return None
        
        best_child = None
        best_value = float('-inf')
        
        for child in self.children.values():
            value = child.ucb1_value(exploration_constant)
            if value > best_value:
                best_value = value
                best_child = child
        
        return best_child
    
    def expand(self, action: int) -> 'ISMCTSNode':
        """
        展开节点（添加子节点）
        
        参数：
        - action: 动作
        
        返回：
        - 新创建的子节点
        """
        if action in self.children:
            return self.children[action]
        
        child = ISMCTSNode(action=action, parent=self)
        self.children[action] = child
        
        if action in self.untried_actions:
            self.untried_actions.remove(action)
        
        return child
    
    def update(self, value: float):
        """
        更新节点值
        
        参数：
        - value: 回报值
        """
        self.visits += 1
        self.total_value += value
    
    def get_best_action(self) -> Optional[int]:
        """
        获取最佳动作（访问次数最多的子节点）
        
        返回：
        - 最佳动作，如果没有子节点则返回 None
        """
        if not self.children:
            return None
        
        best_action = None
        best_visits = -1
        
        for action, child in self.children.items():
            if child.visits > best_visits:
                best_visits = child.visits
                best_action = action
        
        return best_action


class ISMCTS:
    """ISMCTS (Information Set Monte Carlo Tree Search) 搜索算法
    
    在推理端实现信息集蒙特卡洛树搜索，对未知牌墙进行 Determinization 采样。
    """
    
    def __init__(
        self,
        model: DualResNet,
        num_simulations: int = 100,
        exploration_constant: float = 1.414,
        determinization_samples: int = 10,
        device: str = 'cpu',
    ):
        """
        参数：
        - model: 神经网络模型
        - num_simulations: 模拟次数（默认 100）
        - exploration_constant: 探索常数（默认 sqrt(2)）
        - determinization_samples: Determinization 采样次数（默认 10）
        - device: 设备（'cpu' 或 'cuda'）
        """
        self.model = model
        self.num_simulations = num_simulations
        self.exploration_constant = exploration_constant
        self.determinization_samples = determinization_samples
        self.device = device
    
    def search(
        self,
        game_state,
        player_id: int,
        action_mask: np.ndarray,
        remaining_tiles: int,
        seed: Optional[int] = None,
    ) -> Tuple[int, Dict]:
        """
        执行 ISMCTS 搜索
        
        参数：
        - game_state: 游戏状态（PyGameState）
        - player_id: 当前玩家 ID
        - action_mask: 动作掩码
        - remaining_tiles: 剩余牌数
        - seed: 随机种子（可选）
        
        返回：
        - (最佳动作, 搜索统计信息)
        """
        root = ISMCTSNode()
        
        # 获取合法动作
        legal_actions = [i for i in range(len(action_mask)) if action_mask[i] > 0.5]
        root.untried_actions = legal_actions.copy()
        
        # 执行多次模拟
        for sim in range(self.num_simulations):
            # Determinization 采样
            determinization_seed = (seed + sim) if seed is not None else None
            
            # 创建确定化的游戏状态
            determinized_state = self._determinize_state(
                game_state,
                player_id,
                remaining_tiles,
                determinization_seed,
            )
            
            # 执行一次模拟
            value = self._simulate(root, determinized_state, player_id, action_mask)
            
            # 更新节点值
            self._backpropagate(root, value)
        
        # 获取最佳动作
        best_action = root.get_best_action()
        
        # 统计信息
        stats = {
            'visits': root.visits,
            'num_simulations': self.num_simulations,
            'children_visits': {
                action: child.visits
                for action, child in root.children.items()
            },
        }
        
        return best_action, stats
    
    def _determinize_state(
        self,
        game_state,
        player_id: int,
        remaining_tiles: int,
        seed: Optional[int] = None,
    ):
        """
        对未知牌墙进行 Determinization 采样
        
        参数：
        - game_state: 游戏状态
        - player_id: 当前玩家 ID
        - remaining_tiles: 剩余牌数
        - seed: 随机种子（可选）
        
        返回：
        - 确定化的游戏状态
        """
        # 创建游戏状态的副本
        # 使用 clone 方法（如果可用）或深拷贝
        if hasattr(game_state, 'clone'):
            determinized_state = game_state.clone()
        else:
            # 如果 PyGameState 没有 clone 方法，尝试使用 copy.deepcopy
            import copy
            determinized_state = copy.deepcopy(game_state)
        
        # 使用 fill_unknown_cards 方法填充未知牌
        if hasattr(determinized_state, 'fill_unknown_cards'):
            determinization_seed = seed if seed is not None else random.randint(0, 2**32)
            determinized_state.fill_unknown_cards(
                viewer_id=player_id,
                remaining_wall_count=remaining_tiles,
                seed=determinization_seed,
            )
        
        return determinized_state
    
    def _simulate(
        self,
        node: ISMCTSNode,
        game_state,
        player_id: int,
        action_mask: np.ndarray,
    ) -> float:
        """
        执行一次模拟（从当前节点到终端节点）
        
        参数：
        - node: 当前节点
        - game_state: 游戏状态
        - player_id: 当前玩家 ID
        - action_mask: 动作掩码
        
        返回：
        - 模拟回报值
        """
        current_node = node
        current_state = game_state
        depth = 0
        max_depth = 200  # 防止无限循环
        
        # Selection: 选择到叶子节点
        while not current_node.is_terminal() and depth < max_depth:
            if not current_node.is_fully_expanded():
                # Expansion: 展开节点
                action = current_node.untried_actions[0]
                current_node = current_node.expand(action)
                break
            else:
                # 选择最佳子节点
                current_node = current_node.select_child(self.exploration_constant)
                if current_node is None:
                    break
                # 在游戏状态中执行动作
                current_state = self._apply_action(current_state, current_node.action, player_id)
                depth += 1
        
        # Rollout: 从当前状态随机模拟到终端
        value = self._rollout(current_state, player_id, action_mask)
        
        return value
    
    def _rollout(
        self,
        game_state,
        player_id: int,
        action_mask: np.ndarray,
    ) -> float:
        """
        随机模拟（Rollout）到终端节点
        
        参数：
        - game_state: 游戏状态
        - player_id: 当前玩家 ID
        - action_mask: 动作掩码
        
        返回：
        - 模拟回报值
        """
        # 使用神经网络模型进行快速评估
        # 将游戏状态转换为张量
        state_tensor = self._state_to_tensor(game_state, player_id)
        action_mask_tensor = torch.FloatTensor(action_mask).unsqueeze(0).to(self.device)
        
        # 获取价值估计
        self.model.eval()
        with torch.no_grad():
            _, value = self.model(state_tensor, action_mask_tensor)
            value_estimate = value.item()
        
        self.model.train()
        
        return value_estimate
    
    def _state_to_tensor(
        self,
        game_state,
        player_id: int,
    ) -> torch.Tensor:
        """
        将游戏状态转换为张量
        
        参数：
        - game_state: 游戏状态
        - player_id: 当前玩家 ID
        
        返回：
        - 状态张量
        """
        # 使用游戏状态的 to_tensor 方法
        if hasattr(game_state, 'to_tensor'):
            state_vector = game_state.to_tensor(
                player_id=player_id,
                remaining_tiles=None,
                use_oracle=False,  # 推理时不使用 Oracle
                wall_tile_distribution=None,
            )
            state_tensor = torch.FloatTensor(state_vector).unsqueeze(0).to(self.device)
            return state_tensor
        else:
            # 占位符：返回随机张量
            return torch.randn(1, 2412).to(self.device)
    
    def _apply_action(
        self,
        game_state,
        action_index: int,
        player_id: int,
    ):
        """
        在游戏状态中执行动作（简化版本，用于 ISMCTS 快速模拟）
        
        注意：这是一个简化实现，不完整执行所有游戏逻辑。
        对于 ISMCTS 的快速模拟，我们主要依赖后续的 rollout（神经网络评估），
        而不是完整的状态转换。
        
        参数：
        - game_state: 游戏状态（PyGameState）
        - action_index: 动作索引（0-433）
        - player_id: 执行动作的玩家 ID
        
        返回：
        - 执行动作后的新游戏状态（简化版本）
        """
        # 克隆游戏状态
        if hasattr(game_state, 'clone'):
            new_state = game_state.clone()
        else:
            # 如果没有 clone 方法，使用深拷贝
            import copy
            new_state = copy.deepcopy(game_state)
        
        # 简化处理：对于 ISMCTS 模拟，我们不需要完整执行动作
        # 因为后续的 rollout 会使用神经网络进行快速评估
        # 这里我们只更新一些基本状态（如当前玩家），
        # 完整的状态转换逻辑在 rollout 阶段通过神经网络评估来近似
        
        # 更新当前玩家（循环到下一个玩家）
        if hasattr(new_state, 'set_current_player'):
            next_player = (player_id + 1) % 4
            new_state.set_current_player(next_player)
        
        # 注意：这里不完整执行动作（如摸牌、出牌等），
        # 因为完整执行需要访问引擎的私有状态（如牌墙），
        # 而且对于 ISMCTS 的快速模拟来说，完整执行会太慢。
        # 我们依赖后续的神经网络 rollout 来评估状态价值。
        
        return new_state
    
    def _index_to_action_params(
        self,
        action_index: int,
        state,
        player_id: int,
    ) -> Tuple[str, Optional[int], Optional[bool]]:
        """
        将动作索引转换为动作类型和参数
        
        参数：
        - action_index: 动作索引（0-433）
        - state: 游戏状态
        - player_id: 玩家 ID
        
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
            return "discard", action_index, None
        elif action_index < 216:
            tile_index = action_index - 108
            return "pong", tile_index, None
        elif action_index < 324:
            tile_index = action_index - 216
            return "gang", tile_index, False  # 默认明杠
        elif action_index < 432:
            return "win", None, None
        elif action_index == 432:
            return "pass", None, None
        else:
            return "draw", None, None
    
    def _backpropagate(self, node: ISMCTSNode, value: float):
        """
        反向传播更新节点值
        
        参数：
        - node: 节点
        - value: 回报值
        """
        current = node
        while current is not None:
            current.update(value)
            current = current.parent
    
    def get_action_with_search(
        self,
        game_state,
        player_id: int,
        action_mask: np.ndarray,
        remaining_tiles: int,
        seed: Optional[int] = None,
    ) -> Tuple[int, Dict]:
        """
        使用 ISMCTS 搜索选择动作
        
        参数：
        - game_state: 游戏状态
        - player_id: 当前玩家 ID
        - action_mask: 动作掩码
        - remaining_tiles: 剩余牌数
        - seed: 随机种子（可选）
        
        返回：
        - (选择的动作, 搜索统计信息)
        """
        return self.search(
            game_state,
            player_id,
            action_mask,
            remaining_tiles,
            seed,
        )

