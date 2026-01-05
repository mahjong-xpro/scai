"""
奖励函数初调 (Reward Shaping)

实现引导奖惩和最终奖励计算。
"""

from typing import Dict, Optional
import numpy as np


class RewardShaping:
    """奖励函数初调
    
    实现引导奖惩和最终奖励计算，帮助 AI 在训练初期学习基本策略。
    """
    
    def __init__(
        self,
        ready_reward: float = 0.1,
        hu_reward: float = 1.0,
        flower_pig_penalty: float = -5.0,
        final_score_weight: float = 1.0,
    ):
        """
        参数：
        - ready_reward: 听牌奖励（默认 0.1）
        - hu_reward: 胡牌奖励（默认 1.0）
        - flower_pig_penalty: 花猪惩罚（默认 -5.0）
        - final_score_weight: 最终得分权重（默认 1.0）
        """
        self.ready_reward = ready_reward
        self.hu_reward = hu_reward
        self.flower_pig_penalty = flower_pig_penalty
        self.final_score_weight = final_score_weight
    
    def compute_step_reward(
        self,
        is_ready: bool = False,
        is_hu: bool = False,
        is_flower_pig: bool = False,
    ) -> float:
        """
        计算单步奖励（引导奖惩）
        
        参数：
        - is_ready: 是否听牌
        - is_hu: 是否胡牌
        - is_flower_pig: 是否成为花猪
        
        返回：
        - 即时奖励
        """
        reward = 0.0
        
        # 听牌奖励
        if is_ready:
            reward += self.ready_reward
        
        # 胡牌奖励
        if is_hu:
            reward += self.hu_reward
        
        # 花猪惩罚
        if is_flower_pig:
            reward += self.flower_pig_penalty
        
        return reward
    
    def compute_final_reward(
        self,
        final_score: float,
        is_winner: bool = False,
    ) -> float:
        """
        计算最终奖励（局末真实得分）
        
        参数：
        - final_score: 最终得分（金币/积分）
        - is_winner: 是否获胜
        
        返回：
        - 最终奖励
        """
        # 以局末真实得分为唯一最终指标
        return self.final_score_weight * final_score
    
    def compute_total_reward(
        self,
        step_rewards: list,
        final_score: float,
        is_winner: bool = False,
    ) -> float:
        """
        计算总奖励（引导奖惩 + 最终奖励）
        
        参数：
        - step_rewards: 单步奖励列表
        - final_score: 最终得分
        - is_winner: 是否获胜
        
        返回：
        - 总奖励
        """
        # 单步奖励总和
        step_total = sum(step_rewards)
        
        # 最终奖励
        final_reward = self.compute_final_reward(final_score, is_winner)
        
        return step_total + final_reward
    
    def update_rewards(
        self,
        rewards: list,
        final_score: float,
        is_winner: bool = False,
    ) -> list:
        """
        更新奖励列表，将最终奖励添加到最后一个时间步
        
        参数：
        - rewards: 奖励列表
        - final_score: 最终得分
        - is_winner: 是否获胜
        
        返回：
        - 更新后的奖励列表
        """
        if len(rewards) == 0:
            return rewards
        
        # 计算最终奖励
        final_reward = self.compute_final_reward(final_score, is_winner)
        
        # 将最终奖励添加到最后一个时间步
        updated_rewards = rewards.copy()
        updated_rewards[-1] += final_reward
        
        return updated_rewards

