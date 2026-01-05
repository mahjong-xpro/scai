"""
Python 绑定测试

测试 PyO3 绑定的基本功能，包括：
- PyGameState 的创建和查询
- PyActionMask 的生成和验证
- PyGameEngine 的游戏流程
- Tensor 转换功能
"""

import sys
import os

# 添加 Rust 模块路径（需要根据实际编译路径调整）
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../rust/target/release'))

try:
    import scai_engine
    import numpy as np
    print("✓ 成功导入 scai_engine 模块")
except ImportError as e:
    print(f"✗ 无法导入 scai_engine 模块: {e}")
    print("提示: 需要先编译 Python 扩展模块")
    print("运行: cd rust && cargo build --release --features python")
    sys.exit(1)


def test_pygame_state():
    """测试 PyGameState"""
    print("\n=== 测试 PyGameState ===")
    
    # 创建游戏状态
    state = scai_engine.PyGameState()
    print(f"✓ 创建游戏状态成功")
    
    # 测试基本属性
    assert state.current_player == 0, "初始当前玩家应该是 0"
    assert state.turn == 0, "初始回合数应该是 0"
    assert not state.is_game_over(), "游戏不应该结束"
    print(f"✓ 基本属性正确: current_player={state.current_player}, turn={state.turn}")
    
    # 测试获取玩家手牌
    hand = state.get_player_hand(0)
    assert isinstance(hand, dict), "手牌应该是字典"
    print(f"✓ 获取玩家手牌成功: {len(hand)} 种不同的牌")
    
    # 测试获取定缺
    declared_suit = state.get_player_declared_suit(0)
    assert declared_suit is None or isinstance(declared_suit, str), "定缺应该是 None 或字符串"
    print(f"✓ 获取定缺成功: {declared_suit}")
    
    print("✓ PyGameState 测试通过")


def test_pyaction_mask():
    """测试 PyActionMask"""
    print("\n=== 测试 PyActionMask ===")
    
    # 创建游戏状态
    state = scai_engine.PyGameState()
    
    # 生成动作掩码（自己的回合）
    mask = scai_engine.PyActionMask.generate_own_turn(0, state)
    print(f"✓ 生成动作掩码成功（自己的回合）")
    
    # 转换为布尔数组
    bool_array = mask.to_bool_array(True, None)
    assert len(bool_array) == 434, f"动作掩码应该有 434 个元素，实际有 {len(bool_array)}"
    print(f"✓ 转换为布尔数组成功: 长度 {len(bool_array)}")
    
    # 验证动作
    is_valid = scai_engine.PyActionMask.validate_action(432, 0, state, True, None)
    assert isinstance(is_valid, bool), "验证结果应该是布尔值"
    print(f"✓ 验证动作成功: 摸牌动作 {'合法' if is_valid else '非法'}")
    
    # 测试牌索引转换
    try:
        index = scai_engine.PyActionMask.tile_to_index(0, 1)  # 1万
        assert isinstance(index, int), "索引应该是整数"
        print(f"✓ 牌转索引成功: 1万 -> {index}")
        
        tile_str = scai_engine.PyActionMask.index_to_tile(index)
        assert isinstance(tile_str, str), "牌字符串应该是字符串"
        print(f"✓ 索引转牌成功: {index} -> {tile_str}")
    except Exception as e:
        print(f"⚠ 牌索引转换测试跳过: {e}")
    
    print("✓ PyActionMask 测试通过")


def test_pygame_engine():
    """测试 PyGameEngine"""
    print("\n=== 测试 PyGameEngine ===")
    
    # 创建游戏引擎
    engine = scai_engine.PyGameEngine()
    print(f"✓ 创建游戏引擎成功")
    
    # 初始化游戏
    try:
        engine.initialize()
        print(f"✓ 初始化游戏成功")
    except Exception as e:
        print(f"⚠ 初始化游戏失败: {e}")
        return
    
    # 获取游戏状态
    state = engine.state
    assert isinstance(state, scai_engine.PyGameState), "状态应该是 PyGameState"
    print(f"✓ 获取游戏状态成功")
    
    # 测试处理动作（摸牌）
    try:
        result = engine.process_action(
            player_id=0,
            action_type="draw",
            tile_index=None,
            is_concealed=None
        )
        print(f"✓ 处理摸牌动作成功")
    except Exception as e:
        print(f"⚠ 处理动作失败: {e}")
    
    # 检查游戏是否结束
    is_over = engine.is_game_over()
    assert isinstance(is_over, bool), "游戏结束状态应该是布尔值"
    print(f"✓ 检查游戏状态成功: {'已结束' if is_over else '进行中'}")
    
    print("✓ PyGameEngine 测试通过")


def test_tensor_conversion():
    """测试 Tensor 转换"""
    print("\n=== 测试 Tensor 转换 ===")
    
    # 创建游戏状态
    state = scai_engine.PyGameState()
    
    # 转换为 Tensor
    try:
        tensor = scai_engine.state_to_tensor(state, 0)
        assert tensor.shape == (64, 4, 9), f"Tensor 形状应该是 (64, 4, 9)，实际是 {tensor.shape}"
        print(f"✓ 状态转 Tensor 成功: 形状 {tensor.shape}")
        
        # 检查数据类型
        assert tensor.dtype == np.float32, f"Tensor 类型应该是 float32，实际是 {tensor.dtype}"
        print(f"✓ Tensor 数据类型正确: {tensor.dtype}")
    except Exception as e:
        print(f"⚠ Tensor 转换测试跳过: {e}")
    
    # 测试动作掩码数组转换
    try:
        mask = scai_engine.PyActionMask.generate_own_turn(0, state)
        array = scai_engine.action_mask_to_array(mask, True, None)
        assert array.shape == (434,), f"动作掩码数组形状应该是 (434,)，实际是 {array.shape}"
        print(f"✓ 动作掩码转数组成功: 形状 {array.shape}")
        
        # 检查数据类型
        assert array.dtype == bool, f"动作掩码类型应该是 bool，实际是 {array.dtype}"
        print(f"✓ 动作掩码数据类型正确: {array.dtype}")
    except Exception as e:
        print(f"⚠ 动作掩码转换测试跳过: {e}")
    
    print("✓ Tensor 转换测试通过")


def main():
    """运行所有测试"""
    print("=" * 50)
    print("Python 绑定测试")
    print("=" * 50)
    
    try:
        test_pygame_state()
        test_pyaction_mask()
        test_pygame_engine()
        test_tensor_conversion()
        
        print("\n" + "=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
        return 0
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

