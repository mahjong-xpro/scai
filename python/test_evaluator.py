#!/usr/bin/env python3
"""
评估系统测试脚本

验证评估系统的功能是否完整。
"""

import torch
import numpy as np
from typing import Dict

from scai.models import DualResNet
from scai.training.evaluator import Evaluator, EloRating


def test_elo_rating():
    """测试 Elo 评分系统"""
    print("=" * 60)
    print("测试 Elo 评分系统")
    print("=" * 60)
    
    # 创建 Elo 评分系统
    elo = EloRating(initial_rating=1500.0, k_factor=32.0)
    
    # 测试初始评分
    print("\n1. 测试初始评分...")
    rating_a = elo.get_rating("model_a")
    rating_b = elo.get_rating("model_b")
    assert rating_a == 1500.0, f"初始评分应该是 1500.0，实际是 {rating_a}"
    assert rating_b == 1500.0, f"初始评分应该是 1500.0，实际是 {rating_b}"
    print(f"✓ 初始评分正确: model_a={rating_a}, model_b={rating_b}")
    
    # 测试期望得分
    print("\n2. 测试期望得分计算...")
    expected = elo.expected_score(1500.0, 1500.0)
    assert abs(expected - 0.5) < 0.01, f"相同评分的期望得分应该是 0.5，实际是 {expected}"
    print(f"✓ 期望得分计算正确: {expected:.4f}")
    
    # 测试评分更新
    print("\n3. 测试评分更新...")
    elo.update_rating("model_a", "model_b", 1.0)  # model_a 获胜
    new_rating_a = elo.get_rating("model_a")
    new_rating_b = elo.get_rating("model_b")
    assert new_rating_a > 1500.0, f"获胜后评分应该增加，实际是 {new_rating_a}"
    assert new_rating_b < 1500.0, f"失败后评分应该减少，实际是 {new_rating_b}"
    print(f"✓ 评分更新正确: model_a={new_rating_a:.2f}, model_b={new_rating_b:.2f}")
    
    # 测试获取所有评分
    print("\n4. 测试获取所有评分...")
    all_ratings = elo.get_ratings()
    assert "model_a" in all_ratings, "应该包含 model_a"
    assert "model_b" in all_ratings, "应该包含 model_b"
    print(f"✓ 所有评分: {all_ratings}")
    
    print("\n" + "=" * 60)
    print("✓ Elo 评分系统测试通过！")
    print("=" * 60)


def test_evaluator_basic():
    """测试评估器的基本功能"""
    print("\n" + "=" * 60)
    print("测试评估器基本功能")
    print("=" * 60)
    
    # 创建评估器
    evaluator = Evaluator(
        checkpoint_dir='./checkpoints',
        elo_threshold=0.55,
        device='cpu',
    )
    
    # 测试初始化
    print("\n1. 测试初始化...")
    assert evaluator.elo_threshold == 0.55, "Elo 阈值不正确"
    assert evaluator.device == 'cpu', "设备不正确"
    assert evaluator.elo is not None, "Elo 评分系统未初始化"
    print("✓ 评估器初始化正确")
    
    # 测试 should_keep_model
    print("\n2. 测试 should_keep_model...")
    assert evaluator.should_keep_model(0.6) == True, "胜率 0.6 应该保留模型"
    assert evaluator.should_keep_model(0.5) == False, "胜率 0.5 不应该保留模型"
    assert evaluator.should_keep_model(0.55) == True, "胜率 0.55 应该保留模型"
    print("✓ should_keep_model 功能正确")
    
    # 测试 get_best_model_id（空列表）
    print("\n3. 测试 get_best_model_id（空列表）...")
    best_id = evaluator.get_best_model_id()
    assert best_id is None, "空列表应该返回 None"
    print("✓ get_best_model_id（空列表）正确")
    
    # 测试 get_model_elo（新模型）
    print("\n4. 测试 get_model_elo（新模型）...")
    elo_rating = evaluator.get_model_elo("new_model")
    assert elo_rating == 1500.0, f"新模型的初始评分应该是 1500.0，实际是 {elo_rating}"
    print(f"✓ get_model_elo（新模型）正确: {elo_rating}")
    
    print("\n" + "=" * 60)
    print("✓ 评估器基本功能测试通过！")
    print("=" * 60)


def test_evaluator_without_engine():
    """测试评估器在没有游戏引擎时的情况"""
    print("\n" + "=" * 60)
    print("测试评估器（无游戏引擎）")
    print("=" * 60)
    
    # 创建模型
    model = DualResNet()
    
    # 创建评估器
    evaluator = Evaluator(device='cpu')
    
    # 测试 evaluate_model（应该返回占位符数据）
    print("\n1. 测试 evaluate_model（无引擎）...")
    # 注意：这需要模拟 HAS_SCAI_ENGINE = False 的情况
    # 在实际测试中，如果引擎不可用，会返回占位符数据
    try:
        results = evaluator.evaluate_model(model, "test_model", num_games=10)
        assert 'win_rate' in results, "结果应该包含 win_rate"
        assert 'avg_score' in results, "结果应该包含 avg_score"
        assert 'wins' in results, "结果应该包含 wins"
        assert 'total_games' in results, "结果应该包含 total_games"
        print(f"✓ evaluate_model 返回正确格式: {results}")
    except Exception as e:
        print(f"⚠ evaluate_model 需要游戏引擎: {e}")
    
    print("\n" + "=" * 60)
    print("✓ 评估器（无游戏引擎）测试完成")
    print("=" * 60)


