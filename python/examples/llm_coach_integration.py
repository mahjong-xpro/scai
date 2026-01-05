"""
大模型总教练集成示例

展示如何将大模型总教练集成到训练循环中。
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scai.coach import (
    GameLogger,
    LLMCoach,
    LLMCoachConfig,
    TrainingMonitor,
    ReportGenerator,
    CurriculumLearning,
)
from scai.training import Trainer, PPO, RewardShaping
from scai.models import DualResNet
from scai.training.buffer import ReplayBuffer


def main():
    """主函数：演示大模型总教练的集成"""
    
    # 1. 初始化组件
    print("初始化组件...")
    
    # 游戏日志记录器
    logger = GameLogger(log_dir='./logs')
    
    # 大模型教练（需要配置API密钥）
    llm_config = LLMCoachConfig(
        api_type='openai',  # 或 'anthropic'
        model_name='gpt-4',
        api_key=os.getenv('OPENAI_API_KEY'),  # 从环境变量读取
    )
    llm_coach = LLMCoach(config=llm_config)
    
    # 报告生成器
    report_generator = ReportGenerator(report_dir='./reports')
    
    # 训练监控器
    monitor = TrainingMonitor(
        logger=logger,
        llm_coach=llm_coach,
        report_generator=report_generator,
        check_interval=1000,  # 每1000个epoch检查一次
    )
    
    # 课程学习规划器
    curriculum = CurriculumLearning(llm_coach=llm_coach)
    
    # 2. 模拟训练循环
    print("开始模拟训练...")
    
    # 初始化模型和训练器（这里只是示例，实际需要完整的初始化）
    # model = DualResNet()
    # buffer = ReplayBuffer(capacity=100000)
    # ppo = PPO(model)
    # reward_shaping = RewardShaping()
    # trainer = Trainer(model, buffer, ppo, reward_shaping)
    
    # 模拟训练过程
    for iteration in range(5000):
        # 模拟游戏决策
        # 这里应该从实际的游戏引擎获取状态和动作
        logger.log_decision(
            state={
                'hand': '1W 2W 3W 4T 5T',
                'declared_suit': 'Tong',
                'remaining_tiles': 50,
            },
            action='Discard 3W',
            reward=-2.0,
            was_winning_tile=False,
            is_ready=True,
            hand_summary='1W 2W 3W 4T 5T',
            declared_suit='Tong',
            remaining_tiles=50,
            turn=iteration % 100,
            player_id=0,
        )
        
        # 每100步结束一局游戏
        if iteration % 100 == 0:
            logger.finish_game(game_id=iteration // 100)
        
        # 更新训练指标（模拟）
        current_loss = 0.5 + 0.1 * (iteration % 100) / 100
        current_elo = 1200 + iteration * 0.1
        
        monitor.update_metrics(
            loss=current_loss,
            elo_score=current_elo,
            reward_config={
                'ready_reward': 0.1,
                'hu_reward': 1.0,
                'flower_pig_penalty': -5.0,
            },
        )
        
        # 检查并分析（每1000次迭代）
        if iteration % 1000 == 0 and iteration > 0:
            analysis = monitor.check_and_analyze(
                iteration=iteration,
                training_stats={
                    'total_games': iteration // 100,
                    'total_steps': iteration,
                },
                reward_config={
                    'ready_reward': 0.1,
                    'hu_reward': 1.0,
                    'flower_pig_penalty': -5.0,
                },
            )
            
            if analysis:
                print(f"\n[迭代 {iteration}] 大模型分析结果:")
                print(f"策略问题: {analysis['strategy_analysis'].get('issues', [])[:3]}")
                print(f"改进建议: {analysis['strategy_analysis'].get('suggestions', [])[:3]}")
        
        # 检查课程学习进度
        if iteration % 2000 == 0 and iteration > 0:
            performance_metrics = {
                'win_rate': 0.35 + (iteration / 10000) * 0.1,
                'elo_score': current_elo,
                'flower_pig_rate': 0.03,
            }
            
            if curriculum.should_advance_stage(performance_metrics):
                print(f"\n[迭代 {iteration}] 满足进入下一阶段的条件")
                next_stage = curriculum.design_next_stage(
                    performance_metrics=performance_metrics,
                    current_issues=['需要提高胜率', '需要优化策略'],
                )
                curriculum.advance_to_next_stage()
                print(f"进入新阶段: {next_stage.name}")
    
    print("\n训练完成！")
    print(f"日志保存在: {logger.log_dir}")
    print(f"报告保存在: {report_generator.report_dir}")


if __name__ == '__main__':
    main()

