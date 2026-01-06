"""
对抗性鲁棒训练 (Adversarial Robust Training)

针对性模拟极端局势，提升防御避炮能力。
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import random

from .reward_shaping import RewardShaping
from ..models import DualResNet


class AdversarialTrainer:
    """对抗性鲁棒训练器
    
    针对性模拟极端局势，提升模型的防御避炮能力。
    """
    
    def __init__(
        self,
        reward_shaping: RewardShaping,
        targeted_declare_prob: float = 0.3,
        bad_hand_prob: float = 0.2,
    ):
        """
        参数：
        - reward_shaping: 奖励函数初调实例
        - targeted_declare_prob: 被三家定缺针对的概率（默认 0.3）
        - bad_hand_prob: 起手极烂的概率（默认 0.2）
        """
        self.reward_shaping = reward_shaping
        self.targeted_declare_prob = targeted_declare_prob
        self.bad_hand_prob = bad_hand_prob
    
    def create_targeted_declare_scenario(
        self,
        game_state,
        target_player_id: int,
    ) -> Dict:
        """
        创建被三家定缺针对的极端局势
        
        参数：
        - game_state: 游戏状态
        - target_player_id: 被针对的玩家 ID
        
        返回：
        - 包含场景配置的字典
        """
        # 获取目标玩家的手牌
        target_hand = game_state.get_player_hand(target_player_id)
        
        # 分析手牌中最多的花色
        suit_counts = {'Wan': 0, 'Tong': 0, 'Tiao': 0}
        for tile_str, count in target_hand.items():
            if 'Wan' in tile_str:
                suit_counts['Wan'] += count
            elif 'Tong' in tile_str:
                suit_counts['Tong'] += count
            elif 'Tiao' in tile_str:
                suit_counts['Tiao'] += count
        
        # 找到最多的花色
        most_suit = max(suit_counts.items(), key=lambda x: x[1])[0]
        
        # 让其他三家都定缺这个花色
        scenario = {
            'type': 'targeted_declare',
            'target_player_id': target_player_id,
            'declared_suits': {
                0: most_suit if 0 != target_player_id else None,
                1: most_suit if 1 != target_player_id else None,
                2: most_suit if 2 != target_player_id else None,
                3: most_suit if 3 != target_player_id else None,
            },
        }
        
        return scenario
    
    def create_bad_hand_scenario(
        self,
        game_state,
        target_player_id: int,
    ) -> Dict:
        """
        创建起手极烂的极端局势
        
        参数：
        - game_state: 游戏状态
        - target_player_id: 目标玩家 ID
        
        返回：
        - 包含场景配置的字典
        """
        # 创建极烂的手牌（分散、无对子、无顺子）
        scenario = {
            'type': 'bad_hand',
            'target_player_id': target_player_id,
            'description': '起手极烂：牌型分散，无对子，无顺子',
        }
        
        return scenario
    
    def should_apply_adversarial_scenario(self) -> Tuple[bool, str]:
        """
        判断是否应用对抗性场景
        
        返回：
        - (是否应用, 场景类型)
        """
        rand = random.random()
        
        if rand < self.targeted_declare_prob:
            return True, 'targeted_declare'
        elif rand < self.targeted_declare_prob + self.bad_hand_prob:
            return True, 'bad_hand'
        else:
            return False, 'normal'
    
    def apply_scenario(
        self,
        game_state,
        scenario: Dict,
    ):
        """
        应用对抗性场景到游戏状态
        
        参数：
        - game_state: 游戏状态
        - scenario: 场景配置
        """
        if scenario['type'] == 'targeted_declare':
            # 设置其他玩家的定缺
            for player_id, declared_suit in scenario['declared_suits'].items():
                if declared_suit is not None:
                    # 在游戏状态中设置定缺
                    if hasattr(game_state, 'set_player_declared_suit'):
                        try:
                            game_state.set_player_declared_suit(player_id, declared_suit)
                        except Exception as e:
                            print(f"Warning: Failed to set declared suit for player {player_id}: {e}")
        
        elif scenario['type'] == 'bad_hand':
            # 修改目标玩家的手牌为极烂手牌
            target_player_id = scenario['target_player_id']
            
            if hasattr(game_state, 'set_player_hand'):
                try:
                    # 创建极烂手牌（分散、无对子、无顺子）
                    # 策略：选择不同花色、不同数字的单张牌，避免形成对子或顺子
                    bad_hand = self._generate_bad_hand()
                    
                    # 转换为字典格式（键为牌字符串，值为数量）
                    hand_dict = {}
                    for tile_str, count in bad_hand.items():
                        hand_dict[tile_str] = count
                    
                    game_state.set_player_hand(target_player_id, hand_dict)
                except Exception as e:
                    print(f"Warning: Failed to set bad hand for player {target_player_id}: {e}")
    
    def _generate_bad_hand(self) -> Dict[str, int]:
        """
        生成极烂手牌（分散、无对子、无顺子）
        
        返回：
        - 手牌字典，键为牌字符串，值为数量
        """
        # 策略：选择不同花色、不同数字的单张牌
        # 避免形成对子（相同牌）或顺子（连续数字）
        
        # 生成13张牌（标准起手牌数）
        bad_tiles = []
        
        # 使用分散策略：选择间隔较大的牌，避免形成顺子
        # 例如：1万、4万、7万、2筒、5筒、8筒、3条、6条、9条等
        
        suits = ['Wan', 'Tong', 'Tiao']
        ranks = [1, 4, 7, 2, 5, 8, 3, 6, 9]  # 间隔较大的数字
        
        suit_idx = 0
        rank_idx = 0
        
        for _ in range(13):
            suit = suits[suit_idx % len(suits)]
            rank = ranks[rank_idx % len(ranks)]
            
            tile_str = f"{suit}({rank})"
            bad_tiles.append(tile_str)
            
            suit_idx += 1
            rank_idx += 1
        
        # 转换为字典（统计每张牌的数量）
        hand_dict = {}
        for tile_str in bad_tiles:
            hand_dict[tile_str] = hand_dict.get(tile_str, 0) + 1
        
        return hand_dict
    
    def compute_defense_reward(
        self,
        is_discard_safe: bool,
        avoided_pao: bool,
        is_ready: bool,
    ) -> float:
        """
        计算防御奖励
        
        参数：
        - is_discard_safe: 出牌是否安全（不点炮）
        - avoided_pao: 是否避免了点炮
        - is_ready: 是否听牌
        
        返回：
        - 防御奖励
        """
        reward = 0.0
        
        # 安全出牌奖励
        if is_discard_safe:
            reward += 0.05
        
        # 避免点炮奖励
        if avoided_pao:
            reward += 0.2
        
        # 听牌时的安全出牌额外奖励
        if is_ready and is_discard_safe:
            reward += 0.1
        
        return reward
    
    def train_with_adversarial_scenarios(
        self,
        game_state,
        player_id: int,
        num_episodes: int = 100,
    ) -> Dict:
        """
        使用对抗性场景进行训练
        
        参数：
        - game_state: 游戏状态
        - player_id: 玩家 ID
        - num_episodes: 训练轮数
        
        返回：
        - 训练统计信息
        """
        stats = {
            'targeted_declare_count': 0,
            'bad_hand_count': 0,
            'normal_count': 0,
            'defense_rewards': [],
        }
        
        for episode in range(num_episodes):
            # 判断是否应用对抗性场景
            apply_scenario, scenario_type = self.should_apply_adversarial_scenario()
            
            if apply_scenario:
                if scenario_type == 'targeted_declare':
                    scenario = self.create_targeted_declare_scenario(game_state, player_id)
                    stats['targeted_declare_count'] += 1
                elif scenario_type == 'bad_hand':
                    scenario = self.create_bad_hand_scenario(game_state, player_id)
                    stats['bad_hand_count'] += 1
                
                # 应用场景
                self.apply_scenario(game_state, scenario)
            else:
                stats['normal_count'] += 1
        
        return stats

