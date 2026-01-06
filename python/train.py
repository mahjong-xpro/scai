#!/usr/bin/env python3
"""
主训练脚本 (Main Training Script)

整合所有组件，实现完整的强化学习训练循环：
- 分布式自对弈数据收集
- PPO 策略优化
- 模型评估和 Elo 评分
- Checkpoint 管理
- 可选：对抗训练、超参数搜索、LLM 教练

使用方法：
    python train.py --config config.yaml
    python train.py --config config.yaml --resume checkpoints/latest.pt
"""

import argparse
import os
import sys
import yaml
import torch
import numpy as np
import signal
import shutil
import time
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 Ray（分布式训练）
try:
    import ray
    HAS_RAY = True
except ImportError:
    HAS_RAY = False
    print("Warning: Ray not found. Install with: pip install ray")

# 导入项目模块
from scai.models import DualResNet
from scai.training.trainer import Trainer
from scai.training.ppo import PPO
from scai.training.buffer import ReplayBuffer
from scai.training.reward_shaping import RewardShaping
from scai.training.evaluator import Evaluator
from scai.selfplay.collector import DataCollector
from scai.utils.checkpoint import CheckpointManager

# 可选组件
try:
    from scai.training.adversarial import AdversarialTrainer
    HAS_ADVERSARIAL = True
except ImportError:
    HAS_ADVERSARIAL = False

try:
    from scai.coach.curriculum import CurriculumLearning, TrainingStage
    from scai.coach.document_generator import TrainingDocumentGenerator
    from scai.coach.dashboard import update_training_status
    from scai.coach.web_server import start_server
    import threading
    HAS_COACH = True
except ImportError:
    HAS_COACH = False

try:
    from scai.utils.data_augmentation import DataAugmentation
    HAS_DATA_AUG = True
except ImportError:
    HAS_DATA_AUG = False

try:
    from scai.search.ismcts import ISMCTS
    HAS_ISMCTS = True
except ImportError:
    HAS_ISMCTS = False


# 导入日志系统
from scai.utils.logger import get_logger, get_metrics_logger


def load_config(config_path: str) -> Dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def create_model(config: Dict, device: str = 'cpu', logger=None) -> DualResNet:
    """创建模型"""
    model_config = config.get('model', {})
    backbone_config = model_config.get('backbone', {})
    policy_config = model_config.get('policy_head', {})
    value_config = model_config.get('value_head', {})
    
    model = DualResNet(
        input_channels=model_config.get('input_channels', 64),
        num_blocks=backbone_config.get('num_blocks', 20),
        base_channels=backbone_config.get('channels', 128),
        feature_dim=policy_config.get('hidden_size', 512),
        action_space_size=model_config.get('action_space_size', 434),
        hidden_dim=value_config.get('hidden_size', 256),
    )
    
    model = model.to(device)
    num_params = sum(p.numel() for p in model.parameters())
    if logger:
        logger.info(f"Created model with {num_params} parameters")
    else:
        print(f"Created model with {num_params} parameters")
    
    return model


def initialize_ray(config: Dict):
    """初始化 Ray 集群"""
    if not HAS_RAY:
        raise ImportError("Ray is required for distributed training. Install with: pip install ray")
    
    ray_config = config.get('ray', {})
    if ray_config.get('init', True):
        if not ray.is_initialized():
            ray.init(
                num_cpus=ray_config.get('num_cpus', None),
                num_gpus=ray_config.get('num_gpus', 0),
                ignore_reinit_error=True,
            )
            logger.info("Ray initialized")
        else:
            logger.info("Ray already initialized")


