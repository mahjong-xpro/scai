"""
数据收集器 (Data Collector)

收集自对弈数据，管理轨迹数据的存储和预处理。
"""

import numpy as np
from typing import List, Dict, Optional
from collections import defaultdict

from .worker import SelfPlayWorker, create_workers, collect_trajectories_parallel
from .opponent_pool import OpponentPool
from .feeding_games import FeedingGameConfig, FeedingGameGenerator
from ..training.buffer import ReplayBuffer
from ..training.reward_shaping import RewardShaping
from ..utils.data_validator import DataValidator


class DataCollector:
    """数据收集器
    
    收集自对弈数据，管理轨迹数据的存储和预处理。
    """
    
    def __init__(
        self,
        buffer: ReplayBuffer,
        reward_shaping: RewardShaping,
        num_workers: int = 100,
        num_games_per_worker: int = 10,
        use_oracle: bool = True,
        validate_data: bool = True,
        strict_validation: bool = False,
    ):
        """
        参数：
        - buffer: 经验回放缓冲区
        - reward_shaping: 奖励函数初调实例
        - num_workers: Worker 数量（默认 100）
        - num_games_per_worker: 每个 Worker 运行的游戏数量（默认 10）
        - use_oracle: 是否使用 Oracle 特征（默认 True）
        - validate_data: 是否验证数据（默认 True）
        - strict_validation: 严格验证模式（默认 False，发现错误时只警告不抛出异常）
        """
        self.buffer = buffer
        self.reward_shaping = reward_shaping
        self.num_workers = num_workers
        self.num_games_per_worker = num_games_per_worker
        self.use_oracle = use_oracle
        self.validate_data = validate_data
        
        # 数据验证器
        if self.validate_data:
            self.validator = DataValidator(
                state_shape=(64, 4, 9),  # 特征张量形状
                action_space_size=434,
                strict_mode=strict_validation,
            )
        else:
            self.validator = None
        
        # 对手池（可选）
        self.opponent_pool = None
        self.use_opponent_pool = False
        
        # 喂牌机制（可选）
        self.feeding_config = None
        self.use_feeding = False
        
        # 课程学习配置（用于传递阶段信息给Worker）
        self.curriculum = None
        self.enable_win = True  # 是否允许胡牌（所有阶段都允许，通过奖励函数引导是否追求）
        
        # Worker 列表
        self.workers = None
    
    def initialize_workers(self, use_feeding: bool = False, enable_win: bool = True):
        """初始化 Worker
        
        参数：
        - use_feeding: 是否使用喂牌模式
        - enable_win: 是否开启胡牌功能
        """
        if self.workers is None:
            # 传递 reward_config 到 worker，确保奖励配置一致
            reward_config = self.reward_shaping.reward_config if self.reward_shaping else {}
            self.workers = create_workers(
                num_workers=self.num_workers,
                num_games_per_worker=self.num_games_per_worker,
                use_oracle=self.use_oracle,
                use_feeding=use_feeding,
                feeding_config=self.feeding_config if self.use_feeding else None,
                enable_win=enable_win,
                reward_config=reward_config,
            )
    
    def enable_opponent_pool(
        self,
        checkpoint_dir: str = './checkpoints',
        pool_size: int = 10,
        selection_strategy: str = 'uniform',
    ):
        """
        启用对手池系统
        
        参数：
        - checkpoint_dir: Checkpoint 目录
        - pool_size: 池大小
        - selection_strategy: 选择策略
        """
        self.opponent_pool = OpponentPool(
            checkpoint_dir=checkpoint_dir,
            pool_size=pool_size,
            selection_strategy=selection_strategy,
        )
        self.use_opponent_pool = True
    
    def enable_feeding_games(
        self,
        enabled: bool = True,
        difficulty: str = 'easy',
        feeding_rate: float = 0.8,
        win_types: Optional[List[str]] = None,
    ):
        """
        启用喂牌机制
        
        参数：
        - enabled: 是否启用
        - difficulty: 难度级别
        - feeding_rate: 喂牌概率
        - win_types: 要学习的胡牌类型列表
        """
        if enabled:
            self.feeding_config = FeedingGameConfig(
                enabled=True,
                difficulty=difficulty,
                feeding_rate=feeding_rate,
                win_types=win_types or ['basic', 'seven_pairs'],
            )
            self.use_feeding = True
        else:
            self.use_feeding = False
    
    def add_model_to_pool(
        self,
        model,
        iteration: int,
        elo_rating: float = 1500.0,
    ):
        """
        添加模型到对手池
        
        参数：
        - model: 模型实例
        - iteration: 迭代次数
        - elo_rating: Elo 评分
        """
        if self.opponent_pool:
            self.opponent_pool.add_model(model, iteration, elo_rating)
    
    def collect(
        self,
        model_state_dict: Dict,
        current_iteration: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        收集轨迹数据
        
        参数：
        - model_state_dict: 模型状态字典
        
        返回：
        - 包含收集统计信息的字典
        """
        if self.workers is None:
            # 添加日志以便调试
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Initializing {self.num_workers} workers...")
            self.initialize_workers()
            logger.info(f"Workers initialized successfully")
        
        # 添加日志以便调试
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting parallel trajectory collection with {len(self.workers)} workers...")
        
        # 并行收集轨迹（传递 reward_config，确保 worker 使用正确的奖励配置）
        # 重要：每次都从reward_shaping获取最新的reward_config，因为curriculum阶段可能已经变化
        reward_config = self.reward_shaping.reward_config if self.reward_shaping else {}
        
        # 调试信息：打印reward_config（仅第一次收集时打印）
        if not hasattr(self, '_reward_config_logged'):
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"DataCollector: Using reward_config: {reward_config}")
            if not reward_config:
                logger.warning("DataCollector: reward_config is empty! This may cause all rewards to be zero.")
            self._reward_config_logged = True
        
        trajectories = collect_trajectories_parallel(
            self.workers,
            model_state_dict,
            reward_config=reward_config,
        )
        
        logger.info(f"Collection complete: {len(trajectories)} trajectories collected")
        
        # 处理轨迹，添加到缓冲区
        num_trajectories = len(trajectories)
        total_steps = 0
        valid_trajectories = 0
        invalid_trajectories = 0
        
        # 用于保存到dashboard的游戏轨迹（选择有代表性的游戏）
        games_to_replay = []
        
        # 生成全局唯一的游戏计数器（使用时间戳和迭代次数）
        import time
        base_game_id = int(time.time() * 1000) % 1000000  # 使用毫秒时间戳的后6位作为基础ID
        
        for traj_idx, trajectory in enumerate(trajectories):
            # 验证轨迹（如果启用）
            is_valid = True
            validation_errors = []
            
            if self.validate_data and self.validator is not None:
                is_valid, validation_errors = self.validator.validate_trajectory(
                    trajectory,
                    trajectory_id=f"trajectory_{traj_idx}",
                )
                
                if not is_valid:
                    invalid_trajectories += 1
                    # 记录无效轨迹（即使是非严格模式）
                    if validation_errors:
                        # 只打印前几个轨迹的详细错误，避免日志过多
                        if traj_idx < 3:
                            print(f"Warning: Trajectory {traj_idx} has {len(validation_errors)} validation errors:")
                            for error in validation_errors[:10]:  # 显示前10个错误
                                print(f"  - {error}")
                        elif traj_idx == 3:
                            print(f"Warning: More trajectories have validation errors. Suppressing detailed logs...")
                            print(f"  (Showing error summary at the end of collection)")
                        # 在非严格模式下，记录但继续处理
                        if self.validator.strict_mode:
                            # 严格模式：跳过无效轨迹
                            continue
                else:
                    valid_trajectories += 1
            else:
                # 如果没有验证，假设所有轨迹都有效
                valid_trajectories += 1
                is_valid = True
            
            # 计算无效轨迹比例（在处理每个轨迹后检查）
            total_checked = valid_trajectories + invalid_trajectories
            if total_checked > 0:
                invalid_rate = invalid_trajectories / total_checked
                # 如果无效轨迹比例超过 50%，发出警告
                if invalid_rate > 0.5 and total_checked >= 10:
                    print(f"Warning: High invalid trajectory rate: {invalid_rate:.2%} ({invalid_trajectories}/{total_checked})")
                    print("Consider checking data collection logic or validation rules.")
            
            # 更新奖励（在验证之后，因为验证检查的是原始奖励）
            # 注意：update_rewards会在最后一步添加final_reward，但验证时检查的是原始step rewards
            rewards = self.reward_shaping.update_rewards(
                trajectory['rewards'],
                trajectory['final_score'],
                is_winner=trajectory['final_score'] > 0,
            )
            
            # 调试信息：检查奖励是否真的都是0（仅前几个轨迹）
            if traj_idx < 3 and len(trajectory['rewards']) > 0:
                original_rewards = trajectory['rewards']
                non_zero_count = sum(1 for r in original_rewards if abs(float(r)) > 1e-6)
                if non_zero_count == 0:
                    print(f"Debug: Trajectory {traj_idx}: All {len(original_rewards)} step rewards are zero")
                    print(f"  First 5 rewards: {original_rewards[:5]}")
                    print(f"  Final score: {trajectory.get('final_score', 0.0)}")
                else:
                    print(f"Debug: Trajectory {traj_idx}: {non_zero_count}/{len(original_rewards)} rewards are non-zero")
                    non_zero_rewards = [r for r in original_rewards if abs(float(r)) > 1e-6]
                    print(f"  Non-zero rewards (first 5): {non_zero_rewards[:5]}")
            
            # 添加到缓冲区
            for i in range(len(trajectory['states'])):
                self.buffer.add(
                    state=trajectory['states'][i],
                    action=trajectory['actions'][i],
                    reward=rewards[i],
                    value=trajectory['values'][i],
                    log_prob=trajectory['log_probs'][i],
                    done=trajectory['dones'][i],
                    action_mask=trajectory['action_masks'][i] if 'action_masks' in trajectory else None,
                )
                total_steps += 1
            
            # 完成轨迹
            self.buffer.finish_trajectory()
            
            # 选择有代表性的游戏保存到dashboard（每10个游戏选1个，或者最终得分高的）
            if is_valid and len(trajectory['states']) > 0:
                final_score = trajectory.get('final_score', 0.0)
                # 选择条件：1) 每10个游戏选1个，2) 最终得分>0的，3) 步骤数>10的（完整的游戏）
                should_save = (
                    (traj_idx % 10 == 0) or  # 每10个选1个
                    (final_score > 0) or  # 有得分的游戏
                    (len(trajectory['states']) > 50)  # 长游戏
                ) and len(trajectory['states']) > 10  # 至少10步
                
                if should_save:
                    # 生成唯一的game_id（使用时间戳基础 + 迭代次数 + 轨迹索引）
                    # 格式：base_game_id * 1000000 + iteration * 1000 + traj_idx
                    # 这样可以确保全局唯一，且能反推出迭代和游戏序号
                    iteration_part = (current_iteration or 0) % 1000  # 迭代次数（最多999）
                    traj_part = traj_idx % 1000  # 轨迹索引（最多999）
                    unique_game_id = base_game_id * 1000000 + iteration_part * 1000 + traj_part
                    
                    games_to_replay.append({
                        'game_id': unique_game_id,
                        'iteration': current_iteration,
                        'game_index_in_iteration': traj_idx,  # 在当前迭代中的游戏序号
                        'total_games_in_iteration': num_trajectories,  # 当前迭代的总游戏数
                        'trajectory': trajectory,
                        'game_info': {
                            'final_score': final_score,
                            'num_steps': len(trajectory['states']),
                            'is_winner': final_score > 0,
                        },
                    })
        
        # 计算优势函数
        self.buffer.compute_advantages()
        
        result = {
            'num_trajectories': num_trajectories,
            'total_steps': total_steps,
            'buffer_size': self.buffer.size(),
        }
        
        # 添加验证统计（如果启用）
        if self.validate_data and self.validator is not None:
            validation_stats = self.validator.get_validation_stats()
            result['validation'] = {
                'valid_trajectories': validation_stats['valid_trajectories'],
                'invalid_trajectories': validation_stats['invalid_trajectories'],
                'valid_rate': validation_stats['valid_rate'],
                'num_errors': len(validation_stats['errors']),
                'num_warnings': len(validation_stats['warnings']),
            }
            # 如果有错误或警告，打印统计信息
            if (validation_stats.get('top_errors') and len(validation_stats['top_errors']) > 0) or \
               (validation_stats.get('top_warnings') and len(validation_stats['top_warnings']) > 0):
                print(f"\n{'='*60}")
                print(f"Validation Summary:")
                print(f"  Valid trajectories: {validation_stats['valid_trajectories']}")
                print(f"  Invalid trajectories: {validation_stats['invalid_trajectories']}")
                print(f"  Valid rate: {validation_stats['valid_rate']:.2%}")
                
                # 显示最常见的警告类型（如果有）
                if validation_stats.get('top_warnings') and len(validation_stats['top_warnings']) > 0:
                    print(f"\nTop 5 most common warning types (total: {len(validation_stats['warnings'])}):")
                    for warning_type, count in validation_stats['top_warnings']:
                        percentage = (count / len(validation_stats['warnings'])) * 100 if validation_stats['warnings'] else 0
                        print(f"  - {warning_type}: {count} occurrences ({percentage:.1f}%)")
                
                # 显示最常见的错误类型（如果有）
                if validation_stats.get('top_errors') and len(validation_stats['top_errors']) > 0:
                    print(f"\nTop 5 most common error types (total: {len(validation_stats['errors'])}):")
                    for error_type, count in validation_stats['top_errors']:
                        percentage = (count / len(validation_stats['errors'])) * 100 if validation_stats['errors'] else 0
                        print(f"  - {error_type}: {count} occurrences ({percentage:.1f}%)")
                
                print(f"{'='*60}\n")
        
        # 将选中的游戏轨迹保存到dashboard（如果可用）
        if games_to_replay:
            try:
                from ..coach.dashboard import get_state_manager
                state_manager = get_state_manager()
                for game_data in games_to_replay:
                    state_manager.add_game_replay(game_data)
            except Exception as e:
                # 如果dashboard不可用，静默失败（不影响训练）
                pass
        
        return result
    
    def collect_batch(
        self,
        model_state_dict: Dict,
        num_batches: int = 1,
    ) -> Dict[str, int]:
        """
        批量收集轨迹数据
        
        参数：
        - model_state_dict: 模型状态字典
        - num_batches: 批次数（默认 1）
        
        返回：
        - 包含收集统计信息的字典
        """
        total_stats = {
            'num_trajectories': 0,
            'total_steps': 0,
        }
        
        for _ in range(num_batches):
            stats = self.collect(model_state_dict)
            total_stats['num_trajectories'] += stats['num_trajectories']
            total_stats['total_steps'] += stats['total_steps']
        
        total_stats['buffer_size'] = self.buffer.size()
        
        return total_stats

