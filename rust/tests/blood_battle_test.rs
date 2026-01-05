use scai_engine::game::blood_battle::BloodBattleRules;
use scai_engine::game::state::GameState;
use scai_engine::game::settlement::{GangSettlement, FinalSettlement};
use scai_engine::game::player::Player;
use scai_engine::tile::Suit;

/// 测试初始定缺
#[test]
fn test_initial_declare_suit() {
    let mut state = GameState::new();
    
    // 所有玩家定缺
    assert!(BloodBattleRules::declare_suit(0, Suit::Wan, &mut state));
    assert!(BloodBattleRules::declare_suit(1, Suit::Tong, &mut state));
    assert!(BloodBattleRules::declare_suit(2, Suit::Tiao, &mut state));
    assert!(BloodBattleRules::declare_suit(3, Suit::Wan, &mut state));
    
    assert!(BloodBattleRules::all_players_declared(&state));
    assert_eq!(state.players[0].declared_suit, Some(Suit::Wan));
    assert_eq!(state.players[1].declared_suit, Some(Suit::Tong));
}

/// 测试刮风下雨（即时杠钱结算）
#[test]
fn test_gang_settlement() {
    let players = [
        Player::new(0),
        Player::new(1),
        Player::new(2),
        Player::new(3),
    ];
    
    // 测试暗杠结算
    let result = GangSettlement::calculate_gang_payment(0, true, &players);
    assert_eq!(result.payments.get(&0), Some(&6)); // 收入 6 分（3 人 × 2 分）
    assert_eq!(result.payments.get(&1), Some(&-2)); // 支出 2 分
    assert_eq!(result.payments.get(&2), Some(&-2)); // 支出 2 分
    assert_eq!(result.payments.get(&3), Some(&-2)); // 支出 2 分
    
    // 测试明杠结算
    let result = GangSettlement::calculate_gang_payment(1, false, &players);
    assert_eq!(result.payments.get(&1), Some(&3)); // 收入 3 分（3 人 × 1 分）
    assert_eq!(result.payments.get(&0), Some(&-1)); // 支出 1 分
}

/// 测试玩家离场逻辑
#[test]
fn test_player_out_logic() {
    let mut state = GameState::new();
    
    // 玩家 0 胡牌
    let can_continue = BloodBattleRules::handle_player_out(0, &mut state);
    assert!(state.players[0].is_out);
    assert_eq!(state.out_count, 1);
    assert!(can_continue); // 还有 3 个玩家，可以继续
    
    // 玩家 1 胡牌
    let can_continue = BloodBattleRules::handle_player_out(1, &mut state);
    assert_eq!(state.out_count, 2);
    assert!(can_continue); // 还有 2 个玩家，可以继续
    
    // 玩家 2 胡牌
    let can_continue = BloodBattleRules::handle_player_out(2, &mut state);
    assert_eq!(state.out_count, 3);
    assert!(!can_continue); // 只剩 1 个玩家，游戏结束
}

/// 测试查花猪
#[test]
fn test_check_flower_pig() {
    let mut players = [
        Player::new(0),
        Player::new(1),
        Player::new(2),
        Player::new(3),
    ];
    
    // 玩家 0 定缺万子，但手牌中还有万子（花猪）
    players[0].declare_suit(Suit::Wan);
    players[0].hand.add_tile(scai_engine::tile::Tile::Wan(1));
    
    // 玩家 1 定缺筒子，已打完
    players[1].declare_suit(Suit::Tong);
    
    // 玩家 2 定缺条子，已打完
    players[2].declare_suit(Suit::Tiao);
    
    // 玩家 3 已离场
    players[3].mark_out();
    
    let result = FinalSettlement::check_flower_pig(&players, 16);
    
    // 玩家 0（花猪）应该赔钱
    assert!(result.payments.get(&0).unwrap() < &0);
    // 玩家 1 和 2（非花猪）应该收钱
    assert!(result.payments.get(&1).unwrap() > &0);
    assert!(result.payments.get(&2).unwrap() > &0);
}

/// 测试查大叫
#[test]
fn test_check_not_ready() {
    let mut players = [
        Player::new(0),
        Player::new(1),
        Player::new(2),
        Player::new(3),
    ];
    
    // 玩家 0 和 1 听牌
    players[0].mark_ready();
    players[1].mark_ready();
    
    // 玩家 2 和 3 未听牌
    // players[2].is_ready = false; // 默认就是 false
    // players[3].is_ready = false;
    
    let result = FinalSettlement::check_not_ready(&players, 8);
    
    // 未听牌玩家应该赔钱
    assert!(result.payments.get(&2).unwrap() < &0);
    assert!(result.payments.get(&3).unwrap() < &0);
    
    // 听牌玩家应该收钱
    assert!(result.payments.get(&0).unwrap() > &0);
    assert!(result.payments.get(&1).unwrap() > &0);
}

/// 测试退税
#[test]
fn test_refund() {
    let mut players = [
        Player::new(0),
        Player::new(1),
        Player::new(2),
        Player::new(3),
    ];
    
    // 玩家 0 之前杠牌收了 6 分
    players[0].add_gang_earnings(6);
    
    // 现在需要退税（因为被查出是花猪或未听牌）
    let refund_amount = players[0].refund_gang_earnings();
    assert_eq!(refund_amount, 6);
    assert_eq!(players[0].gang_earnings, 0);
    
    // 退税结算
    let original_payers = vec![1, 2, 3];
    let result = FinalSettlement::refund_gang_money(0, refund_amount, &original_payers);
    
    // 玩家 0 支出
    assert_eq!(result.payments.get(&0), Some(&-6));
    // 原始支付者收入（平均分配）
    assert_eq!(result.payments.get(&1), Some(&2));
    assert_eq!(result.payments.get(&2), Some(&2));
    assert_eq!(result.payments.get(&3), Some(&2));
}

/// 测试完整流程：定缺 -> 游戏 -> 离场 -> 结算
#[test]
fn test_complete_blood_battle_flow() {
    let mut state = GameState::new();
    
    // 1. 初始定缺
    for i in 0..4 {
        let suit = match i {
            0 => Suit::Wan,
            1 => Suit::Tong,
            2 => Suit::Tiao,
            _ => Suit::Wan,
        };
        BloodBattleRules::declare_suit(i, suit, &mut state);
    }
    assert!(BloodBattleRules::all_players_declared(&state));
    
    // 2. 模拟游戏进行，玩家 0 胡牌
    state.mark_player_out(0);
    assert!(BloodBattleRules::can_continue(&state));
    
    // 3. 玩家 1 胡牌
    state.mark_player_out(1);
    assert!(BloodBattleRules::can_continue(&state));
    
    // 4. 玩家 2 胡牌
    state.mark_player_out(2);
    assert!(!BloodBattleRules::can_continue(&state)); // 游戏结束
    
    // 5. 局末结算（查大叫、查花猪）
    let active_players = BloodBattleRules::get_active_players(&state);
    assert_eq!(active_players, vec![3]); // 只剩玩家 3
}