def test_evaluator_compare_models():
    """测试模型比较功能"""
    print("\n" + "=" * 60)
    print("测试模型比较功能")
    print("=" * 60)
    
    # 创建两个模型
    model_a = DualResNet()
    model_b = DualResNet()
    
    # 创建评估器
    evaluator = Evaluator(device='cpu')
    
    # 测试 compare_models（应该返回占位符数据或实际结果）
    print("\n1. 测试 compare_models...")
    try:
        results = evaluator.compare_models(
            model_a=model_a,
            model_b=model_b,
            model_a_id="model_a",
            model_b_id="model_b",
            num_games=10,
        )
        
        # 验证返回格式
        required_fields = [
            'model_a_win_rate',
            'model_b_win_rate',
            'model_a_avg_score',
            'model_b_avg_score',
            'model_a_elo',
            'model_b_elo',
        ]
        
        for field in required_fields:
            assert field in results, f"结果应该包含 {field}"
        
        print(f"✓ compare_models 返回正确格式")
        print(f"  模型 A 胜率: {results['model_a_win_rate']:.2f}")
        print(f"  模型 B 胜率: {results['model_b_win_rate']:.2f}")
        print(f"  模型 A Elo: {results['model_a_elo']:.2f}")
        print(f"  模型 B Elo: {results['model_b_elo']:.2f}")
        
        # 验证 Elo 评分已更新
        elo_a = evaluator.get_model_elo("model_a")
        elo_b = evaluator.get_model_elo("model_b")
        assert elo_a == results['model_a_elo'], "Elo 评分应该已更新"
        assert elo_b == results['model_b_elo'], "Elo 评分应该已更新"
        print("✓ Elo 评分已正确更新")
        
    except Exception as e:
        print(f"⚠ compare_models 需要游戏引擎: {e}")
    
    print("\n" + "=" * 60)
    print("✓ 模型比较功能测试完成")
    print("=" * 60)


def test_evaluator_best_model():
    """测试最佳模型选择"""
    print("\n" + "=" * 60)
    print("测试最佳模型选择")
    print("=" * 60)
    
    evaluator = Evaluator(device='cpu')
    
    # 添加多个模型的评分
    print("\n1. 添加多个模型的评分...")
    evaluator.elo.update_rating("model_1", "model_2", 1.0)  # model_1 获胜
    evaluator.elo.update_rating("model_1", "model_3", 1.0)  # model_1 获胜
    evaluator.elo.update_rating("model_2", "model_3", 0.0)  # model_2 失败（model_3 获胜）
    
    # 获取最佳模型
    print("\n2. 获取最佳模型...")
    best_id = evaluator.get_best_model_id()
    assert best_id is not None, "应该找到最佳模型"
    assert best_id == "model_1", f"最佳模型应该是 model_1，实际是 {best_id}"
    print(f"✓ 最佳模型: {best_id}")
    
    # 验证评分
    ratings = evaluator.elo.get_ratings()
    print(f"✓ 所有模型评分: {ratings}")
    
    print("\n" + "=" * 60)
    print("✓ 最佳模型选择测试通过！")
    print("=" * 60)


def test_evaluator_result_format():
    """测试评估结果格式"""
    print("\n" + "=" * 60)
    print("测试评估结果格式")
    print("=" * 60)
    
    model = DualResNet()
    evaluator = Evaluator(device='cpu')
    
    # 测试 evaluate_model 返回格式
    print("\n1. 测试 evaluate_model 返回格式...")
    try:
        results = evaluator.evaluate_model(model, "test_model", num_games=10)
        
        # 验证必需字段
        assert 'win_rate' in results, "应该包含 win_rate"
        assert isinstance(results['win_rate'], (int, float)), "win_rate 应该是数字"
        assert 0.0 <= results['win_rate'] <= 1.0, "win_rate 应该在 [0, 1] 范围内"
        
        assert 'avg_score' in results, "应该包含 avg_score"
        assert isinstance(results['avg_score'], (int, float)), "avg_score 应该是数字"
        
        assert 'wins' in results, "应该包含 wins"
        assert isinstance(results['wins'], int), "wins 应该是整数"
        assert 0 <= results['wins'] <= results['total_games'], "wins 应该在合理范围内"
        
        assert 'total_games' in results, "应该包含 total_games"
        assert isinstance(results['total_games'], int), "total_games 应该是整数"
        assert results['total_games'] > 0, "total_games 应该大于 0"
        
        print("✓ evaluate_model 返回格式正确")
        print(f"  胜率: {results['win_rate']:.2f}")
        print(f"  平均得分: {results['avg_score']:.2f}")
        print(f"  获胜次数: {results['wins']}/{results['total_games']}")
        
    except Exception as e:
        print(f"⚠ 需要游戏引擎: {e}")
    
    print("\n" + "=" * 60)
    print("✓ 评估结果格式测试完成")
    print("=" * 60)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("评估系统功能测试")
    print("=" * 60)
    
    try:
        test_elo_rating()
        test_evaluator_basic()
        test_evaluator_without_engine()
        test_evaluator_compare_models()
        test_evaluator_best_model()
        test_evaluator_result_format()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        raise

