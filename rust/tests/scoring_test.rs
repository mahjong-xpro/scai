use scai_engine::tile::{Hand, Tile};
use scai_engine::tile::win_check::{WinChecker, WinResult, WinType};
use scai_engine::game::scoring::{RootCounter, Settlement, ActionFlags};
use smallvec::SmallVec;

#[test]
fn test_integration_win_to_fans() {
    // 测试完整流程：胡牌判定 → 根数统计 → 番数计算
    
    // 1. 胡牌判定
    let mut hand = Hand::new();
    // 清七对
    for rank in [1, 2, 3, 4, 5, 6, 7] {
        hand.add_tile(Tile::Wan(rank));
        hand.add_tile(Tile::Wan(rank));
    }
    
    let mut checker = WinChecker::new();
    let win_result = checker.check_win(&hand);
    assert!(win_result.is_win);
    assert_eq!(win_result.win_type, WinType::PureSevenPairs);
    
    // 2. 根数统计
    let melds = vec![];
    let roots = RootCounter::count_roots(&hand, &melds);
    assert_eq!(roots, 0);
    
    // 3. 番数计算
    let mut actions = ActionFlags::new();
    actions.is_zi_mo = true;
    
    let settlement = Settlement::calculate(&win_result, roots, &actions);
    // 清七对 16 + 自摸 ×2 = 32
    assert_eq!(settlement.total_fans(), Some(32));
}

#[test]
fn test_integration_with_roots() {
    // 测试带根的情况
    
    // 1. 手牌：4 张 1 万（1 个根）+ 其他牌
    let mut hand = Hand::new();
    for _ in 0..4 {
        hand.add_tile(Tile::Wan(1));
    }
    for rank in 2..=5 {
        hand.add_tile(Tile::Wan(rank));
    }
    for rank in 6..=9 {
        hand.add_tile(Tile::Wan(rank));
    }
    hand.add_tile(Tile::Wan(1)); // 对子
    
    // 2. 根数统计
    let melds = vec![];
    let roots = RootCounter::count_roots(&hand, &melds);
    assert_eq!(roots, 1);
    
    // 3. 假设是平胡 + 1 根 + 自摸
    let win_result = WinResult {
        is_win: true,
        win_type: WinType::Normal,
        pair: Some(Tile::Wan(1)),
        groups: SmallVec::new(),
    };
    
    let mut actions = ActionFlags::new();
    actions.is_zi_mo = true;
    
    let settlement = Settlement::calculate(&win_result, roots, &actions);
    // 平胡 1 × 2^1(根) × 2^1(自摸) = 4
    assert_eq!(settlement.total_fans(), Some(4));
}

#[test]
fn test_integration_dragon_seven_pairs() {
    // 测试龙七对的动态计算
    
    // 双龙七对：2 个根
    let win_result = WinResult {
        is_win: true,
        win_type: WinType::DragonSevenPairs,
        pair: None,
        groups: SmallVec::new(),
    };
    
    let actions = ActionFlags::new();
    let settlement = Settlement::calculate(&win_result, 2, &actions);
    // 龙七对：七对(4) × 2^2(2根) = 16
    assert_eq!(settlement.total_fans(), Some(16));
    
    // 三龙七对：3 个根
    let settlement = Settlement::calculate(&win_result, 3, &actions);
    // 龙七对：七对(4) × 2^3(3根) = 32
    assert_eq!(settlement.total_fans(), Some(32));
}

#[test]
fn test_integration_example_calculations() {
    // 测试示例计算（参考胡牌规则.md 第 8 章）
    
    // 示例 1：清七对 + 1 个根 + 自摸
    let win_result = WinResult {
        is_win: true,
        win_type: WinType::PureSevenPairs,
        pair: None,
        groups: SmallVec::new(),
    };
    
    let mut actions = ActionFlags::new();
    actions.is_zi_mo = true;
    
    let settlement = Settlement::calculate(&win_result, 1, &actions);
    // 基础番：清七对 = 16
    // 根数：1 个 = ×2
    // 自摸：+1 番 = ×2
    // 总番数：16 × 2 × 2 = 64
    assert_eq!(settlement.total_fans(), Some(64));
    
    // 示例 2：龙七对（双龙）+ 杠上开花
    let win_result = WinResult {
        is_win: true,
        win_type: WinType::DragonSevenPairs,
        pair: None,
        groups: SmallVec::new(),
    };
    
    let mut actions = ActionFlags::new();
    actions.is_gang_kai = true;
    
    let settlement = Settlement::calculate(&win_result, 2, &actions);
    // 基础番：龙七对 = 16（七对 4 × 2^2(2根) = 16，已包含根数倍率）
    // 杠上开花：+1 番 = ×2
    // 总番数：16 × 2 = 32
    assert_eq!(settlement.total_fans(), Some(32));
}

