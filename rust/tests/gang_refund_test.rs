use scai_engine::game::player::Player;
use scai_engine::game::settlement::{GangSettlement, FinalSettlement};

/// 测试杠上炮退税
#[test]
fn test_gang_pao_refund() {
    // 场景：玩家 A 杠牌收了 6 分，然后点炮给玩家 B
    let gang_player_id = 0;
    let win_player_id = 1;
    let gang_earnings = 6;
    
    let refund = GangSettlement::calculate_gang_pao_refund(
        gang_player_id,
        win_player_id,
        gang_earnings,
    );
    
    // 杠牌者应该支出 6 分
    assert_eq!(refund.payments.get(&gang_player_id), Some(&-6));
    
    // 胡牌者应该收入 6 分
    assert_eq!(refund.payments.get(&win_player_id), Some(&6));
    
    // 其他玩家不受影响
    assert_eq!(refund.payments.get(&2), None);
    assert_eq!(refund.payments.get(&3), None);
}

/// 测试查大叫退税（未听牌玩家退还杠钱）
#[test]
fn test_not_ready_refund() {
    // 场景：流局时，玩家 A 未听牌，但之前杠牌收了 6 分
    let mut players = [
        Player::new(0),
        Player::new(1),
        Player::new(2),
        Player::new(3),
    ];
    
    // 玩家 0 杠牌收了 6 分，但未听牌
    players[0].add_gang_earnings(6);
    // players[0].is_ready = false; // 默认就是 false
    
    // 玩家 1、2、3 都听牌了
    players[1].mark_ready();
    players[2].mark_ready();
    players[3].mark_ready();
    
    // 执行查大叫退税
    let refund_amount = players[0].gang_earnings;
    assert_eq!(refund_amount, 6);
    
    // 原始支付者是玩家 1、2、3（所有非玩家 0 的玩家）
    let original_payers = vec![1, 2, 3];
    let refund = FinalSettlement::refund_gang_money(0, refund_amount, &original_payers);
    
    // 玩家 0 应该支出 6 分
    assert_eq!(refund.payments.get(&0), Some(&-6));
    
    // 原始支付者应该平均分配收入（每人 2 分）
    assert_eq!(refund.payments.get(&1), Some(&2));
    assert_eq!(refund.payments.get(&2), Some(&2));
    assert_eq!(refund.payments.get(&3), Some(&2));
}

/// 测试查大叫退税（多个未听牌玩家）
#[test]
fn test_multiple_not_ready_refund() {
    // 场景：流局时，玩家 A 和 B 都未听牌，都杠过牌
    let mut players = [
        Player::new(0),
        Player::new(1),
        Player::new(2),
        Player::new(3),
    ];
    
    // 玩家 0 杠牌收了 6 分，未听牌
    players[0].add_gang_earnings(6);
    
    // 玩家 1 杠牌收了 3 分，未听牌
    players[1].add_gang_earnings(3);
    
    // 玩家 2、3 都听牌了
    players[2].mark_ready();
    players[3].mark_ready();
    
    // 玩家 0 的退税
    let refund0 = FinalSettlement::refund_gang_money(0, 6, &vec![1, 2, 3]);
    assert_eq!(refund0.payments.get(&0), Some(&-6));
    assert_eq!(refund0.payments.get(&1), Some(&2));
    assert_eq!(refund0.payments.get(&2), Some(&2));
    assert_eq!(refund0.payments.get(&3), Some(&2));
    
    // 玩家 1 的退税
    let refund1 = FinalSettlement::refund_gang_money(1, 3, &vec![0, 2, 3]);
    assert_eq!(refund1.payments.get(&1), Some(&-3));
    assert_eq!(refund1.payments.get(&0), Some(&1));
    assert_eq!(refund1.payments.get(&2), Some(&1));
    assert_eq!(refund1.payments.get(&3), Some(&1));
}

