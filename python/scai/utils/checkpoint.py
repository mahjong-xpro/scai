"""
Checkpoint 管理器

管理模型检查点的保存和加载。
"""

import torch
import os
from typing import Dict, Optional
from datetime import datetime

from ..models import DualResNet


class CheckpointManager:
    """Checkpoint 管理器
    
    管理模型检查点的保存和加载。
    """
    
    def __init__(self, checkpoint_dir: str = './checkpoints'):
        """
        参数：
        - checkpoint_dir: Checkpoint 保存目录
        """
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
    
    def save_checkpoint(
        self,
        model: DualResNet,
        optimizer: torch.optim.Optimizer,
        iteration: int,
        training_stats: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        保存 Checkpoint
        
        参数：
        - model: 模型
        - optimizer: 优化器
        - iteration: 迭代次数
        - training_stats: 训练统计信息（可选）
        - metadata: 元数据（可选）
        
        返回：
        - Checkpoint 文件路径
        """
        checkpoint = {
            'iteration': iteration,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'training_stats': training_stats or {},
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
        }
        
        # 生成文件名
        filename = f'checkpoint_iter_{iteration}.pt'
        filepath = os.path.join(self.checkpoint_dir, filename)
        
        # 保存
        torch.save(checkpoint, filepath)
        
        # 同时保存最新版本
        latest_path = os.path.join(self.checkpoint_dir, 'latest.pt')
        torch.save(checkpoint, latest_path)
        
        return filepath
    
    def load_checkpoint(
        self,
        checkpoint_path: str,
        model: Optional[DualResNet] = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
        device: str = 'cpu',
        strict: bool = True,
    ) -> Dict:
        """
        加载 Checkpoint
        
        参数：
        - checkpoint_path: Checkpoint 文件路径
        - model: 模型（可选，如果提供则加载状态）
        - optimizer: 优化器（可选，如果提供则加载状态）
        - device: 设备（'cpu' 或 'cuda'）
        - strict: 是否严格匹配模型参数（默认 True）
        
        返回：
        - Checkpoint 字典
        
        抛出：
        - FileNotFoundError: 如果文件不存在
        - KeyError: 如果 Checkpoint 缺少必需字段
        """
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_path}")
        
        try:
            checkpoint = torch.load(checkpoint_path, map_location=device)
        except Exception as e:
            raise RuntimeError(f"Failed to load checkpoint: {e}") from e
        
        # 验证必需字段
        required_fields = ['iteration', 'model_state_dict', 'optimizer_state_dict']
        for field in required_fields:
            if field not in checkpoint:
                raise KeyError(f"Checkpoint missing required field: {field}")
        
        # 加载模型状态
        if model is not None:
            try:
                model.load_state_dict(checkpoint['model_state_dict'], strict=strict)
            except Exception as e:
                if strict:
                    raise RuntimeError(f"Failed to load model state: {e}") from e
                else:
                    # 非严格模式：只加载匹配的参数
                    model_dict = model.state_dict()
                    checkpoint_dict = checkpoint['model_state_dict']
                    matched = {k: v for k, v in checkpoint_dict.items() if k in model_dict}
                    model_dict.update(matched)
                    model.load_state_dict(model_dict, strict=False)
        
        # 加载优化器状态
        if optimizer is not None:
            try:
                optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            except Exception as e:
                raise RuntimeError(f"Failed to load optimizer state: {e}") from e
        
        return checkpoint
    
    def verify_checkpoint(self, checkpoint_path: str) -> Dict[str, bool]:
        """
        验证 Checkpoint 的完整性
        
        参数：
        - checkpoint_path: Checkpoint 文件路径
        
        返回：
        - 包含验证结果的字典
        """
        result = {
            'exists': False,
            'readable': False,
            'has_required_fields': False,
            'has_model_state': False,
            'has_optimizer_state': False,
            'has_training_stats': False,
            'has_metadata': False,
            'has_timestamp': False,
        }
        
        # 检查文件是否存在
        if not os.path.exists(checkpoint_path):
            return result
        
        result['exists'] = True
        
        try:
            # 尝试加载
            checkpoint = torch.load(checkpoint_path, map_location='cpu')
            result['readable'] = True
            
            # 检查必需字段
            required_fields = ['iteration', 'model_state_dict', 'optimizer_state_dict']
            result['has_required_fields'] = all(field in checkpoint for field in required_fields)
            
            # 检查各个字段
            result['has_model_state'] = 'model_state_dict' in checkpoint and len(checkpoint['model_state_dict']) > 0
            result['has_optimizer_state'] = 'optimizer_state_dict' in checkpoint and len(checkpoint['optimizer_state_dict']) > 0
            result['has_training_stats'] = 'training_stats' in checkpoint
            result['has_metadata'] = 'metadata' in checkpoint
            result['has_timestamp'] = 'timestamp' in checkpoint
            
        except Exception:
            pass
        
        return result
    
    def list_checkpoints(self) -> list:
        """
        列出所有 Checkpoint
        
        返回：
        - Checkpoint 文件路径列表
        """
        checkpoints = []
        for filename in os.listdir(self.checkpoint_dir):
            if filename.endswith('.pt') and filename.startswith('checkpoint_iter_'):
                filepath = os.path.join(self.checkpoint_dir, filename)
                checkpoints.append(filepath)
        
        # 按迭代次数排序
        checkpoints.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
        
        return checkpoints
    
    def get_latest_checkpoint(self) -> Optional[str]:
        """
        获取最新的 Checkpoint
        
        返回：
        - 最新 Checkpoint 文件路径，如果没有则返回 None
        """
        latest_path = os.path.join(self.checkpoint_dir, 'latest.pt')
        if os.path.exists(latest_path):
            return latest_path
        
        checkpoints = self.list_checkpoints()
        if len(checkpoints) > 0:
            return checkpoints[-1]
        
        return None

