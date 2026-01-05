"""
游戏日志记录器 (Game Logger)

将关键决策点序列化为结构化JSON，用于大模型分析。
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np


@dataclass
class DecisionLog:
    """决策日志
    
    记录AI在某个状态下的决策信息。
    """
    # 游戏状态（人类可读格式）
    state: str
    # 执行的动作
    action_taken: str
    # 即时奖励
    reward: float
    # 是否是危险牌（可能导致点炮）
    was_winning_tile: bool
    # 是否听牌
    is_ready: bool
    # 当前手牌（简化表示）
    hand_summary: str
    # 定缺花色
    declared_suit: str
    # 剩余牌数
    remaining_tiles: int
    # 回合数
    turn: int
    # 玩家ID
    player_id: int
    # 时间戳
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class GameLogger:
    """游戏日志记录器
    
    记录游戏过程中的关键决策点，并序列化为结构化数据。
    """
    
    def __init__(
        self,
        log_dir: str = './logs',
        max_logs_per_game: int = 100,
    ):
        """
        参数：
        - log_dir: 日志保存目录
        - max_logs_per_game: 每局游戏最多记录多少条日志
        """
        self.log_dir = log_dir
        self.max_logs_per_game = max_logs_per_game
        self.current_game_logs: List[DecisionLog] = []
        self.all_game_logs: List[List[DecisionLog]] = []
        
        # 创建日志目录
        import os
        os.makedirs(log_dir, exist_ok=True)
    
    def log_decision(
        self,
        state: Dict[str, Any],
        action: str,
        reward: float,
        was_winning_tile: bool = False,
        is_ready: bool = False,
        hand_summary: Optional[str] = None,
        declared_suit: Optional[str] = None,
        remaining_tiles: int = 0,
        turn: int = 0,
        player_id: int = 0,
    ):
        """
        记录一个决策点
        
        参数：
        - state: 游戏状态字典
        - action: 执行的动作
        - reward: 即时奖励
        - was_winning_tile: 是否是危险牌
        - is_ready: 是否听牌
        - hand_summary: 手牌摘要（人类可读格式）
        - declared_suit: 定缺花色
        - remaining_tiles: 剩余牌数
        - turn: 回合数
        - player_id: 玩家ID
        """
        if len(self.current_game_logs) >= self.max_logs_per_game:
            return  # 达到上限，不再记录
        
        # 格式化状态字符串
        state_str = self._format_state(state)
        
        # 如果没有提供手牌摘要，从状态中提取
        if hand_summary is None:
            hand_summary = self._extract_hand_summary(state)
        
        # 创建决策日志
        log = DecisionLog(
            state=state_str,
            action_taken=action,
            reward=reward,
            was_winning_tile=was_winning_tile,
            is_ready=is_ready,
            hand_summary=hand_summary or "Unknown",
            declared_suit=declared_suit or "Unknown",
            remaining_tiles=remaining_tiles,
            turn=turn,
            player_id=player_id,
            timestamp=datetime.now().isoformat(),
        )
        
        self.current_game_logs.append(log)
    
    def finish_game(self, game_id: Optional[int] = None):
        """
        结束一局游戏，保存日志
        
        参数：
        - game_id: 游戏ID（可选）
        """
        if len(self.current_game_logs) == 0:
            return
        
        # 保存到内存
        self.all_game_logs.append(self.current_game_logs.copy())
        
        # 保存到文件
        if game_id is None:
            game_id = len(self.all_game_logs) - 1
        
        self._save_game_logs(game_id, self.current_game_logs)
        
        # 清空当前游戏日志
        self.current_game_logs.clear()
    
    def get_recent_logs(self, num_games: int = 10) -> List[List[DecisionLog]]:
        """
        获取最近的游戏日志
        
        参数：
        - num_games: 获取最近多少局游戏的日志
        
        返回：
        - 游戏日志列表
        """
        return self.all_game_logs[-num_games:]
    
    def get_anomaly_logs(
        self,
        min_loss: float = 10.0,
        min_negative_reward: float = -5.0,
    ) -> List[DecisionLog]:
        """
        获取异常日志（高损失或极端负奖励）
        
        参数：
        - min_loss: 最小损失阈值
        - min_negative_reward: 最小负奖励阈值
        
        返回：
        - 异常决策日志列表
        """
        anomaly_logs = []
        
        for game_logs in self.all_game_logs:
            for log in game_logs:
                # 检查是否是异常决策
                if log.reward <= min_negative_reward:
                    anomaly_logs.append(log)
        
        return anomaly_logs
    
    def export_to_json(self, filepath: str, num_games: Optional[int] = None):
        """
        导出日志为JSON文件
        
        参数：
        - filepath: 输出文件路径
        - num_games: 导出最近多少局游戏（None表示全部）
        """
        logs_to_export = self.all_game_logs
        if num_games is not None:
            logs_to_export = logs_to_export[-num_games:]
        
        # 转换为字典列表
        export_data = {
            'total_games': len(logs_to_export),
            'games': [
                [log.to_dict() for log in game_logs]
                for game_logs in logs_to_export
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    def _format_state(self, state: Dict[str, Any]) -> str:
        """格式化游戏状态为人类可读字符串"""
        parts = []
        
        if 'hand' in state:
            parts.append(f"Hand: {state['hand']}")
        if 'declared_suit' in state:
            parts.append(f"Lack: {state['declared_suit']}")
        if 'remaining_tiles' in state:
            parts.append(f"Remaining: {state['remaining_tiles']}")
        if 'discards' in state:
            parts.append(f"Discards: {len(state['discards'])} tiles")
        if 'melds' in state:
            parts.append(f"Melds: {len(state['melds'])} groups")
        
        return ", ".join(parts) if parts else "Unknown state"
    
    def _extract_hand_summary(self, state: Dict[str, Any]) -> str:
        """从状态中提取手牌摘要"""
        if 'hand' in state:
            hand = state['hand']
            if isinstance(hand, (list, np.ndarray)):
                # 简化表示：只显示牌的数量
                return f"{len(hand)} tiles"
            elif isinstance(hand, str):
                return hand
        return "Unknown"
    
    def _save_game_logs(self, game_id: int, logs: List[DecisionLog]):
        """保存游戏日志到文件"""
        import os
        
        filepath = os.path.join(self.log_dir, f"game_{game_id:06d}.json")
        
        export_data = {
            'game_id': game_id,
            'total_decisions': len(logs),
            'decisions': [log.to_dict() for log in logs]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

