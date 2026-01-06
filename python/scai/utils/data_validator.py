"""
数据验证器 (Data Validator)

验证轨迹数据的完整性和正确性，确保训练数据的质量。
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings


class DataValidator:
    """数据验证器
    
    验证轨迹数据的完整性和正确性。
    """
    
    def __init__(
        self,
        state_shape: Tuple[int, ...] = (64, 4, 9),
        action_space_size: int = 434,
        strict_mode: bool = True,
    ):
        """
        参数：
        - state_shape: 状态张量的形状（默认 (64, 4, 9)）
        - action_space_size: 动作空间大小（默认 434）
        - strict_mode: 严格模式（默认 True，发现错误时抛出异常）
        """
        self.state_shape = state_shape
        self.action_space_size = action_space_size
        self.strict_mode = strict_mode
        
        # 验证统计
        self.validation_stats = {
            'total_trajectories': 0,
            'valid_trajectories': 0,
            'invalid_trajectories': 0,
            'warnings': [],
            'errors': [],
        }
    
    def validate_trajectory(
        self,
        trajectory: Dict,
        trajectory_id: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        验证单个轨迹
        
        参数：
        - trajectory: 轨迹字典，包含 states, actions, rewards, values, log_probs, dones, action_masks
        - trajectory_id: 轨迹 ID（可选，用于错误报告）
        
        返回：
        - (is_valid, errors): 是否有效，错误列表
        """
        errors = []
        warnings_list = []
        
        # 检查必需字段
        required_fields = ['states', 'actions', 'rewards', 'values', 'log_probs', 'dones']
        for field in required_fields:
            if field not in trajectory:
                errors.append(f"Missing required field: {field}")
                if self.strict_mode:
                    raise ValueError(f"Trajectory {trajectory_id}: Missing required field: {field}")
        
        if errors:
            return False, errors
        
        # 获取轨迹长度
        trajectory_length = len(trajectory['states'])
        
        # 验证长度一致性
        for field in required_fields:
            if len(trajectory[field]) != trajectory_length:
                error_msg = f"Length mismatch: {field} has {len(trajectory[field])} elements, expected {trajectory_length}"
                errors.append(error_msg)
                if self.strict_mode:
                    raise ValueError(f"Trajectory {trajectory_id}: {error_msg}")
        
        # 验证每个时间步
        for step in range(trajectory_length):
            step_errors = self._validate_step(
                trajectory,
                step,
                trajectory_id,
            )
            errors.extend(step_errors)
        
        # 验证轨迹完整性
        trajectory_errors = self._validate_trajectory_integrity(trajectory, trajectory_id)
        errors.extend(trajectory_errors)
        
        # 更新统计
        self.validation_stats['total_trajectories'] += 1
        if errors:
            self.validation_stats['invalid_trajectories'] += 1
            self.validation_stats['errors'].extend(errors)
        else:
            self.validation_stats['valid_trajectories'] += 1
        
        if warnings_list:
            self.validation_stats['warnings'].extend(warnings_list)
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _validate_step(
        self,
        trajectory: Dict,
        step: int,
        trajectory_id: Optional[str] = None,
    ) -> List[str]:
        """验证单个时间步"""
        errors = []
        
        # 验证状态
        state = trajectory['states'][step]
        state_errors = self._validate_state(state, step, trajectory_id)
        errors.extend(state_errors)
        
        # 验证动作
        action = trajectory['actions'][step]
        action_errors = self._validate_action(action, step, trajectory_id)
        errors.extend(action_errors)
        
        # 验证奖励
        reward = trajectory['rewards'][step]
        reward_errors = self._validate_reward(reward, step, trajectory_id)
        errors.extend(reward_errors)
        
        # 验证价值
        value = trajectory['values'][step]
        value_errors = self._validate_value(value, step, trajectory_id)
        errors.extend(value_errors)
        
        # 验证对数概率
        log_prob = trajectory['log_probs'][step]
        log_prob_errors = self._validate_log_prob(log_prob, step, trajectory_id)
        errors.extend(log_prob_errors)
        
        # 验证动作掩码（如果存在）
        if 'action_masks' in trajectory and len(trajectory['action_masks']) > step:
            action_mask = trajectory['action_masks'][step]
            mask_errors = self._validate_action_mask(
                action_mask,
                action,
                step,
                trajectory_id,
            )
            errors.extend(mask_errors)
        
        return errors
    
    def _validate_state(
        self,
        state: np.ndarray,
        step: int,
        trajectory_id: Optional[str] = None,
    ) -> List[str]:
        """验证状态"""
        errors = []
        
        # 检查类型
        if not isinstance(state, np.ndarray):
            errors.append(f"Step {step}: State is not a numpy array")
            return errors
        
        # 检查形状
        if state.shape != self.state_shape:
            error_msg = f"Step {step}: State shape {state.shape} != expected {self.state_shape}"
            errors.append(error_msg)
            if self.strict_mode:
                raise ValueError(f"Trajectory {trajectory_id}: {error_msg}")
        
        # 检查 NaN 和 Inf
        if np.any(np.isnan(state)):
            errors.append(f"Step {step}: State contains NaN values")
        if np.any(np.isinf(state)):
            errors.append(f"Step {step}: State contains Inf values")
        
        # 检查数值范围（状态应该是归一化的，通常在 [0, 1] 或 [-1, 1]）
        if np.any(state < -10) or np.any(state > 10):
            warnings.warn(f"Step {step}: State values out of expected range [-10, 10]")
        
        return errors
    
    def _validate_action(
        self,
        action: int,
        step: int,
        trajectory_id: Optional[str] = None,
    ) -> List[str]:
        """验证动作"""
        errors = []
        
        # 检查类型
        if not isinstance(action, (int, np.integer)):
            errors.append(f"Step {step}: Action is not an integer")
            return errors
        
        # 检查范围
        if action < 0 or action >= self.action_space_size:
            error_msg = f"Step {step}: Action {action} out of range [0, {self.action_space_size})"
            errors.append(error_msg)
            if self.strict_mode:
                raise ValueError(f"Trajectory {trajectory_id}: {error_msg}")
        
        return errors
    
    def _validate_reward(
        self,
        reward: float,
        step: int,
        trajectory_id: Optional[str] = None,
    ) -> List[str]:
        """验证奖励"""
        errors = []
        
        # 检查类型
        if not isinstance(reward, (int, float, np.floating, np.integer)):
            errors.append(f"Step {step}: Reward is not a number")
            return errors
        
        # 检查 NaN 和 Inf
        if np.isnan(reward):
            errors.append(f"Step {step}: Reward is NaN")
        if np.isinf(reward):
            errors.append(f"Step {step}: Reward is Inf")
        
        # 检查范围（奖励通常在合理范围内，例如 [-100, 100]）
        if abs(reward) > 1000:
            warnings.warn(f"Step {step}: Reward {reward} is unusually large")
        
        return errors
    
    def _validate_value(
        self,
        value: float,
        step: int,
        trajectory_id: Optional[str] = None,
    ) -> List[str]:
        """验证价值估计"""
        errors = []
        
        # 检查类型
        if not isinstance(value, (int, float, np.floating, np.integer)):
            errors.append(f"Step {step}: Value is not a number")
            return errors
        
        # 检查 NaN 和 Inf
        if np.isnan(value):
            errors.append(f"Step {step}: Value is NaN")
        if np.isinf(value):
            errors.append(f"Step {step}: Value is Inf")
        
        return errors
    
    def _validate_log_prob(
        self,
        log_prob: float,
        step: int,
        trajectory_id: Optional[str] = None,
    ) -> List[str]:
        """验证对数概率"""
        errors = []
        
        # 检查类型
        if not isinstance(log_prob, (int, float, np.floating, np.integer)):
            errors.append(f"Step {step}: Log prob is not a number")
            return errors
        
        # 检查 NaN 和 Inf
        if np.isnan(log_prob):
            errors.append(f"Step {step}: Log prob is NaN")
        if np.isinf(log_prob):
            # 对数概率可能是 -inf（对于概率为 0 的动作），这是允许的
            if log_prob > 0:
                errors.append(f"Step {step}: Log prob is +Inf (should be <= 0)")
        
        # 检查范围（对数概率应该 <= 0）
        if log_prob > 0:
            warnings.warn(f"Step {step}: Log prob {log_prob} is positive (should be <= 0)")
        
        return errors
    
    def _validate_action_mask(
        self,
        action_mask: np.ndarray,
        action: int,
        step: int,
        trajectory_id: Optional[str] = None,
    ) -> List[str]:
        """验证动作掩码"""
        errors = []
        
        # 检查类型
        if not isinstance(action_mask, np.ndarray):
            errors.append(f"Step {step}: Action mask is not a numpy array")
            return errors
        
        # 检查形状
        if action_mask.shape != (self.action_space_size,):
            error_msg = f"Step {step}: Action mask shape {action_mask.shape} != expected ({self.action_space_size},)"
            errors.append(error_msg)
            if self.strict_mode:
                raise ValueError(f"Trajectory {trajectory_id}: {error_msg}")
        
        # 检查值（应该是 0 或 1）
        if np.any((action_mask != 0) & (action_mask != 1)):
            warnings.warn(f"Step {step}: Action mask contains values other than 0 and 1")
        
        # 检查动作是否在掩码中允许
        if action_mask[action] < 0.5:
            error_msg = f"Step {step}: Action {action} is not allowed by action mask (mask[{action}] = {action_mask[action]})"
            errors.append(error_msg)
            if self.strict_mode:
                raise ValueError(f"Trajectory {trajectory_id}: {error_msg}")
        
        return errors
    
    def _validate_trajectory_integrity(
        self,
        trajectory: Dict,
        trajectory_id: Optional[str] = None,
    ) -> List[str]:
        """验证轨迹完整性"""
        errors = []
        
        # 检查轨迹长度
        trajectory_length = len(trajectory['states'])
        if trajectory_length == 0:
            errors.append("Trajectory is empty")
            return errors
        
        # 检查 done 标志
        dones = trajectory['dones']
        if not any(dones):
            warnings.warn(f"Trajectory {trajectory_id}: No done flag is True (trajectory may be incomplete)")
        
        # 检查最后一个时间步是否有 done 标志
        if not dones[-1]:
            warnings.warn(f"Trajectory {trajectory_id}: Last step is not marked as done")
        
        # 检查奖励序列的合理性
        rewards = trajectory['rewards']
        if all(r == 0 for r in rewards):
            warnings.warn(f"Trajectory {trajectory_id}: All rewards are zero")
        
        # 检查价值估计的合理性（应该与奖励相关）
        values = trajectory['values']
        if len(values) > 1:
            # 价值估计应该大致单调递减（因为折扣因子）
            # 但这不是严格的要求，只是警告
            pass
        
        return errors
    
    def validate_batch(
        self,
        trajectories: List[Dict],
    ) -> Tuple[List[bool], List[List[str]]]:
        """
        验证一批轨迹
        
        参数：
        - trajectories: 轨迹列表
        
        返回：
        - (valid_flags, error_lists): 每个轨迹的有效性标志和错误列表
        """
        valid_flags = []
        error_lists = []
        
        for i, trajectory in enumerate(trajectories):
            is_valid, errors = self.validate_trajectory(trajectory, trajectory_id=f"trajectory_{i}")
            valid_flags.append(is_valid)
            error_lists.append(errors)
        
        return valid_flags, error_lists
    
    def get_validation_stats(self) -> Dict:
        """获取验证统计信息"""
        return {
            **self.validation_stats,
            'valid_rate': (
                self.validation_stats['valid_trajectories'] / self.validation_stats['total_trajectories']
                if self.validation_stats['total_trajectories'] > 0
                else 0.0
            ),
        }
    
    def reset_stats(self):
        """重置验证统计"""
        self.validation_stats = {
            'total_trajectories': 0,
            'valid_trajectories': 0,
            'invalid_trajectories': 0,
            'warnings': [],
            'errors': [],
        }
    
    def print_stats(self):
        """打印验证统计信息"""
        stats = self.get_validation_stats()
        print("=" * 60)
        print("数据验证统计")
        print("=" * 60)
        print(f"总轨迹数: {stats['total_trajectories']}")
        print(f"有效轨迹数: {stats['valid_trajectories']}")
        print(f"无效轨迹数: {stats['invalid_trajectories']}")
        print(f"有效率: {stats['valid_rate']:.2%}")
        print(f"警告数: {len(stats['warnings'])}")
        print(f"错误数: {len(stats['errors'])}")
        
        if stats['errors']:
            print("\n前 10 个错误:")
            for error in stats['errors'][:10]:
                print(f"  - {error}")
        
        if stats['warnings']:
            print("\n前 10 个警告:")
            for warning in stats['warnings'][:10]:
                print(f"  - {warning}")

