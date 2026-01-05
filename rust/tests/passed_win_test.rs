use scai_engine::game::player::Player;
use scai_engine::game::rules;

#[test]
fn test_passed_win_restriction() {
    // 测试过胡锁定功能
    
    // 1. 玩家放弃 2 番的点炮
    let mut player = Player::new(0);
    player.record_passed_win(2);
    assert_eq!(player.passed_hu_fan, Some(2));
    
    // 2. 检查是否可以胡 1 番的点炮（应该被屏蔽）
    assert!(!rules::check_passed_win_restriction(1, player.passed_hu_fan, false));
    
    // 3. 检查是否可以胡 2 番的点炮（应该被屏蔽）
    assert!(!rules::check_passed_win_restriction(2, player.passed_hu_fan, false));
    
    // 4. 检查是否可以胡 3 番的点炮（应该可以，因为番数更高）
    assert!(rules::check_passed_win_restriction(3, player.passed_hu_fan, false));
    
    // 5. 检查自摸（应该可以，自摸不受过胡限制）
    assert!(rules::check_passed_win_restriction(1, player.passed_hu_fan, true));
    assert!(rules::check_passed_win_restriction(2, player.passed_hu_fan, true));
    
    // 6. 清除过胡锁定
    player.clear_passed_win();
    assert_eq!(player.passed_hu_fan, None);
    
    // 7. 清除后应该可以胡任何番数的点炮
    assert!(rules::check_passed_win_restriction(1, player.passed_hu_fan, false));
    assert!(rules::check_passed_win_restriction(2, player.passed_hu_fan, false));
}

#[test]
fn test_record_passed_win_multiple_times() {
    // 测试多次过胡的情况
    
    let mut player = Player::new(0);
    
    // 第一次过胡：放弃 3 番
    player.record_passed_win(3);
    assert_eq!(player.passed_hu_fan, Some(3));
    
    // 第二次过胡：放弃 2 番（应该更新为更小的值，更严格的限制）
    player.record_passed_win(2);
    assert_eq!(player.passed_hu_fan, Some(2));
    
    // 第三次过胡：放弃 5 番（不应该更新，因为 5 > 2）
    player.record_passed_win(5);
    assert_eq!(player.passed_hu_fan, Some(2));
    
    // 检查：不能胡 1 番和 2 番，但可以胡 3 番及以上
    assert!(!rules::check_passed_win_restriction(1, player.passed_hu_fan, false));
    assert!(!rules::check_passed_win_restriction(2, player.passed_hu_fan, false));
    assert!(rules::check_passed_win_restriction(3, player.passed_hu_fan, false));
}

#[test]
fn test_passed_win_clear_on_draw() {
    // 测试摸牌后清除过胡锁定
    
    let mut player = Player::new(0);
    player.record_passed_win(2);
    assert_eq!(player.passed_hu_fan, Some(2));
    
    // 模拟摸牌（应该清除过胡锁定）
    player.clear_passed_win();
    assert_eq!(player.passed_hu_fan, None);
    
    // 清除后应该可以胡任何番数的点炮
    assert!(rules::check_passed_win_restriction(1, player.passed_hu_fan, false));
}

