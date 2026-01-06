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
        shanten_reward_weight: float = 0.05,  # 向听数奖励权重（用于初期训练）
        use_shanten_reward: bool = True,  # 是否使用向听数奖励（初期阶段启用）
        reward_config: Optional[Dict[str, float]] = None,  # 阶段特定的奖励配置
    ):
        """
        参数：
        - ready_reward: 听牌奖励（默认 0.1）
        - hu_reward: 胡牌奖励（默认 1.0）
        - flower_pig_penalty: 花猪惩罚（默认 -5.0）
        - final_score_weight: 最终得分权重（默认 1.0）
        - shanten_reward_weight: 向听数奖励权重（默认 0.05，用于初期训练）
        - use_shanten_reward: 是否使用向听数奖励（默认 True，初期阶段启用）
        - reward_config: 阶段特定的奖励配置（可选）
        """
        self.ready_reward = ready_reward
        self.hu_reward = hu_reward
        self.flower_pig_penalty = flower_pig_penalty
        self.final_score_weight = final_score_weight
        self.shanten_reward_weight = shanten_reward_weight
        self.use_shanten_reward = use_shanten_reward
        self.reward_config = reward_config or {}
    
    def compute_step_reward(
        self,
        is_ready: bool = False,
        is_hu: bool = False,
        is_flower_pig: bool = False,
        shanten: Optional[int] = None,
        previous_shanten: Optional[int] = None,
        lack_color_discard: bool = False,  # 是否打出缺门牌
        illegal_action_attempt: bool = False,  # 是否尝试非法动作
        point_loss: bool = False,  # 是否点炮
        safe_discard: bool = False,  # 是否安全弃牌（打熟张）
        pass_hu_success: bool = False,  # 是否过胡后胡了更大的番数
        call_transfer_loss: bool = False,  # 是否发生呼叫转移损失
    ) -> float:
        """
        计算单步奖励（引导奖惩）
        
        参数验证：
        - shanten 和 previous_shanten 应该在合理范围内（0-8）
        """
        # 参数验证
        if shanten is not None:
            if shanten < 0 or shanten > 8:
                raise ValueError(f"Invalid shanten value: {shanten}, expected 0-8")
        if previous_shanten is not None:
            if previous_shanten < 0 or previous_shanten > 8:
                raise ValueError(f"Invalid previous_shanten value: {previous_shanten}, expected 0-8")
        """
        计算单步奖励（引导奖惩）
        
        参数：
        - is_ready: 是否听牌
        - is_hu: 是否胡牌
        - is_flower_pig: 是否成为花猪
        - shanten: 当前向听数（可选，用于初期训练）
        - previous_shanten: 上一步的向听数（可选，用于计算向听数改善）
        - lack_color_discard: 是否打出缺门牌
        - illegal_action_attempt: 是否尝试非法动作
        - point_loss: 是否点炮
        - safe_discard: 是否安全弃牌（打熟张）
        - pass_hu_success: 是否过胡后胡了更大的番数
        - call_transfer_loss: 是否发生呼叫转移损失
        
        返回：
        - 即时奖励
        """
        reward = 0.0
        
        # 如果使用阶段特定的奖励配置
        if self.reward_config.get('raw_score_only', False):
            # 阶段6：纯金币收益，不添加任何人工奖励
            return 0.0
        
        # 定缺相关奖励（阶段1）
        if lack_color_discard:
            reward += self.reward_config.get('lack_color_discard', 0.0)
        
        if illegal_action_attempt:
            reward += self.reward_config.get('illegal_action_attempt', 0.0)
        
        # 向听数奖励（阶段2-4，逐步衰减）
        shanten_weight = self.reward_config.get('shanten_reward', self.shanten_reward_weight if self.use_shanten_reward else 0.0)
        if shanten_weight > 0 and shanten is not None and previous_shanten is not None:
            if shanten < previous_shanten:
                # 向听数减少（进张）
                shanten_improvement = previous_shanten - shanten
                reward += shanten_improvement * self.reward_config.get('shanten_decrease', 2.0)
            elif shanten > previous_shanten:
                # 向听数增加（拆搭子）
                shanten_degradation = shanten - previous_shanten
                reward += shanten_degradation * self.reward_config.get('shanten_increase', -1.5)
            elif shanten == 0:
                # 已听牌（一次性重奖）
                reward += self.reward_config.get('ready_hand', self.ready_reward)
        
        # 听牌奖励（如果未在向听数奖励中处理）
        if is_ready and shanten_weight == 0:
            reward += self.reward_config.get('ready_reward', self.ready_reward)
        
        # 胡牌奖励（阶段3+）
        if is_hu:
            reward += self.reward_config.get('base_win', self.hu_reward)
        
        # 花猪惩罚
        if is_flower_pig:
            reward += self.reward_config.get('flower_pig_penalty', self.flower_pig_penalty)
        
        # 点炮惩罚（阶段4+）
        if point_loss:
            reward += self.reward_config.get('point_loss', 0.0)
        
        # 安全弃牌奖励（阶段4+）
        if safe_discard:
            reward += self.reward_config.get('safe_discard_bonus', 0.0)
        
        # 过胡成功奖励（阶段5+）
        if pass_hu_success:
            reward += self.reward_config.get('pass_hu_success', 0.0)
        
        # 呼叫转移损失（阶段5+）
        if call_transfer_loss:
            reward += self.reward_config.get('call_transfer_loss', 0.0)
        
        return reward
    
    def compute_final_reward(
        self,
        final_score: float,
        is_winner: bool = False,
        fan_count: int = 0,  # 番数
        gen_count: int = 0,  # 根数
        shouting_penalty: float = 0.0,  # 查大叫罚分
    ) -> float:
        """
        计算最终奖励（局末真实得分）
        
        参数：
        - final_score: 最终得分（金币/积分）
        - is_winner: 是否获胜
        - fan_count: 番数（用于阶段3+的番数倍数奖励）
        - gen_count: 根数（用于阶段3+的根奖励）
        - shouting_penalty: 查大叫罚分
        
        返回：
        - 最终奖励
        """
        reward = 0.0
        
        # 如果使用阶段特定的奖励配置
        if self.reward_config.get('raw_score_only', False):
            # 阶段6：纯金币收益
            return self.final_score_weight * final_score
        
        # 基础得分
        reward += self.final_score_weight * final_score
        
        # 番数倍数奖励（阶段3+）
        fan_multiplier = self.reward_config.get('fan_multiplier', 0.0)
        if fan_multiplier > 0 and fan_count > 0:
            reward += final_score * (fan_multiplier - 1.0)  # 额外奖励 = (倍数 - 1) * 得分
        
        # 根奖励（阶段3+）
        gen_reward = self.reward_config.get('gen_reward', 0.0)
        if gen_reward > 0:
            reward += gen_count * gen_reward
        
        # 查大叫和查花猪罚分（阶段3+）
        if shouting_penalty < 0:
            reward += self.reward_config.get('shouting_penalty', 0.0) * abs(shouting_penalty) / 10.0
        
        return reward
    
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

