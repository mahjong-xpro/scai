"""
自对弈 Worker (Ray Worker)

使用 Ray 实现分布式自对弈，支持数百个 Rust 实例同时生成轨迹。
"""

import ray
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple, Any
import time
import random
import os

# 注意：需要先安装 Ray: pip install ray

# 确保状态验证默认禁用（避免过于严格的验证导致游戏中断）
# 如果需要调试，可以通过环境变量 SCAI_ENABLE_STATE_VALIDATION=1 启用
if "SCAI_ENABLE_STATE_VALIDATION" not in os.environ:
    os.environ["SCAI_ENABLE_STATE_VALIDATION"] = "0"

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
        ismcts: Optional[Any] = None,
        use_search_enhanced: bool = False,
        critical_decision_threshold: float = 0.8,
        use_feeding: bool = False,
        feeding_config: Optional[Any] = None,
        enable_win: bool = True,
        reward_config: Optional[Dict] = None,
    ):
        """
        参数：
        - worker_id: Worker ID
        - num_games: 每个 Worker 运行的游戏数量（默认 10）
        - use_oracle: 是否使用 Oracle 特征（默认 True）
        - device: 设备（'cpu' 或 'cuda'，默认 'cpu'）
        - ismcts: ISMCTS 搜索器（可选）
        - use_search_enhanced: 是否使用搜索增强推理（默认 False）
        - critical_decision_threshold: 关键决策阈值（默认 0.8）
        - use_feeding: 是否使用喂牌模式（默认 False）
        - feeding_config: 喂牌配置（可选）
        - enable_win: 是否允许胡牌（默认 True，所有阶段都允许，通过奖励函数引导是否追求）
        - reward_config: 奖励配置（可选，用于与主进程保持一致）
        """
        self.worker_id = worker_id
        self.num_games = num_games
        self.use_oracle = use_oracle
        self.device = device
        self.ismcts = ismcts
        self.use_search_enhanced = use_search_enhanced and ismcts is not None
        self.critical_decision_threshold = critical_decision_threshold
        self.use_feeding = use_feeding
        self.feeding_config = feeding_config
        self.enable_win = enable_win  # 是否开启胡牌功能
        
        # 初始化 Rust 引擎
        self.engine = scai_engine.PyGameEngine()
        
        # 初始化奖励函数（使用传入的 reward_config，确保与主进程一致）
        self.reward_shaping = RewardShaping(reward_config=reward_config or {})
        
        # 初始化喂牌生成器（如果启用）
        if self.use_feeding and self.feeding_config:
            from .feeding_games import FeedingGameGenerator
            self.feeding_generator = FeedingGameGenerator(
                difficulty=self.feeding_config.difficulty
            )
        else:
            self.feeding_generator = None
    
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
        
        # 喂牌机制：如果启用，生成喂牌牌局
        if self.use_feeding and self.feeding_generator and self.feeding_config:
            # 使用配置中的 feeding_rate（2:8 比例，即 20% 喂牌，80% 随机）
            should_feed = random.random() < self.feeding_config.feeding_rate
            if should_feed:
                try:
                    # 选择胡牌类型
                    win_type = 'basic'
                    if self.feeding_config and self.feeding_config.win_types:
                        win_type = random.choice(self.feeding_config.win_types)
                    
                    # 生成喂牌游戏（给玩家0，即AI玩家）
                    feeding_engine = self.feeding_generator.create_feeding_game(
                        target_player_id=0,
                        win_type=win_type,
                    )
                    
                    if feeding_engine is not None:
                        # 使用喂牌引擎替换正常引擎
                        engine = feeding_engine
                        # 记录这是喂牌局（用于统计）
                        is_feeding_game = True
                    else:
                        # 如果生成失败，使用正常牌局
                        is_feeding_game = False
                except Exception as e:
                    # 如果喂牌失败，继续使用正常牌局
                    print(f"Worker {self.worker_id}, Game {game_id}, Feeding game error: {e}")
                    is_feeding_game = False
            else:
                is_feeding_game = False
        else:
            is_feeding_game = False
        
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
        
        # 定缺阶段：所有玩家必须定缺
        for player_id in range(4):
            try:
                state = engine.state
            except Exception as e:
                error_str = str(e)
                # 如果是状态验证错误，可能是验证逻辑过于严格，跳过这个游戏
                if "Game state validation failed" in error_str or "InvalidState" in error_str:
                    # 在定缺阶段，如果状态验证失败，跳过这个游戏（不打印错误，避免日志过多）
                    return {
                        'states': [],
                        'actions': [],
                        'rewards': [],
                        'values': [],
                        'log_probs': [],
                    'dones': [],
                    'action_masks': [],
                    'final_score': 0.0,
                }
            
            if state.get_player_declared_suit(player_id) is not None:
                continue  # 已经定缺
            
            # 选择手牌中最少的花色作为定缺
            hand = state.get_player_hand(player_id)
            suit_counts = {'Wan': 0, 'Tong': 0, 'Tiao': 0}
            for tile_str, count in hand.items():
                if 'Wan' in tile_str:
                    suit_counts['Wan'] += count
                elif 'Tong' in tile_str:
                    suit_counts['Tong'] += count
                elif 'Tiao' in tile_str:
                    suit_counts['Tiao'] += count
            
            # 选择最少的花色
            min_suit = min(suit_counts.items(), key=lambda x: x[1])[0]
            # 执行定缺
            try:
                engine.declare_suit(player_id, min_suit)
            except Exception as e:
                print(f"Worker {self.worker_id}, Game {game_id}, Declare suit error: {e}")
                # 如果定缺失败，使用默认值
                engine.declare_suit(player_id, 'Wan')
        
        # 游戏主循环
        max_turns = 200
        turn_count = 0
        
        while not engine.is_game_over() and turn_count < max_turns:
            turn_count += 1
            
            # 获取当前游戏状态
            try:
                state = engine.state
                current_player = state.current_player
            except Exception as e:
                error_str = str(e)
                # 如果是状态验证错误，记录但不中断游戏（验证可能过于严格）
                if "Game state validation failed" in error_str or "InvalidState" in error_str:
                    # 状态验证失败，可能是验证逻辑过于严格，尝试继续游戏
                    # 如果游戏已经结束，则正常退出
                    if engine.remaining_tiles() == 0:
                        break
                    # 否则记录警告并尝试继续
                    # 不打印每个错误，避免日志过多
                    continue
                print(f"Worker {self.worker_id}, Game {game_id}, Turn {turn_count}, Failed to get state: {e}")
                # 如果状态获取失败，结束游戏
                break
            
            # 检查玩家是否已离场
            if state.is_player_out(current_player):
                # 跳过已离场的玩家
                # 注意：需要切换到下一个玩家，但 PyGameEngine 可能没有 next_turn() 方法
                continue
            
            # 先摸牌（如果是自己的回合）
            # 检查牌墙是否为空，避免 WallEmpty 错误
            remaining = engine.remaining_tiles()
            if remaining == 0:
                # 牌墙已空，游戏结束
                break
            
            try:
                # 使用 process_action 执行摸牌
                draw_result = engine.process_action(
                    current_player,
                    "draw",
                    None,
                    None,
                )
                # 检查摸牌结果
                if isinstance(draw_result, dict):
                    if draw_result.get('type') == 'error':
                        # 摸牌失败，可能是游戏结束
                        error_msg = draw_result.get('error', 'Unknown error')
                        if 'WallEmpty' in str(error_msg):
                            # 牌墙已空，正常结束
                            break
                        print(f"Worker {self.worker_id}, Game {game_id}, Turn {turn_count}, Draw error: {error_msg}")
                        break
                    # 摸牌成功，继续处理
            except Exception as e:
                error_str = str(e)
                if 'WallEmpty' in error_str:
                    # 牌墙已空，正常结束
                    break
                print(f"Worker {self.worker_id}, Game {game_id}, Turn {turn_count}, Draw error: {e}")
                # 如果摸牌失败，可能是游戏结束
                break
            
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
            
            # 注意：不再强制禁用胡牌动作
            # 初期阶段通过奖励函数引导AI不追求胡牌（不给胡牌奖励）
            # 让AI自然学习到"这个阶段很难胡牌，所以不追求胡牌"
            
            # 转换为 PyTorch 张量
            state_tensor_torch = torch.from_numpy(state_tensor).float().unsqueeze(0).to(self.device)
            action_mask_torch = torch.from_numpy(np.array(action_mask, dtype=np.float32)).float().unsqueeze(0).to(self.device)
            
            # 判断是否使用搜索增强推理
            use_search = False
            if self.use_search_enhanced:
                # 计算价值函数的方差（简化：使用 policy 的熵作为不确定性指标）
                model.eval()
                with torch.no_grad():
                    policy, value = model(state_tensor_torch, action_mask_torch)
                
                policy_np = policy.cpu().numpy()[0]
                # 计算熵（不确定性）
                entropy = -np.sum(policy_np * np.log(policy_np + 1e-8))
                # 如果熵高（不确定性大），使用搜索
                max_entropy = np.log(len(policy_np))  # 最大熵
                uncertainty = entropy / max_entropy
                use_search = uncertainty > self.critical_decision_threshold
            
            if use_search and self.ismcts is not None:
                # 使用 ISMCTS 搜索
                try:
                    action_index, log_prob, value_np = self.ismcts.search(
                        game_state=state,
                        model=model,
                        action_mask=action_mask,
                        current_player=current_player,
                    )
                except Exception as e:
                    # 如果搜索失败，回退到普通推理
                    print(f"Worker {self.worker_id}, ISMCTS search failed: {e}, falling back to normal inference")
                    use_search = False
            
            if not use_search:
                # 普通模型推理
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
            
            # 记录轨迹（在动作执行前）
            # 确保 action_mask 是 numpy 数组（get_action_mask 返回的是 Python 列表）
            action_mask_array = np.array(action_mask, dtype=np.float32)
            
            trajectory['states'].append(state_tensor)
            trajectory['actions'].append(int(action_index))
            trajectory['values'].append(float(value_np))
            trajectory['log_probs'].append(float(log_prob))
            trajectory['action_masks'].append(action_mask_array)
            trajectory['dones'].append(False)
            
            # 将动作索引转换为动作类型和参数
            action_type, tile_index, is_concealed = self._index_to_action_params(
                action_index, state, current_player
            )
            
            # 在执行动作前，获取玩家定缺的花色（用于检查缺门弃牌奖励）
            declared_suit = None
            try:
                declared_suit = state.get_player_declared_suit(current_player)
            except Exception:
                pass  # 如果获取失败，忽略（可能还未定缺）
            
            # 检查是否打出了缺门牌
            lack_color_discard = False
            if action_type == "discard" and tile_index is not None and declared_suit is not None:
                lack_color_discard = self._is_lack_color_tile(tile_index, declared_suit)
            
            # 执行动作
            is_hu = False
            try:
                result = engine.process_action(
                    current_player,
                    action_type,
                    tile_index,
                    is_concealed,
                )
                
                # 更新状态以获取最新信息（用于奖励计算）
                try:
                    state = engine.state
                    is_ready_after = state.is_player_ready(current_player)
                    is_flower_pig = self._check_flower_pig(state, current_player)
                except Exception as e:
                    error_str = str(e)
                    # 如果是状态验证错误，使用默认值并继续（验证可能过于严格）
                    if "Game state validation failed" in error_str or "InvalidState" in error_str:
                        # 不打印每个错误，避免日志过多
                        is_ready_after = False
                        is_flower_pig = False
                    else:
                        # 其他错误才打印
                        print(f"Worker {self.worker_id}, Game {game_id}, Turn {turn_count}, Failed to get state after action: {e}")
                        is_ready_after = False
                        is_flower_pig = False
                
                # 检查是否胡牌
                if isinstance(result, dict) and result.get('type') == 'won':
                    # 游戏结束
                    trajectory['dones'][-1] = True
                    is_hu = True
                    
                    # 从结算结果中提取最终得分
                    settlement_str = result.get('settlement', '')
                    final_score = self._extract_final_score_from_settlement(
                        settlement_str, current_player
                    )
                    trajectory['final_score'] = final_score
                    
                    # 计算奖励（胡牌奖励）
                    reward = self.reward_shaping.compute_step_reward(
                        is_ready=is_ready_after,
                        is_hu=is_hu,
                        is_flower_pig=is_flower_pig,
                        lack_color_discard=lack_color_discard,
                    )
                    trajectory['rewards'].append(reward)
                    break
                else:
                    # 计算奖励（非胡牌情况）
                    reward = self.reward_shaping.compute_step_reward(
                        is_ready=is_ready_after,
                        is_hu=is_hu,
                        is_flower_pig=is_flower_pig,
                        lack_color_discard=lack_color_discard,
                    )
                    trajectory['rewards'].append(reward)
                
            except Exception as e:
                print(f"Worker {self.worker_id}, Game {game_id}, Turn {turn_count} error: {e}")
                # 如果动作失败，添加默认奖励并跳过这个回合
                trajectory['rewards'].append(0.0)
                continue
        
        # 如果游戏正常结束，设置最后一个时间步的 done 标志
        if len(trajectory['dones']) > 0 and not trajectory['dones'][-1]:
            trajectory['dones'][-1] = True
        
        # 确保奖励数量与状态数量一致
        # 注意：奖励已经在动作执行后计算并添加，这里只需要确保数量一致
        if len(trajectory['rewards']) < len(trajectory['states']):
            missing = len(trajectory['states']) - len(trajectory['rewards'])
            print(f"Worker {self.worker_id}, Game {game_id}: Warning: {missing} rewards missing, padding with 0.0")
            trajectory['rewards'].extend([0.0] * missing)
        elif len(trajectory['rewards']) > len(trajectory['states']):
            # 不应该发生，但需要处理
            extra = len(trajectory['rewards']) - len(trajectory['states'])
            print(f"Worker {self.worker_id}, Game {game_id}: Warning: {extra} extra rewards, truncating")
            trajectory['rewards'] = trajectory['rewards'][:len(trajectory['states'])]
        
        # 添加最终奖励（如果有最终得分）
        if trajectory['final_score'] != 0.0:
            # 判断是否获胜（得分 > 0 表示获胜）
            is_winner = trajectory['final_score'] > 0
            final_reward = self.reward_shaping.compute_final_reward(
                trajectory['final_score'],
                is_winner=is_winner,
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
    
    def _extract_final_score_from_settlement(
        self,
        settlement_str: str,
        player_id: int,
    ) -> float:
        """
        从结算结果字符串中提取最终得分
        
        参数：
        - settlement_str: 结算结果字符串（格式化的字典字符串）
        - player_id: 玩家 ID
        
        返回：
        - 最终得分
        """
        # 简化处理：从结算结果中解析得分
        # 实际实现需要解析 SettlementResult 结构
        # 这里使用占位符，实际应该解析 settlement_str
        try:
            # 尝试从字符串中提取数字
            # 注意：这是一个简化实现，实际应该解析完整的结算结果
            import re
            # 查找玩家 ID 对应的得分
            # 格式可能是：payments: {player_id: score}
            pattern = rf'{player_id}:\s*([+-]?\d+)'
            match = re.search(pattern, settlement_str)
            if match:
                return float(match.group(1))
        except Exception as e:
            print(f"Error extracting final score: {e}")
        
        # 如果解析失败，返回 0
        return 0.0
    
    def _is_lack_color_tile(
        self,
        tile_index: int,
        declared_suit: str,
    ) -> bool:
        """
        检查打出的牌是否是缺门牌（定缺花色）
        
        参数：
        - tile_index: 牌索引（0-107）
        - declared_suit: 定缺花色（"Wan", "Tong", "Tiao"）
        
        返回：
        - 是否是缺门牌
        """
        if tile_index < 0 or tile_index >= 108:
            return False
        
        # 根据 tile_index 计算花色索引
        # tile_index 范围：0-107
        # 0-35: Wan (suit_index=0)
        # 36-71: Tong (suit_index=1)
        # 72-107: Tiao (suit_index=2)
        suit_index = tile_index // 36
        
        # 将定缺花色字符串映射到索引
        suit_map = {
            "Wan": 0,
            "Tong": 1,
            "Tiao": 2,
        }
        
        declared_suit_index = suit_map.get(declared_suit)
        if declared_suit_index is None:
            return False
        
        # 如果打出的牌的花色索引等于定缺花色索引，说明打出了缺门牌
        return suit_index == declared_suit_index
    
    def _check_flower_pig(
        self,
        state,
        player_id: int,
    ) -> bool:
        """
        检查玩家是否成为花猪（未打完缺门）
        
        参数：
        - state: 游戏状态
        - player_id: 玩家 ID
        
        返回：
        - 是否是花猪
        """
        try:
            # 获取玩家定缺花色
            declared_suit_str = state.get_player_declared_suit(player_id)
            if declared_suit_str is None:
                return False  # 未定缺，不算花猪
            
            # 获取玩家手牌
            hand = state.get_player_hand(player_id)
            
            # 检查手牌中是否还有定缺花色的牌
            for tile_str, count in hand.items():
                if declared_suit_str in tile_str and count > 0:
                    return True  # 还有定缺花色的牌，是花猪
            
            return False  # 定缺花色已打完，不是花猪
        except Exception as e:
            print(f"Error checking flower pig: {e}")
            return False
    
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
        # 确保 state_dict 在 CPU 上加载（即使原始模型在 CUDA 上）
        # 这样可以避免 Ray 序列化/反序列化时的设备不匹配问题
        model.load_state_dict(model_state_dict)
        # 加载后再移动到目标设备
        model.to(self.device)
        model.eval()
        
        # 收集轨迹
        trajectories = self.collect_trajectories(model)
        
        return trajectories


def create_workers(
    num_workers: int = 100,
    num_games_per_worker: int = 10,
    use_oracle: bool = True,
    ismcts: Optional[Any] = None,
    use_search_enhanced: bool = False,
    critical_decision_threshold: float = 0.8,
    use_feeding: bool = False,
    feeding_config: Optional[Any] = None,
    enable_win: bool = True,
    reward_config: Optional[Dict] = None,
) -> List:
    """
    创建多个 Worker
    
    参数：
    - num_workers: Worker 数量（默认 100）
    - num_games_per_worker: 每个 Worker 运行的游戏数量（默认 10）
    - use_oracle: 是否使用 Oracle 特征（默认 True）
    - ismcts: ISMCTS 搜索器（可选）
    - use_search_enhanced: 是否使用搜索增强推理（默认 False）
    - critical_decision_threshold: 关键决策阈值（默认 0.8）
    - use_feeding: 是否使用喂牌模式（默认 False）
    - feeding_config: 喂牌配置（可选）
    - enable_win: 是否开启胡牌功能（默认 True）
    
    返回：
    - Worker 列表
    """
    import logging
    logger = logging.getLogger(__name__)
    
    workers = []
    # 分批创建 workers，避免一次性创建太多导致卡住
    batch_size = min(10, num_workers)  # 每批最多 10 个
    
    for i in range(0, num_workers, batch_size):
        batch_end = min(i + batch_size, num_workers)
        logger.info(f"Creating workers {i} to {batch_end-1} ({batch_end-i}/{num_workers})...")
        
        for j in range(i, batch_end):
            try:
                worker = SelfPlayWorker.remote(
                    worker_id=j,
                    num_games=num_games_per_worker,
                    use_oracle=use_oracle,
                    ismcts=ismcts,  # 注意：Ray 可能无法序列化 ISMCTS，需要特殊处理
                    use_search_enhanced=use_search_enhanced,
                    critical_decision_threshold=critical_decision_threshold,
                    use_feeding=use_feeding,
                    feeding_config=feeding_config,
                    enable_win=enable_win,
                    reward_config=reward_config,
                )
                workers.append(worker)
            except Exception as e:
                logger.error(f"Failed to create worker {j}: {e}")
                # 继续创建其他 workers
                continue
        
        logger.info(f"Created {len(workers)}/{num_workers} workers so far...")
    
    logger.info(f"All {len(workers)} workers created successfully")
    return workers


def collect_trajectories_parallel(
    workers: List,
    model_state_dict: Dict,
    reward_config: Optional[Dict] = None,
) -> List[Dict]:
    """
    并行收集轨迹
    
    参数：
    - workers: Worker 列表
    - model_state_dict: 模型状态字典
    
    返回：
    - 所有轨迹的列表
    """
    import logging
    import time
    logger = logging.getLogger(__name__)
    
    logger.info(f"Submitting {len(workers)} worker tasks...")
    # 并行运行所有 Worker
    futures = [worker.run.remote(model_state_dict) for worker in workers]
    logger.info(f"All {len(futures)} tasks submitted, waiting for results...")
    
    # 使用 ray.wait 处理部分失败，提高健壮性
    all_trajectories = []
    remaining_futures = futures
    failed_workers = 0
    start_time = time.time()
    last_log_time = start_time
    
    while remaining_futures:
        try:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # 每 10 秒记录一次进度
            if current_time - last_log_time >= 10.0:
                logger.info(f"Waiting for {len(remaining_futures)} workers... "
                          f"(elapsed: {elapsed:.1f}s, completed: {len(all_trajectories)} trajectories)")
                last_log_time = current_time
            
            # 等待至少一个 worker 完成，最多等待 60 秒（减少超时以便更早发现问题）
            ready, remaining_futures = ray.wait(
                remaining_futures,
                num_returns=1,
                timeout=60.0,  # 减少到 60 秒超时
            )
            
            # 处理已完成的 worker
            for future in ready:
                try:
                    result = ray.get(future)
                    all_trajectories.extend(result)
                except Exception as e:
                    failed_workers += 1
                    print(f"Warning: Worker failed: {e}")
                    # 继续处理其他 worker，不中断整个收集过程
                    continue
        except Exception as e:
            # 处理 ray.wait 本身的异常
            print(f"Warning: Error waiting for workers: {e}")
            # 尝试获取剩余的所有结果
            for future in remaining_futures:
                try:
                    result = ray.get(future, timeout=60.0)
                    all_trajectories.extend(result)
                except Exception:
                    failed_workers += 1
                    continue
            break
    
    if failed_workers > 0:
        print(f"Warning: {failed_workers}/{len(futures)} workers failed during data collection")
    
    return all_trajectories

