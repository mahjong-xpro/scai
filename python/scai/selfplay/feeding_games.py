"""
喂牌机制 (Feeding Games)

生成更容易学习的牌局，帮助AI在初期更快学会基本技能。
"""

import numpy as np
from typing import List, Optional, Tuple
import random

# 导入 Rust 游戏引擎
try:
    import scai_engine
    HAS_SCAI_ENGINE = True
except ImportError:
    HAS_SCAI_ENGINE = False


class FeedingGameGenerator:
    """喂牌游戏生成器
    
    生成更容易学习的牌局，例如：
    - 给AI一个接近听牌的手牌
    - 在牌墙中放置AI需要的牌
    - 减少对手的威胁
    """
    
    def __init__(self, difficulty: str = 'easy'):
        """
        参数：
        - difficulty: 难度级别（'easy', 'medium', 'hard'）
        """
        self.difficulty = difficulty
        self.feeding_probability = {
            'easy': 0.8,    # 80%的概率生成喂牌局
            'medium': 0.5,  # 50%的概率
            'hard': 0.2,    # 20%的概率
        }.get(difficulty, 0.5)
    
    def should_generate_feeding_game(self, feeding_rate: Optional[float] = None) -> bool:
        """
        判断是否应该生成喂牌局
        
        参数：
        - feeding_rate: 自定义喂牌概率（如果提供，优先使用此值而不是 difficulty 对应的概率）
        
        返回：
        - 是否应该生成喂牌局
        """
        if feeding_rate is not None:
            return random.random() < feeding_rate
        return random.random() < self.feeding_probability
    
    def generate_feeding_hand(
        self,
        target_player_id: int,
        win_type: str = 'basic',
    ) -> List[Tuple[int, int]]:
        """
        生成一个接近听牌或已听牌的手牌
        
        参数：
        - target_player_id: 目标玩家ID
        - win_type: 胡牌类型（'basic', 'seven_pairs', 'pure_suit'）
        
        返回：
        - 手牌列表（牌型索引，数量）
        """
        if win_type == 'seven_pairs':
            # 生成七对手牌（6对 + 1张单牌）
            hand = []
            # 随机选择6种不同的牌，每种2张
            tile_types = random.sample(range(27), 6)
            for tile_type in tile_types:
                hand.append((tile_type, 2))
            # 添加1张单牌（接近听牌）
            single_tile = random.choice([t for t in range(27) if t not in tile_types])
            hand.append((single_tile, 1))
            return hand
        
        elif win_type == 'basic':
            # 生成基本胡牌手牌（3个顺子/刻子 + 1对）
            hand = []
            # 选择一个花色
            suit = random.choice([0, 9, 18])  # 万、筒、条的起始索引
            
            # 生成3个顺子
            for _ in range(3):
                start_rank = random.randint(0, 6)  # 1-7，确保可以组成顺子
                for i in range(3):
                    tile_type = suit + start_rank + i
                    hand.append((tile_type, 1))
            
            # 生成1对
            pair_tile = suit + random.randint(0, 8)
            hand.append((pair_tile, 2))
            
            return hand
        
        elif win_type == 'pure_suit':
            # 生成清一色手牌
            suit = random.choice([0, 9, 18])
            hand = []
            # 生成多个顺子和刻子
            ranks = list(range(9))
            random.shuffle(ranks)
            
            # 3个顺子
            for i in range(3):
                start = ranks[i * 2]
                for j in range(3):
                    hand.append((suit + start + j, 1))
            
            # 1对
            hand.append((suit + ranks[6], 2))
            
            return hand
        
        else:
            # 默认：生成一个接近听牌的手牌
            return self.generate_feeding_hand(target_player_id, 'basic')
    
    def modify_wall_for_feeding(
        self,
        engine,
        target_player_id: int,
        needed_tiles: List[int],
        num_tiles: int = 3,
    ):
        """
        修改牌墙，在牌墙中放置AI需要的牌
        
        参数：
        - engine: 游戏引擎
        - target_player_id: 目标玩家ID
        - needed_tiles: 需要的牌型索引列表
        - num_tiles: 在牌墙中放置的牌数
        """
        if not HAS_SCAI_ENGINE:
            return  # 如果无法访问引擎，跳过
        
        # 注意：这需要Rust端支持修改牌墙
        # 如果Rust端不支持，可以在Python端通过重新初始化来实现
        # 这里提供一个概念性的实现
        
        # 实际实现需要：
        # 1. 在Rust端添加修改牌墙的方法
        # 2. 或者在Python端重新初始化游戏，但设置特定的牌墙顺序
        
        pass
    
    def create_feeding_game(
        self,
        target_player_id: int = 0,
        win_type: str = 'basic',
    ) -> Optional[scai_engine.PyGameEngine]:
        """
        创建一个喂牌游戏（生成更容易学习的牌局）
        
        参数：
        - target_player_id: 目标玩家ID（通常是AI玩家，0-3）
        - win_type: 胡牌类型（'basic', 'seven_pairs', 'pure_suit'）
        
        返回：
        - 游戏引擎实例（如果成功），否则返回None
        """
        if not HAS_SCAI_ENGINE:
            return None
        
        try:
            # 创建游戏引擎
            engine = scai_engine.PyGameEngine()
            engine.initialize()
            
            # 生成喂牌手牌（牌型索引，数量）
            feeding_hand = self.generate_feeding_hand(target_player_id, win_type)
            
            # 将手牌转换为Rust端需要的格式（字典：牌字符串 -> 数量）
            hand_dict = self._convert_hand_to_dict(feeding_hand)
            
            # 直接通过引擎设置手牌（PyGameEngine.set_player_hand 会自动处理 Python 解释器）
            engine.set_player_hand(target_player_id, hand_dict)
            
            return engine
        except Exception as e:
            print(f"Error creating feeding game: {e}")
            return None
    
    def _convert_hand_to_dict(self, hand: List[Tuple[int, int]]) -> dict:
        """
        将手牌列表转换为Rust端需要的字典格式
        
        参数：
        - hand: 手牌列表，每个元素是 (tile_index, count)
          tile_index: 0-26（0-8: 万1-9, 9-17: 筒1-9, 18-26: 条1-9）
        
        返回：
        - 字典，键为牌字符串（如 "Wan(1)"），值为数量
        """
        hand_dict = {}
        
        for tile_index, count in hand:
            # 将 tile_index (0-26) 转换为牌字符串
            if tile_index < 9:
                # 万 (0-8) -> Wan(1-9)
                tile_str = f"Wan({tile_index + 1})"
            elif tile_index < 18:
                # 筒 (9-17) -> Tong(1-9)
                tile_str = f"Tong({tile_index - 9 + 1})"
            else:
                # 条 (18-26) -> Tiao(1-9)
                tile_str = f"Tiao({tile_index - 18 + 1})"
            
            hand_dict[tile_str] = count
        
        return hand_dict
    
    def generate_feeding_game_with_wall(
        self,
        target_player_id: int = 0,
        win_type: str = 'basic',
        needed_tiles_in_wall: int = 2,
    ) -> Optional[scai_engine.PyGameEngine]:
        """
        生成一个喂牌游戏，并在牌墙中放置AI需要的牌
        
        参数：
        - target_player_id: 目标玩家ID
        - win_type: 胡牌类型
        - needed_tiles_in_wall: 在牌墙中放置的需要的牌数
        
        返回：
        - 游戏引擎实例
        """
        if not HAS_SCAI_ENGINE:
            return None
        
        # 创建基础喂牌游戏
        engine = self.create_feeding_game(target_player_id, win_type)
        if engine is None:
            return None
        
        # 计算AI需要的牌（用于听牌）
        feeding_hand = self.generate_feeding_hand(target_player_id, win_type)
        needed_tiles = self._calculate_needed_tiles(feeding_hand, win_type)
        
        # 注意：修改牌墙需要Rust端支持
        # 目前先实现基础版本（只设置手牌）
        # 未来可以在Rust端添加 set_wall_order() 方法来优化牌墙
        
        return engine
    
    def _calculate_needed_tiles(
        self,
        hand: List[Tuple[int, int]],
        win_type: str,
    ) -> List[int]:
        """
        计算听牌需要的牌型索引列表
        
        参数：
        - hand: 当前手牌
        - win_type: 胡牌类型
        
        返回：
        - 需要的牌型索引列表
        """
        # 简化实现：根据手牌类型推断需要的牌
        needed = []
        
        if win_type == 'seven_pairs':
            # 七对：找到单牌，需要配对
            for tile_index, count in hand:
                if count == 1:
                    needed.append(tile_index)
        elif win_type == 'basic':
            # 基本胡牌：需要组成顺子或刻子
            # 简化：返回手牌中数量为1或2的牌
            for tile_index, count in hand:
                if count <= 2:
                    needed.append(tile_index)
        
        return needed[:3]  # 最多返回3张需要的牌


