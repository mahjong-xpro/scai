"""
日志系统 (Logging System)

提供完整的日志记录功能，包括：
- 统一的日志配置
- 多级别日志支持（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- 文件和控制台输出
- 结构化日志（可选 JSON 格式）
- 训练指标记录
- 性能指标记录
"""

import logging
import os
import json
from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import sys


class TrainingLogger:
    """训练日志记录器
    
    提供结构化的训练日志记录功能。
    """
    
    def __init__(
        self,
        log_dir: str = './logs',
        log_level: str = 'INFO',
        use_json: bool = False,
        console_output: bool = True,
    ):
        """
        参数：
        - log_dir: 日志文件保存目录
        - log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        - use_json: 是否使用 JSON 格式（默认 False，使用文本格式）
        - console_output: 是否输出到控制台（默认 True）
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.use_json = use_json
        self.console_output = console_output
        
        # 创建主日志记录器
        self.logger = logging.getLogger('scai.training')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.handlers.clear()  # 清除现有处理器
        
        # 创建日志格式
        if use_json:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # 文件处理器
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.log_dir / f'training_{timestamp}.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level.upper()))
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 错误日志文件（单独记录 ERROR 和 CRITICAL）
        error_log_file = self.log_dir / f'errors_{timestamp}.log'
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        self.log_file = log_file
        self.error_log_file = error_log_file
    
    def debug(self, message: str, **kwargs):
        """记录 DEBUG 级别日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """记录 INFO 级别日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录 WARNING 级别日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录 ERROR 级别日志"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录 CRITICAL 级别日志"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """内部日志记录方法"""
        if self.use_json:
            # JSON 格式：将额外参数作为 JSON 字段
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'level': logging.getLevelName(level),
                'message': message,
                **kwargs
            }
            self.logger.log(level, json.dumps(log_data, ensure_ascii=False))
        else:
            # 文本格式：将额外参数附加到消息
            if kwargs:
                extra_info = ', '.join(f'{k}={v}' for k, v in kwargs.items())
                message = f'{message} ({extra_info})'
            self.logger.log(level, message)
    
    def log_training_step(
        self,
        iteration: int,
        losses: Dict[str, float],
        **kwargs
    ):
        """记录训练步骤
        
        参数：
        - iteration: 迭代次数
        - losses: 损失字典
        - **kwargs: 其他指标
        """
        self.info(
            f"Training step {iteration}",
            iteration=iteration,
            **losses,
            **kwargs
        )
    
    def log_evaluation(
        self,
        iteration: int,
        results: Dict[str, float],
        **kwargs
    ):
        """记录评估结果
        
        参数：
        - iteration: 迭代次数
        - results: 评估结果字典
        - **kwargs: 其他指标
        """
        self.info(
            f"Evaluation at iteration {iteration}",
            iteration=iteration,
            **results,
            **kwargs
        )
    
    def log_data_collection(
        self,
        iteration: int,
        stats: Dict[str, int],
        **kwargs
    ):
        """记录数据收集统计
        
        参数：
        - iteration: 迭代次数
        - stats: 统计信息字典
        - **kwargs: 其他指标
        """
        self.info(
            f"Data collection at iteration {iteration}",
            iteration=iteration,
            **stats,
            **kwargs
        )
    
    def log_checkpoint(
        self,
        iteration: int,
        checkpoint_path: str,
        **kwargs
    ):
        """记录 Checkpoint 保存
        
        参数：
        - iteration: 迭代次数
        - checkpoint_path: Checkpoint 文件路径
        - **kwargs: 其他信息
        """
        self.info(
            f"Checkpoint saved at iteration {iteration}",
            iteration=iteration,
            checkpoint_path=checkpoint_path,
            **kwargs
        )
    
    def log_performance(
        self,
        metric: str,
        value: float,
        unit: str = '',
        **kwargs
    ):
        """记录性能指标
        
        参数：
        - metric: 指标名称
        - value: 指标值
        - unit: 单位（可选）
        - **kwargs: 其他信息
        """
        self.info(
            f"Performance: {metric} = {value}{unit}",
            metric=metric,
            value=value,
            unit=unit,
            **kwargs
        )


class JsonFormatter(logging.Formatter):
    """JSON 格式日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 如果有异常信息，添加异常详情
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class MetricsLogger:
    """训练指标记录器
    
    专门用于记录训练过程中的指标，支持导出为 CSV 或 JSON。
    """
    
    def __init__(self, log_dir: str = './logs'):
        """
        参数：
        - log_dir: 日志文件保存目录
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 指标存储
        self.metrics = {
            'iterations': [],
            'losses': [],
            'evaluations': [],
            'performance': [],
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.metrics_file = self.log_dir / f'metrics_{timestamp}.json'
    
    def log_loss(
        self,
        iteration: int,
        policy_loss: float,
        value_loss: float,
        entropy_loss: float,
        total_loss: float,
    ):
        """记录损失值"""
        self.metrics['losses'].append({
            'iteration': iteration,
            'policy_loss': policy_loss,
            'value_loss': value_loss,
            'entropy_loss': entropy_loss,
            'total_loss': total_loss,
            'timestamp': datetime.now().isoformat(),
        })
    
    def log_evaluation(
        self,
        iteration: int,
        win_rate: float,
        avg_score: float,
        elo_rating: float,
        **kwargs
    ):
        """记录评估结果"""
        self.metrics['evaluations'].append({
            'iteration': iteration,
            'win_rate': win_rate,
            'avg_score': avg_score,
            'elo_rating': elo_rating,
            **kwargs,
            'timestamp': datetime.now().isoformat(),
        })
    
    def log_performance(
        self,
        iteration: int,
        games_per_second: float,
        steps_per_second: float,
        **kwargs
    ):
        """记录性能指标"""
        self.metrics['performance'].append({
            'iteration': iteration,
            'games_per_second': games_per_second,
            'steps_per_second': steps_per_second,
            **kwargs,
            'timestamp': datetime.now().isoformat(),
        })
    
    def save(self):
        """保存指标到文件"""
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
    
    def load(self, metrics_file: Optional[str] = None):
        """从文件加载指标"""
        if metrics_file is None:
            metrics_file = self.metrics_file
        else:
            metrics_file = Path(metrics_file)
        
        if metrics_file.exists():
            with open(metrics_file, 'r', encoding='utf-8') as f:
                self.metrics = json.load(f)
            return True
        return False


# 全局日志记录器实例（延迟初始化）
_global_logger: Optional[TrainingLogger] = None
_global_metrics_logger: Optional[MetricsLogger] = None


def get_logger(
    log_dir: str = './logs',
    log_level: str = 'INFO',
    use_json: bool = False,
    console_output: bool = True,
) -> TrainingLogger:
    """获取全局日志记录器
    
    参数：
    - log_dir: 日志文件保存目录
    - log_level: 日志级别
    - use_json: 是否使用 JSON 格式
    - console_output: 是否输出到控制台
    
    返回：
    - TrainingLogger 实例
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = TrainingLogger(
            log_dir=log_dir,
            log_level=log_level,
            use_json=use_json,
            console_output=console_output,
        )
    return _global_logger


def get_metrics_logger(log_dir: str = './logs') -> MetricsLogger:
    """获取全局指标记录器
    
    参数：
    - log_dir: 日志文件保存目录
    
    返回：
    - MetricsLogger 实例
    """
    global _global_metrics_logger
    if _global_metrics_logger is None:
        _global_metrics_logger = MetricsLogger(log_dir=log_dir)
    return _global_metrics_logger


def reset_loggers():
    """重置全局日志记录器（用于测试）"""
    global _global_logger, _global_metrics_logger
    _global_logger = None
    _global_metrics_logger = None

