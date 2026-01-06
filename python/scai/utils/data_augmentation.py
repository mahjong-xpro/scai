"""
数据增强 (Data Augmentation)

实现轨迹数据的增强，提升数据效率和模型鲁棒性。
支持：
- 花色对称性（万、筒、条互换）
- 数字对称性（1-9 镜像）
- 玩家位置旋转
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import random


class DataAugmentation:
    """数据增强器"""
    
    def __init__(
        self,
        enable_suit_symmetry: bool = True,
        enable_rank_symmetry: bool = True,
        enable_position_rotation: bool = True,
        rotation_prob: float = 0.5,
        symmetry_prob: float = 0.5,
    ):
        """
        参数：
        - enable_suit_symmetry: 是否启用花色对称性
        - enable_rank_symmetry: 是否启用数字对称性
        - enable_position_rotation: 是否启用玩家位置旋转
        - rotation_prob: 旋转概率
        - symmetry_prob: 对称性概率
        """
        self.enable_suit_symmetry = enable_suit_symmetry
        self.enable_rank_symmetry = enable_rank_symmetry
        self.enable_position_rotation = enable_position_rotation
        self.rotation_prob = rotation_prob
        self.symmetry_prob = symmetry_prob
        
        # 花色映射：万(0-8) -> 筒(9-17) -> 条(18-26)
        self.suit_mappings = [
            list(range(27)),  # 原始
            [i + 9 if i < 9 else (i - 9 if i < 18 else i - 18) for i in range(27)],  # 万->筒
            [i + 18 if i < 9 else (i - 9 if i < 18 else i - 9) for i in range(27)],  # 万->条
            [i - 9 if i >= 9 and i < 18 else (i + 9 if i >= 18 else i + 18) for i in range(27)],  # 筒->万
            [i + 9 if i < 9 else (i - 9 if i >= 18 else i + 9) for i in range(27)],  # 筒->条
            [i - 18 if i >= 18 else (i + 18 if i < 9 else i + 9) for i in range(27)],  # 条->万
        ]
        
        # 数字对称性映射：1-9 镜像 (1<->9, 2<->8, 3<->7, 4<->6, 5不变)
        self.rank_mirror = {
            0: 8, 1: 7, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1, 8: 0,  # 万
            9: 17, 10: 16, 11: 15, 12: 14, 13: 13, 14: 12, 15: 11, 16: 10, 17: 9,  # 筒
            18: 26, 19: 25, 20: 24, 21: 23, 22: 22, 23: 21, 24: 20, 25: 19, 26: 18,  # 条
        }
    
    def augment_trajectory(
        self,
        trajectory: Dict[str, List],
        apply_augmentation: Optional[bool] = None,
    ) -> Dict[str, List]:
        """
        增强轨迹数据
        
        参数：
        - trajectory: 原始轨迹（包含 states, actions, rewards, values, log_probs, action_masks）
        - apply_augmentation: 是否应用增强（None 表示随机决定）
        
        返回：
        - 增强后的轨迹
        """
        if apply_augmentation is None:
            apply_augmentation = random.random() < self.symmetry_prob
        
        if not apply_augmentation:
            return trajectory
        
        # 随机选择增强类型
        augmentation_type = random.choice(['suit', 'rank', 'position', 'combined'])
        
        if augmentation_type == 'suit' and self.enable_suit_symmetry:
            return self._apply_suit_symmetry(trajectory)
        elif augmentation_type == 'rank' and self.enable_rank_symmetry:
            return self._apply_rank_symmetry(trajectory)
        elif augmentation_type == 'position' and self.enable_position_rotation:
            return self._apply_position_rotation(trajectory)
        elif augmentation_type == 'combined':
            # 组合多种增强
            traj = trajectory
            if self.enable_suit_symmetry and random.random() < 0.5:
                traj = self._apply_suit_symmetry(traj)
            if self.enable_rank_symmetry and random.random() < 0.5:
                traj = self._apply_rank_symmetry(traj)
            if self.enable_position_rotation and random.random() < self.rotation_prob:
                traj = self._apply_position_rotation(traj)
            return traj
        else:
            return trajectory
    
    def _apply_suit_symmetry(self, trajectory: Dict[str, List]) -> Dict[str, List]:
        """应用花色对称性"""
        # 随机选择一个花色映射
        suit_mapping = random.choice(self.suit_mappings[1:])  # 排除原始映射
        
        augmented = {
            'states': [],
            'actions': [],
            'rewards': trajectory['rewards'].copy(),
            'values': trajectory['values'].copy(),
            'log_probs': trajectory['log_probs'].copy(),
            'action_masks': [],
            'dones': trajectory.get('dones', [False] * len(trajectory['states'])).copy(),
        }
        
        for state, action, action_mask in zip(
            trajectory['states'],
            trajectory['actions'],
            trajectory.get('action_masks', [None] * len(trajectory['states'])),
        ):
            # 转换状态张量（64 x 4 x 9）
            augmented_state = self._transform_state_tensor(state, suit_mapping)
            augmented['states'].append(augmented_state)
            
            # 转换动作
            augmented_action = self._transform_action(action, suit_mapping)
            augmented['actions'].append(augmented_action)
            
            # 转换动作掩码
            if action_mask is not None:
                augmented_mask = self._transform_action_mask(action_mask, suit_mapping)
                augmented['action_masks'].append(augmented_mask)
            else:
                augmented['action_masks'].append(None)
        
        if 'final_score' in trajectory:
            augmented['final_score'] = trajectory['final_score']
        
        return augmented
    
    def _apply_rank_symmetry(self, trajectory: Dict[str, List]) -> Dict[str, List]:
        """应用数字对称性（镜像）"""
        augmented = {
            'states': [],
            'actions': [],
            'rewards': trajectory['rewards'].copy(),
            'values': trajectory['values'].copy(),
            'log_probs': trajectory['log_probs'].copy(),
            'action_masks': [],
            'dones': trajectory.get('dones', [False] * len(trajectory['states'])).copy(),
        }
        
        for state, action, action_mask in zip(
            trajectory['states'],
            trajectory['actions'],
            trajectory.get('action_masks', [None] * len(trajectory['states'])),
        ):
            # 转换状态张量
            augmented_state = self._transform_state_tensor(state, self.rank_mirror)
            augmented['states'].append(augmented_state)
            
            # 转换动作
            augmented_action = self._transform_action(action, self.rank_mirror)
            augmented['actions'].append(augmented_action)
            
            # 转换动作掩码
            if action_mask is not None:
                augmented_mask = self._transform_action_mask(action_mask, self.rank_mirror)
                augmented['action_masks'].append(augmented_mask)
            else:
                augmented['action_masks'].append(None)
        
        if 'final_score' in trajectory:
            augmented['final_score'] = trajectory['final_score']
        
        return augmented
    
    def _apply_position_rotation(self, trajectory: Dict[str, List]) -> Dict[str, List]:
        """应用玩家位置旋转（0->1->2->3->0）"""
        rotation = random.randint(1, 3)  # 1, 2, 3 步旋转
        
        augmented = {
            'states': [],
            'actions': [],
            'rewards': trajectory['rewards'].copy(),
            'values': trajectory['values'].copy(),
            'log_probs': trajectory['log_probs'].copy(),
            'action_masks': [],
            'dones': trajectory.get('dones', [False] * len(trajectory['states'])).copy(),
        }
        
        for state, action, action_mask in zip(
            trajectory['states'],
            trajectory['actions'],
            trajectory.get('action_masks', [None] * len(trajectory['states'])),
        ):
            # 旋转状态张量（64 x 4 x 9）- 旋转玩家维度
            augmented_state = np.roll(state, rotation, axis=1)  # 沿玩家维度旋转
            augmented['states'].append(augmented_state)
            
            # 动作不需要转换（动作索引是全局的）
            augmented['actions'].append(action)
            
            # 动作掩码也不需要转换
            if action_mask is not None:
                augmented['action_masks'].append(action_mask)
            else:
                augmented['action_masks'].append(None)
        
        if 'final_score' in trajectory:
            augmented['final_score'] = trajectory['final_score']
        
        return augmented
    
    def _transform_state_tensor(
        self,
        state: np.ndarray,
        tile_mapping: Dict[int, int],
    ) -> np.ndarray:
        """
        转换状态张量
        
        参数：
        - state: 状态张量 (64 x 4 x 9)
        - tile_mapping: 牌型映射字典 {old_tile_index: new_tile_index}
        
        返回：
        - 转换后的状态张量
        """
        if isinstance(tile_mapping, list):
            tile_mapping = {i: tile_mapping[i] for i in range(len(tile_mapping))}
        
        augmented_state = state.copy()
        
        # 对于每个平面，如果它表示特定牌型，需要转换
        # 这里简化处理：只转换前 27 个平面（手牌、弃牌等）
        # 实际实现需要根据特征编码的具体设计来调整
        
        # 创建新的状态张量
        new_state = np.zeros_like(state)
        
        # 对于每个牌型索引 (0-26)
        for old_idx in range(27):
            new_idx = tile_mapping.get(old_idx, old_idx)
            
            # 计算平面索引（假设前 27 个平面对应 27 种牌型）
            # 这里需要根据实际的特征编码来调整
            # 简化：假设每个牌型对应多个平面
            old_plane_start = old_idx // 9 * 3 + old_idx % 9
            new_plane_start = new_idx // 9 * 3 + new_idx % 9
            
            # 复制对应的平面
            if old_plane_start < state.shape[0] and new_plane_start < state.shape[0]:
                new_state[new_plane_start] = state[old_plane_start]
        
        # 对于不涉及牌型转换的平面（如全局特征），直接复制
        # 这里简化处理，实际需要根据特征编码设计来精确实现
        return augmented_state
    
    def _transform_action(
        self,
        action: int,
        tile_mapping: Dict[int, int],
    ) -> int:
        """
        转换动作索引
        
        参数：
        - action: 原始动作索引 (0-433)
        - tile_mapping: 牌型映射
        
        返回：
        - 转换后的动作索引
        """
        # 动作编码：0-107 出牌, 108-215 碰, 216-323 杠, 324-431 胡, 432 过, 433 摸
        if action >= 432:
            return action  # 过和摸不需要转换
        
        # 计算牌型索引
        tile_index = action % 108  # 在 108 种牌型中的索引
        action_type = action // 108  # 动作类型
        
        # 转换牌型索引
        if isinstance(tile_mapping, list):
            if tile_index < len(tile_mapping):
                new_tile_index = tile_mapping[tile_index]
            else:
                new_tile_index = tile_index
        else:
            new_tile_index = tile_mapping.get(tile_index, tile_index)
        
        # 重新计算动作索引
        new_action = action_type * 108 + new_tile_index
        return new_action
    
    def _transform_action_mask(
        self,
        action_mask: List[float],
        tile_mapping: Dict[int, int],
    ) -> List[float]:
        """
        转换动作掩码
        
        参数：
        - action_mask: 原始动作掩码 (434,)
        - tile_mapping: 牌型映射
        
        返回：
        - 转换后的动作掩码
        """
        augmented_mask = [0.0] * len(action_mask)
        
        # 对于每个动作
        for old_action in range(len(action_mask)):
            if action_mask[old_action] == 0:
                continue
            
            # 转换动作
            new_action = self._transform_action(old_action, tile_mapping)
            
            # 复制掩码值
            if new_action < len(augmented_mask):
                augmented_mask[new_action] = action_mask[old_action]
        
        return augmented_mask
    
    def augment_batch(
        self,
        trajectories: List[Dict[str, List]],
        augmentation_rate: float = 0.5,
    ) -> List[Dict[str, List]]:
        """
        批量增强轨迹
        
        参数：
        - trajectories: 轨迹列表
        - augmentation_rate: 增强比例（0.0-1.0）
        
        返回：
        - 增强后的轨迹列表（原始 + 增强）
        """
        augmented_trajectories = trajectories.copy()
        
        num_augment = int(len(trajectories) * augmentation_rate)
        indices_to_augment = random.sample(range(len(trajectories)), num_augment)
        
        for idx in indices_to_augment:
            augmented = self.augment_trajectory(trajectories[idx], apply_augmentation=True)
            augmented_trajectories.append(augmented)
        
        return augmented_trajectories

