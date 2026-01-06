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
from ..selfplay.opponent_pool import OpponentPool

# 导入 Rust 游戏引擎绑定
try:
    import scai_engine
    HAS_SCAI_ENGINE = True
except ImportError:
    HAS_SCAI_ENGINE = False
    print("Warning: scai_engine module not found. Evaluation will use placeholder data.")


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
        opponent_pool: Optional[OpponentPool] = None,
    ):
        """
        参数：
        - checkpoint_dir: Checkpoint 目录
        - elo_threshold: Elo 胜率阈值（默认 0.55，即 55%）
        - device: 设备（'cpu' 或 'cuda'）
        - opponent_pool: 对手池（可选）
        """
        self.checkpoint_dir = checkpoint_dir
        self.elo_threshold = elo_threshold
        self.device = device
        
        # Elo 评分系统
        self.elo = EloRating()
        
        # Checkpoint 管理器
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        
        # 对手池（可选）
        self.opponent_pool = opponent_pool
        self.use_opponent_pool = opponent_pool is not None
        
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
        
        if not HAS_SCAI_ENGINE:
            # 如果没有游戏引擎，返回占位符数据
            wins = int(num_games * 0.5)  # 假设 50% 胜率
            total_score = 0.0
            return {
                'win_rate': 0.5,
                'avg_score': 0.0,
                'wins': wins,
                'total_games': num_games,
            }
        
        # 实现实际的对弈逻辑
        wins = 0
        total_score = 0.0
        
        for game_id in range(num_games):
            try:
                # 运行一局游戏
                game_result = self._play_game_with_model(model, model_id, game_id)
                
                # 检查是否获胜（得分 > 0 表示获胜）
                if game_result['final_score'] > 0:
                    wins += 1
                total_score += game_result['final_score']
            except Exception as e:
                print(f"Error in evaluation game {game_id}: {e}")
                # 如果游戏失败，跳过
                continue
        
        win_rate = wins / num_games if num_games > 0 else 0.0
        avg_score = total_score / num_games if num_games > 0 else 0.0
        
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
        
        if not HAS_SCAI_ENGINE:
            # 如果没有游戏引擎，返回占位符数据
            wins_a = int(num_games * 0.5)
            total_score_a = 0.0
            total_score_b = 0.0
            win_rate_a = 0.5
        else:
            # 实现实际的对弈逻辑
            wins_a = 0
            total_score_a = 0.0
            total_score_b = 0.0
            
            for game_id in range(num_games):
                try:
                    # 运行一局游戏（两个模型对弈）
                    game_result = self._play_game_with_two_models(
                        model_a, model_b, model_a_id, model_b_id, game_id
                    )
                    
                    # 检查模型 A 是否获胜
                    if game_result['model_a_score'] > game_result['model_b_score']:
                        wins_a += 1
                    
                    total_score_a += game_result['model_a_score']
                    total_score_b += game_result['model_b_score']
                except Exception as e:
                    print(f"Error in comparison game {game_id}: {e}")
                    # 如果游戏失败，跳过
                    continue
            
            win_rate_a = wins_a / num_games if num_games > 0 else 0.0
        
        # 更新 Elo 评分
        actual_score = 1.0 if win_rate_a >= 0.5 else 0.0
        self.elo.update_rating(model_a_id, model_b_id, actual_score)
        self.elo.update_rating(model_b_id, model_a_id, 1.0 - actual_score)
        
        return {
            'model_a_win_rate': win_rate_a,
            'model_b_win_rate': 1.0 - win_rate_a,
            'model_a_avg_score': total_score_a / num_games if num_games > 0 else 0.0,
            'model_b_avg_score': total_score_b / num_games if num_games > 0 else 0.0,
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
    
    def _play_game_with_model(
        self,
        model: DualResNet,
        model_id: str,
        game_id: int,
    ) -> Dict[str, float]:
        """
        使用单个模型运行一局游戏（与其他随机玩家或固定策略玩家对弈）
        
        参数：
        - model: 要评估的模型
        - model_id: 模型 ID
        - game_id: 游戏 ID
        
        返回：
        - 包含游戏结果的字典
        """
        # 初始化游戏引擎
        engine = scai_engine.PyGameEngine()
        engine.initialize()
        
        # 定缺阶段
        for player_id in range(4):
            state = engine.state
            if state.get_player_declared_suit(player_id) is not None:
                continue
            
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
            
            min_suit = min(suit_counts.items(), key=lambda x: x[1])[0]
            try:
                engine.declare_suit(player_id, min_suit)
            except Exception:
                engine.declare_suit(player_id, 'Wan')
        
        # 游戏主循环
        max_turns = 200
        turn_count = 0
        final_scores = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
        
        while not engine.is_game_over() and turn_count < max_turns:
            turn_count += 1
            
            state = engine.state
            current_player = state.current_player
            
            if state.is_player_out(current_player):
                continue
            
            # 摸牌
            try:
                draw_result = engine.process_action(current_player, "draw", None, None)
                if isinstance(draw_result, dict) and draw_result.get('type') == 'error':
                    break
            except Exception:
                break
            
            # 获取状态张量和动作掩码
            remaining_tiles = engine.remaining_tiles()
            state_tensor = scai_engine.state_to_tensor(
                state,
                player_id=current_player,
                remaining_tiles=remaining_tiles,
                use_oracle=False,
                wall_tile_distribution=None,
            )
            
            action_mask = scai_engine.PyActionMask.get_action_mask(
                current_player,
                state,
                is_own_turn=True,
                discarded_tile=None,
            )
            
            # 模型推理（仅对玩家 0 使用模型，其他玩家使用随机策略）
            if current_player == 0:
                state_tensor_torch = torch.from_numpy(state_tensor).float().unsqueeze(0).to(self.device)
                action_mask_torch = torch.from_numpy(np.array(action_mask, dtype=np.float32)).float().unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    policy, _ = model(state_tensor_torch, action_mask_torch)
                
                policy_np = policy.cpu().numpy()[0]
                action_mask_np = action_mask_torch.cpu().numpy()[0]
                
                masked_policy = policy_np * action_mask_np
                masked_policy_sum = masked_policy.sum()
                if masked_policy_sum > 1e-8:
                    masked_policy = masked_policy / masked_policy_sum
                else:
                    masked_policy = action_mask_np / (action_mask_np.sum() + 1e-8)
                
                action_index = np.random.choice(len(masked_policy), p=masked_policy)
            else:
                # 其他玩家使用随机策略
                legal_actions = [i for i in range(len(action_mask)) if action_mask[i] > 0.5]
                if legal_actions:
                    action_index = np.random.choice(legal_actions)
                else:
                    action_index = 0
            
            # 转换动作索引为动作参数
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
                
                if isinstance(result, dict) and result.get('type') == 'won':
                    # 游戏结束，记录得分
                    winner_id = result.get('player_id', current_player)
                    settlement_str = result.get('settlement', '')
                    final_score = self._extract_final_score_from_settlement(
                        settlement_str, winner_id
                    )
                    final_scores[winner_id] = final_score
                    break
            except Exception:
                continue
        
        # 返回玩家 0 的最终得分
        return {
            'final_score': final_scores[0],
        }
    
    def _play_game_with_two_models(
        self,
        model_a: DualResNet,
        model_b: DualResNet,
        model_a_id: str,
        model_b_id: str,
        game_id: int,
    ) -> Dict[str, float]:
        """
        使用两个模型运行一局游戏（模型 A 和模型 B 对弈）
        
        参数：
        - model_a: 模型 A
        - model_b: 模型 B
        - model_a_id: 模型 A 的 ID
        - model_b_id: 模型 B 的 ID
        - game_id: 游戏 ID
        
        返回：
        - 包含两个模型得分的字典
        """
        # 初始化游戏引擎
        engine = scai_engine.PyGameEngine()
        engine.initialize()
        
        # 定缺阶段
        for player_id in range(4):
            state = engine.state
            if state.get_player_declared_suit(player_id) is not None:
                continue
            
            hand = state.get_player_hand(player_id)
            suit_counts = {'Wan': 0, 'Tong': 0, 'Tiao': 0}
            for tile_str, count in hand.items():
                if 'Wan' in tile_str:
                    suit_counts['Wan'] += count
                elif 'Tong' in tile_str:
                    suit_counts['Tong'] += count
                elif 'Tiao' in tile_str:
                    suit_counts['Tiao'] += count
            
            min_suit = min(suit_counts.items(), key=lambda x: x[1])[0]
            try:
                engine.declare_suit(player_id, min_suit)
            except Exception:
                engine.declare_suit(player_id, 'Wan')
        
        # 游戏主循环
        max_turns = 200
        turn_count = 0
        final_scores = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
        
        # 分配模型：玩家 0 和 2 使用模型 A，玩家 1 和 3 使用模型 B
        model_assignment = {0: model_a, 1: model_b, 2: model_a, 3: model_b}
        
        while not engine.is_game_over() and turn_count < max_turns:
            turn_count += 1
            
            state = engine.state
            current_player = state.current_player
            
            if state.is_player_out(current_player):
                continue
            
            # 摸牌
            try:
                draw_result = engine.process_action(current_player, "draw", None, None)
                if isinstance(draw_result, dict) and draw_result.get('type') == 'error':
                    break
            except Exception:
                break
            
            # 获取状态张量和动作掩码
            remaining_tiles = engine.remaining_tiles()
            state_tensor = scai_engine.state_to_tensor(
                state,
                player_id=current_player,
                remaining_tiles=remaining_tiles,
                use_oracle=False,
                wall_tile_distribution=None,
            )
            
            action_mask = scai_engine.PyActionMask.get_action_mask(
                current_player,
                state,
                is_own_turn=True,
                discarded_tile=None,
            )
            
            # 使用对应的模型进行推理
            current_model = model_assignment.get(current_player, model_a)
            state_tensor_torch = torch.from_numpy(state_tensor).float().unsqueeze(0).to(self.device)
            action_mask_torch = torch.from_numpy(np.array(action_mask, dtype=np.float32)).float().unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                policy, _ = current_model(state_tensor_torch, action_mask_torch)
            
            policy_np = policy.cpu().numpy()[0]
            action_mask_np = action_mask_torch.cpu().numpy()[0]
            
            masked_policy = policy_np * action_mask_np
            masked_policy_sum = masked_policy.sum()
            if masked_policy_sum > 1e-8:
                masked_policy = masked_policy / masked_policy_sum
            else:
                masked_policy = action_mask_np / (action_mask_np.sum() + 1e-8)
            
            action_index = np.random.choice(len(masked_policy), p=masked_policy)
            
            # 转换动作索引为动作参数
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
                
                if isinstance(result, dict) and result.get('type') == 'won':
                    # 游戏结束，记录得分
                    winner_id = result.get('player_id', current_player)
                    settlement_str = result.get('settlement', '')
                    final_score = self._extract_final_score_from_settlement(
                        settlement_str, winner_id
                    )
                    final_scores[winner_id] = final_score
                    break
            except Exception:
                continue
        
        # 计算模型 A 和模型 B 的总得分
        model_a_score = final_scores[0] + final_scores[2]
        model_b_score = final_scores[1] + final_scores[3]
        
        return {
            'model_a_score': model_a_score,
            'model_b_score': model_b_score,
        }
    
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
        if action_index < 108:
            return "discard", action_index, None
        elif action_index < 216:
            tile_index = action_index - 108
            return "pong", tile_index, None
        elif action_index < 324:
            tile_index = action_index - 216
            return "gang", tile_index, False
        elif action_index < 432:
            return "win", None, None
        elif action_index == 432:
            return "pass", None, None
        else:
            return "draw", None, None
    
    def _extract_final_score_from_settlement(
        self,
        settlement_str: str,
        player_id: int,
    ) -> float:
        """
        从结算结果字符串中提取最终得分
        
        参数：
        - settlement_str: 结算结果字符串
        - player_id: 玩家 ID
        
        返回：
        - 最终得分
        """
        try:
            import re
            pattern = rf'{player_id}:\s*([+-]?\d+)'
            match = re.search(pattern, settlement_str)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        
        return 0.0

