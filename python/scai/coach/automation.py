"""
自动化反馈机制 (Automation)

定期生成训练报告和文档，供手动提交给大模型进行分析。
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from .logger import GameLogger
from .document_generator import TrainingDocumentGenerator


class ReportGenerator:
    """训练报告生成器"""
    
    def __init__(self, report_dir: str = './reports'):
        """
        参数：
        - report_dir: 报告保存目录
        """
        self.report_dir = report_dir
        os.makedirs(report_dir, exist_ok=True)
    
    def generate_training_report(
        self,
        iteration: int,
        training_stats: Dict[str, Any],
        loss_history: List[float],
        elo_scores: List[float],
        reward_config: Dict[str, Any],
        anomaly_logs: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成训练报告
        
        参数：
        - iteration: 当前迭代次数
        - training_stats: 训练统计信息
        - loss_history: 损失历史
        - elo_scores: Elo分数历史
        - reward_config: 奖励函数配置
        - anomaly_logs: 异常日志（可选）
        
        返回：
        - 报告字典
        """
        report = {
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'training_stats': training_stats,
            'loss_summary': {
                'current': loss_history[-1] if loss_history else 0.0,
                'average': sum(loss_history[-100:]) / len(loss_history[-100:]) if loss_history else 0.0,
                'trend': self._calculate_trend(loss_history[-20:]) if len(loss_history) >= 20 else 'unknown',
            },
            'elo_summary': {
                'current': elo_scores[-1] if elo_scores else 0.0,
                'average': sum(elo_scores[-10:]) / len(elo_scores[-10:]) if elo_scores else 0.0,
                'trend': self._calculate_trend(elo_scores[-10:]) if len(elo_scores) >= 10 else 'unknown',
            },
            'reward_config': reward_config,
            'anomaly_count': len(anomaly_logs) if anomaly_logs else 0,
            'anomaly_samples': [
                {
                    'state': log.state,
                    'action': log.action_taken,
                    'reward': log.reward,
                }
                for log in (anomaly_logs[:5] if anomaly_logs else [])
            ],
        }
        
        # 保存报告
        report_path = os.path.join(self.report_dir, f"report_{iteration:06d}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return 'unknown'
        
        recent_avg = sum(values[-5:]) / len(values[-5:])
        earlier_avg = sum(values[:5]) / len(values[:5])
        
        if recent_avg > earlier_avg * 1.1:
            return 'improving'
        elif recent_avg < earlier_avg * 0.9:
            return 'declining'
        else:
            return 'stable'


class TrainingMonitor:
    """训练监控器
    
    定期监控训练过程，生成报告和文档供手动分析。
    """
    
    def __init__(
        self,
        logger: GameLogger,
        document_generator: TrainingDocumentGenerator,
        report_generator: ReportGenerator,
        check_interval: int = 1000,
    ):
        """
        参数：
        - logger: 游戏日志记录器
        - document_generator: 文档生成器
        - report_generator: 报告生成器
        - check_interval: 检查间隔（每N个epoch检查一次）
        """
        self.logger = logger
        self.document_generator = document_generator
        self.report_generator = report_generator
        self.check_interval = check_interval
        
        # 训练历史
        self.loss_history: List[float] = []
        self.elo_scores: List[float] = []
        self.reward_config_history: List[Dict[str, Any]] = []
    
    def update_metrics(
        self,
        loss: float,
        elo_score: Optional[float] = None,
        reward_config: Optional[Dict[str, Any]] = None,
    ):
        """
        更新训练指标
        
        参数：
        - loss: 当前损失
        - elo_score: 当前Elo分数（可选）
        - reward_config: 当前奖励函数配置（可选）
        """
        self.loss_history.append(loss)
        if elo_score is not None:
            self.elo_scores.append(elo_score)
        if reward_config is not None:
            self.reward_config_history.append(reward_config)
    
    def check_and_generate_documents(
        self,
        iteration: int,
        training_stats: Dict[str, Any],
        reward_config: Dict[str, Any],
    ) -> Optional[Dict[str, str]]:
        """
        检查是否需要生成文档，如果需要则生成分析文档
        
        参数：
        - iteration: 当前迭代次数
        - training_stats: 训练统计信息
        - reward_config: 奖励函数配置
        
        返回：
        - 文档路径字典（如果生成了文档），否则返回None
        """
        if iteration % self.check_interval != 0:
            return None
        
        print(f"[TrainingMonitor] 迭代 {iteration}: 生成报告和分析文档...")
        
        # 获取异常日志
        anomaly_logs = self.logger.get_anomaly_logs(
            min_negative_reward=-5.0,
        )
        
        # 生成训练报告
        report = self.report_generator.generate_training_report(
            iteration=iteration,
            training_stats=training_stats,
            loss_history=self.loss_history,
            elo_scores=self.elo_scores,
            reward_config=reward_config,
            anomaly_logs=anomaly_logs,
        )
        
        # 获取最近的游戏日志
        recent_logs = self.logger.get_recent_logs(num_games=10)
        
        # 转换为字典格式
        game_logs_dict = [
            [log.to_dict() for log in game_logs]
            for game_logs in recent_logs
        ]
        
        # 计算性能指标
        performance_metrics = {
            'iteration': iteration,
            'avg_score': training_stats.get('avg_score', 0.0),
            'win_rate': training_stats.get('win_rate', 0.0),
            'elo_rating': self.elo_scores[-1] if self.elo_scores else 0.0,
        }
        
        # 生成策略分析文档
        strategy_doc_path = self.document_generator.generate_strategy_analysis_document(
            game_logs=game_logs_dict,
            performance_metrics=performance_metrics,
            focus_anomalies=True,
            iteration=iteration,
        )
        
        # 提取行为问题（从异常日志中）
        behavior_issues = [
            f"异常决策: {log.action_taken}, 奖励: {log.reward}"
            for log in anomaly_logs[:5]
        ]
        
        # 生成奖励函数评价文档
        reward_doc_path = self.document_generator.generate_reward_evaluation_document(
            reward_config=reward_config,
            loss_curve=self.loss_history,
            elo_scores=self.elo_scores,
            behavior_issues=behavior_issues if behavior_issues else None,
            iteration=iteration,
        )
        
        # 返回文档路径
        doc_paths = {
            'strategy_analysis': strategy_doc_path,
            'reward_evaluation': reward_doc_path,
            'report': os.path.join(
                self.report_generator.report_dir,
                f"report_{iteration:06d}.json"
            ),
        }
        
        print(f"[TrainingMonitor] 文档生成完成:")
        print(f"  - 策略分析文档: {strategy_doc_path}")
        print(f"  - 奖励函数评价文档: {reward_doc_path}")
        print(f"  - 训练报告: {doc_paths['report']}")
        print(f"  请手动将这些文档提交给大模型进行分析。")
        
        return doc_paths
    
    def get_latest_analysis(self) -> Optional[Dict[str, Any]]:
        """获取最新的分析结果"""
        analysis_files = sorted(
            Path(self.report_generator.report_dir).glob("analysis_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        
        if not analysis_files:
            return None
        
        with open(analysis_files[0], 'r', encoding='utf-8') as f:
            return json.load(f)