def main():
    parser = argparse.ArgumentParser(description='Train Mahjong AI using Reinforcement Learning')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--resume', type=str, default=None, help='Path to checkpoint to resume from')
    parser.add_argument('--device', type=str, default=None, help='Device (cpu/cuda, auto-detect if not specified)')
    parser.add_argument('--eval-only', action='store_true', help='Only evaluate, do not train')
    
    args = parser.parse_args()
    
    # 加载配置
    config_path = args.config
    if not os.path.exists(config_path):
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    
    config = load_config(config_path)
    
    # 初始化日志系统
    logging_config = config.get('logging', {})
    logger = get_logger(
        log_dir=logging_config.get('log_dir', './logs'),
        log_level=logging_config.get('log_level', 'INFO'),
        use_json=logging_config.get('use_json', False),
        console_output=logging_config.get('console_output', True),
    )
    metrics_logger = None
    if logging_config.get('metrics_logging', True):
        metrics_logger = get_metrics_logger(log_dir=logging_config.get('log_dir', './logs'))
    
    logger.info(f"Loaded config from {config_path}")
    
    # 设备选择
    if args.device:
        device = args.device
    else:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"Using device: {device}")
    
    # 初始化 Ray（如果需要）
    if not args.eval_only:
        initialize_ray(config)
    
    # 创建模型
    model = create_model(config, device, logger)
    
    # 创建组件
    training_config = config.get('training', {})
    selfplay_config = config.get('selfplay', {})
    eval_config = config.get('evaluation', {})
    
    # 经验回放缓冲区
    buffer = ReplayBuffer(capacity=training_config.get('buffer_capacity', 100000))
    
    # 奖励函数（初始配置，会根据课程学习阶段动态调整）
    initial_reward_config = {}
    if curriculum:
        initial_reward_config = curriculum.get_current_reward_config()
    
    reward_shaping = RewardShaping(
        ready_reward=training_config.get('ready_reward', 0.1),
        hu_reward=training_config.get('hu_reward', 1.0),
        flower_pig_penalty=training_config.get('flower_pig_penalty', -5.0),
        final_score_weight=training_config.get('final_score_weight', 1.0),
        reward_config=initial_reward_config,  # 使用课程学习阶段的奖励配置
    )
    
    if curriculum:
        logger.info(f"Reward config for stage {curriculum.current_stage.value}: {initial_reward_config}")
    
    # PPO 算法
    ppo = PPO(
        model=model,
        learning_rate=training_config.get('learning_rate', 3e-4),
        clip_epsilon=training_config.get('clip_epsilon', 0.2),
        value_coef=training_config.get('value_coef', 0.5),
        entropy_coef=training_config.get('entropy_coef', 0.01),
        max_grad_norm=training_config.get('max_grad_norm', 0.5),
        device=device,
    )
    
    # 训练器
    checkpoint_dir = config.get('checkpoint_dir', './checkpoints')
    trainer = Trainer(
        model=model,
        buffer=buffer,
        ppo=ppo,
        reward_shaping=reward_shaping,
        checkpoint_dir=checkpoint_dir,
        device=device,
    )
    
    # 数据收集器
    collector = None
    if not args.eval_only:
        collector = DataCollector(
            buffer=buffer,
            reward_shaping=reward_shaping,
            num_workers=selfplay_config.get('num_workers', 100),
            num_games_per_worker=selfplay_config.get('games_per_worker', 10),
            use_oracle=selfplay_config.get('oracle_enabled', True),
            validate_data=selfplay_config.get('validate_data', True),
            strict_validation=selfplay_config.get('strict_validation', False),
        )
        
        # 启用对手池（如果配置）
        opponent_pool_config = config.get('opponent_pool', {})
        if opponent_pool_config.get('enabled', False):
            collector.enable_opponent_pool(
                checkpoint_dir=checkpoint_dir,
                pool_size=opponent_pool_config.get('pool_size', 10),
                selection_strategy=opponent_pool_config.get('selection_strategy', 'uniform'),
            )
            logger.info("Opponent pool enabled")
    
    # 数据增强（如果启用）
    data_aug = None
    if HAS_DATA_AUG:
        aug_config = config.get('data_augmentation', {})
        if aug_config.get('enabled', False):
            data_aug = DataAugmentation(
                enable_suit_symmetry=aug_config.get('suit_symmetry', True),
                enable_rank_symmetry=aug_config.get('rank_symmetry', True),
                enable_position_rotation=aug_config.get('position_rotation', True),
                rotation_prob=aug_config.get('rotation_prob', 0.5),
                symmetry_prob=aug_config.get('symmetry_prob', 0.5),
            )
            logger.info("Data augmentation enabled")
    
    # 课程学习（如果启用）
    curriculum = None
    document_generator = None
    if HAS_COACH:
        curriculum_config = config.get('curriculum_learning', {})
        if curriculum_config.get('enabled', False):
            # 创建文档生成器
            doc_output_dir = curriculum_config.get('document_output_dir', './coach_documents')
            document_generator = TrainingDocumentGenerator(output_dir=doc_output_dir)
            
            # 创建课程学习规划器
            curriculum = CurriculumLearning(document_generator=document_generator)
            
            # 设置初始阶段（如果配置中指定）
            initial_stage_str = curriculum_config.get('initial_stage', 'declare_suit')
            if initial_stage_str == 'declare_suit':
                curriculum.current_stage = TrainingStage.DECLARE_SUIT
            elif initial_stage_str == 'learn_win':
                curriculum.current_stage = TrainingStage.LEARN_WIN
            elif initial_stage_str == 'basic':
                curriculum.current_stage = TrainingStage.BASIC
            elif initial_stage_str == 'defensive':
                curriculum.current_stage = TrainingStage.DEFENSIVE
            elif initial_stage_str == 'advanced':
                curriculum.current_stage = TrainingStage.ADVANCED
            elif initial_stage_str == 'expert':
                curriculum.current_stage = TrainingStage.EXPERT
            
            logger.info(f"Curriculum learning enabled (document generation mode), initial stage: {curriculum.current_stage.value}")
            
            # 启动 Web 仪表板（如果启用）
            dashboard_config = curriculum_config.get('dashboard', {})
            if dashboard_config.get('enabled', False):
                dashboard_port = dashboard_config.get('port', 5000)
                dashboard_host = dashboard_config.get('host', '0.0.0.0')
                # 在后台线程启动 Web 服务器
                dashboard_thread = threading.Thread(
                    target=start_server,
                    args=(dashboard_host, dashboard_port, False),
                    daemon=True,
                )
                dashboard_thread.start()
                logger.info(f"课程学习中心 Web 仪表板已启动: http://{dashboard_host}:{dashboard_port}")
    
    # 搜索增强推理（如果启用）
    ismcts = None
    search_config = config.get('search_enhanced_inference', {})
    if HAS_ISMCTS and search_config.get('enabled', False):
        ismcts = ISMCTS(
            num_simulations=search_config.get('num_simulations', 100),
            exploration_constant=search_config.get('exploration_constant', 1.41),
            determinization_samples=search_config.get('determinization_samples', 10),
        )
        logger.info("Search-enhanced inference enabled")
    
    # 评估器
    evaluator = Evaluator(
        checkpoint_dir=checkpoint_dir,
        elo_threshold=eval_config.get('elo_threshold', 0.55),
        device=device,
    )
    
    # 加载 Checkpoint（如果指定）
    start_iteration = 0
    if args.resume:
        logger.info(f"Resuming from checkpoint: {args.resume}")
        checkpoint = trainer.load_checkpoint(args.resume)
        start_iteration = checkpoint.get('iteration', 0)
        logger.info(f"Resumed from iteration {start_iteration}")
    elif not args.eval_only:
        # 尝试加载最新 Checkpoint
        checkpoint_manager = CheckpointManager(checkpoint_dir)
        latest_checkpoint = checkpoint_manager.get_latest_checkpoint()
        if latest_checkpoint:
            logger.info(f"Found latest checkpoint: {latest_checkpoint}")
            response = input("Resume from latest checkpoint? (y/n): ")
            if response.lower() == 'y':
                checkpoint = trainer.load_checkpoint(latest_checkpoint)
                start_iteration = checkpoint.get('iteration', 0)
                logger.info(f"Resumed from iteration {start_iteration}")
    
    # 仅评估模式
    if args.eval_only:
        logger.info("Running evaluation only...")
        if args.resume:
            checkpoint_path = args.resume
        else:
            checkpoint_manager = CheckpointManager(checkpoint_dir)
            checkpoint_path = checkpoint_manager.get_latest_checkpoint()
        
        if not checkpoint_path:
            logger.error("No checkpoint found for evaluation")
            sys.exit(1)
        
        # 评估模型
        results = evaluator.evaluate_model(model, num_games=eval_config.get('num_eval_games', 100))
        logger.info(f"Evaluation results: {results}")
        return
    
    # 训练循环
    num_iterations = training_config.get('num_iterations', 1000)
    collect_interval = training_config.get('collect_interval', 1)  # 每 N 次迭代收集一次
    eval_interval = eval_config.get('eval_interval', 100)  # 每 N 次迭代评估一次
    save_interval = training_config.get('save_interval', 100)  # 每 N 次迭代保存一次
    
    logger.info("Starting training loop...")
    logger.info(f"Total iterations: {num_iterations}")
    logger.info(f"Collect interval: {collect_interval}")
    logger.info(f"Eval interval: {eval_interval}")
    logger.info(f"Save interval: {save_interval}")
    
    # 添加信号处理，支持优雅中断
    import signal
    interrupted = False
    
    def signal_handler(sig, frame):
        nonlocal interrupted
        logger.info("\nTraining interrupted by user (Ctrl+C)")
        interrupted = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    for iteration in range(start_iteration, num_iterations):
        # 检查是否被中断
        if interrupted:
            logger.info("Saving checkpoint before exit...")
            try:
                trainer.save_checkpoint(iteration + 1)
                logger.info(f"Checkpoint saved at iteration {iteration + 1}")
            except Exception as e:
                logger.error(f"Failed to save checkpoint: {e}")
            break
        
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Iteration {iteration + 1}/{num_iterations}")
            logger.info(f"{'='*60}")
            
            # 更新仪表板状态（如果启用）
            if HAS_COACH and curriculum is not None:
            current_metrics = {
                'iteration': iteration + 1,
                'buffer_size': buffer.size(),
            }
            if metrics_logger:
                recent_metrics = metrics_logger.get_recent_metrics()
                current_metrics.update(recent_metrics)
            
            training_stats = {
                'buffer_size': buffer.size(),
                'buffer_ready': buffer.is_ready(min_size=training_config.get('batch_size', 4096)),
            }
            
            update_training_status(
                curriculum=curriculum,
                current_iteration=iteration + 1,
                total_iterations=num_iterations,
                metrics=current_metrics,
                training_stats=training_stats,
            )
        
        # 0. 课程学习阶段调整（如果启用）
        if curriculum is not None:
            curriculum_config = config.get('curriculum_learning', {})
            if (iteration + 1) % curriculum_config.get('llm_coach_frequency', 100) == 0:
                # 获取当前性能指标
                current_metrics = {
                    'iteration': iteration + 1,
                    'buffer_size': buffer.size(),
                }
                if metrics_logger:
                    # 尝试从指标日志获取最近的评估结果
                    recent_metrics = metrics_logger.get_recent_metrics()
                    current_metrics.update(recent_metrics)
                
                # 生成课程规划文档（供手动提交给大模型）
                current_issues = []  # 可以从评估结果中提取
                doc_path = curriculum.design_next_stage(
                    performance_metrics=current_metrics,
                    current_issues=current_issues,
                    iteration=iteration + 1,
                )
                if doc_path:
                    logger.info(f"Curriculum design document generated: {doc_path}")
                
                # 检查是否应该推进阶段（传入迭代次数以支持基于迭代的推进）
                if curriculum.should_advance_stage(
                    current_metrics,
                    current_iteration=iteration + 1,
                ):
                    old_stage = curriculum.current_stage
                    curriculum.advance_to_next_stage()
                    logger.info(f"Advanced from {old_stage.value} to {curriculum.current_stage.value}")
                    
                    # 更新奖励配置
                    new_reward_config = curriculum.get_current_reward_config()
                    if new_reward_config:
                        reward_shaping.reward_config = new_reward_config
                        logger.info(f"Updated reward config: {new_reward_config}")
                    
                    # 更新熵系数
                    new_entropy_coef = curriculum.get_current_entropy_coef()
                    ppo.entropy_coef = new_entropy_coef
                    logger.info(f"Updated entropy coef: {new_entropy_coef}")
                    
                    # 更新搜索增强推理
                    new_use_search = curriculum.should_use_search_enhanced()
                    if new_use_search and not use_search_enhanced and HAS_ISMCTS:
                        ismcts = ISMCTS(
                            num_simulations=search_config.get('num_simulations', 100),
                            exploration_constant=search_config.get('exploration_constant', 1.41),
                            determinization_samples=search_config.get('determinization_samples', 10),
                        )
                        use_search_enhanced = True
                        logger.info("Enabled search-enhanced inference")
                    
                    # 更新对抗训练
                    new_use_adversarial = curriculum.should_use_adversarial()
                    if new_use_adversarial:
                        logger.info("Adversarial training should be enabled for this stage")
        
        # 1. 收集数据（如果需要）
        if (iteration + 1) % collect_interval == 0:
            logger.info("Collecting trajectories...")
            model_state_dict = model.state_dict()
            
            # 根据课程学习阶段更新 collector 配置（如果启用）
            if collector and curriculum is not None:
                current_curriculum = curriculum.get_current_curriculum()
                # 更新 enable_win
                collector.enable_win = current_curriculum.enable_win
                # 更新喂牌配置
                if current_curriculum.use_feeding_games:
                    collector.enable_feeding_games(
                        enabled=True,
                        difficulty='easy',
                        feeding_rate=current_curriculum.feeding_rate,
                    )
                else:
                    collector.enable_feeding_games(enabled=False)
                # 重新初始化 workers 以应用新配置
                collector.initialize_workers(
                    use_feeding=current_curriculum.use_feeding_games,
                    enable_win=current_curriculum.enable_win,
                )
                logger.info(f"Updated collector config: enable_win={current_curriculum.enable_win}, "
                          f"use_feeding={current_curriculum.use_feeding_games}, "
                          f"feeding_rate={current_curriculum.feeding_rate if current_curriculum.use_feeding_games else 0.0}")
            
            # 如果启用了对手池，选择对手
            if collector and collector.use_opponent_pool:
                # 对手池会自动选择对手模型
                pass
            
            stats = collector.collect(model_state_dict, current_iteration=iteration + 1)
            logger.log_data_collection(iteration + 1, stats)
            
            # 应用数据增强（如果启用）
            if data_aug and buffer.size() > 0:
                aug_config = config.get('data_augmentation', {})
                if aug_config.get('enabled', False):
                    # 对缓冲区中的轨迹进行增强
                    # 注意：这里简化处理，实际应该在收集时增强
                    logger.info("Applying data augmentation...")
        
        # 2. 训练
        if buffer.is_ready(min_size=training_config.get('batch_size', 4096)):
            logger.info("Training model...")
            
            # 根据课程学习调整训练参数（如果启用）
            train_batch_size = training_config.get('batch_size', 4096)
            train_num_epochs = training_config.get('num_epochs', 10)
            
            if curriculum:
                # 根据当前阶段调整参数
                current_curriculum = curriculum.get_current_curriculum()
                # 可以根据阶段调整学习率等参数
                # 这里简化处理，实际应该调整 PPO 的学习率
            
            losses = trainer.train_step(
                batch_size=train_batch_size,
                num_epochs=train_num_epochs,
            )
            if losses:
                logger.log_training_step(iteration + 1, losses)
                # 记录到指标日志
                if metrics_logger:
                    metrics_logger.log_loss(
                        iteration + 1,
                        losses.get('policy_loss', 0.0),
                        losses.get('value_loss', 0.0),
                        losses.get('entropy_loss', 0.0),
                        losses.get('total_loss', 0.0),
                    )
        
        # 3. 评估（如果需要）
        if (iteration + 1) % eval_interval == 0:
            logger.info("Evaluating model...")
            model_id = f"iteration_{iteration + 1}"
            results = evaluator.evaluate_model(model, model_id, num_games=eval_config.get('num_eval_games', 100))
            elo_rating = evaluator.get_model_elo(model_id)
            logger.log_evaluation(iteration + 1, results, elo_rating=elo_rating)
            
            # 添加模型到对手池（如果启用）
            if collector and collector.use_opponent_pool:
                collector.add_model_to_pool(model, iteration + 1, elo_rating)
                logger.info(f"Added model to opponent pool (Elo: {elo_rating:.2f})")
            
            # 记录到指标日志
            if metrics_logger:
                metrics_logger.log_evaluation(
                    iteration + 1,
                    results.get('win_rate', 0.0),
                    results.get('avg_score', 0.0),
                    elo_rating,
                )
        
        # 4. 保存 Checkpoint（如果需要）
        if (iteration + 1) % save_interval == 0:
            logger.info("Saving checkpoint...")
            checkpoint_path = trainer.save_checkpoint(iteration + 1)
            logger.log_checkpoint(iteration + 1, checkpoint_path)
            # 保存指标
            if metrics_logger:
                metrics_logger.save()
    
    logger.info("\nTraining completed!")
    
    # 最终评估
    logger.info("Running final evaluation...")
    final_model_id = f"iteration_{num_iterations}_final"
    results = evaluator.evaluate_model(model, final_model_id, num_games=eval_config.get('num_eval_games', 100))
    final_elo_rating = evaluator.get_model_elo(final_model_id)
    logger.log_evaluation(num_iterations, results, elo_rating=final_elo_rating, final=True)
    
    # 保存最终 Checkpoint
    final_checkpoint_path = trainer.save_checkpoint(num_iterations)
    logger.log_checkpoint(num_iterations, final_checkpoint_path, final=True)
    
    # 保存最终指标
    if metrics_logger:
        metrics_logger.log_evaluation(
            num_iterations,
            results.get('win_rate', 0.0),
            results.get('avg_score', 0.0),
            final_elo_rating,
        )
        metrics_logger.save()
        logger.info(f"Metrics saved to {metrics_logger.metrics_file}")


if __name__ == '__main__':
    main()