class FeedingGameConfig:
    """喂牌游戏配置"""
    
    def __init__(
        self,
        enabled: bool = True,
        difficulty: str = 'easy',
        feeding_rate: float = 0.8,
        win_types: List[str] = None,
    ):
        """
        参数：
        - enabled: 是否启用喂牌
        - difficulty: 难度级别
        - feeding_rate: 喂牌概率（0.0-1.0）
        - win_types: 要学习的胡牌类型列表
        """
        self.enabled = enabled
        self.difficulty = difficulty
        self.feeding_rate = feeding_rate
        self.win_types = win_types or ['basic', 'seven_pairs']
        self.generator = FeedingGameGenerator(difficulty=difficulty)
    
    def should_use_feeding(self, iteration: int, stage: str) -> bool:
        """
        判断当前是否应该使用喂牌
        
        参数：
        - iteration: 当前迭代次数
        - stage: 当前训练阶段
        
        返回：
        - 是否应该使用喂牌
        """
        if not self.enabled:
            return False
        
        # 只在特定阶段使用喂牌
        if stage in ['LEARN_WIN', 'DECLARE_SUIT']:
            return random.random() < self.feeding_rate
        
        return False
    
    def get_feeding_hand(self, target_player_id: int, win_type: Optional[str] = None):
        """获取喂牌手牌"""
        if win_type is None:
            win_type = random.choice(self.win_types)
        return self.generator.generate_feeding_hand(target_player_id, win_type)

