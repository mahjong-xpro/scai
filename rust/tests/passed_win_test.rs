use scai_engine::game::player::Player;
use scai_engine::game::rules;
use scai_engine::tile::Tile;

#[test]
fn test_passed_win_restriction() {
    // 测试过胡锁定功能
    
    // 1. 玩家放弃 2 番的点炮（1万）
    let mut player = Player::new(0);
    player.record_passed_win(Tile::Wan(1), 2);
    assert_eq!(player.passed_hu_fan, Some(2));
    assert_eq!(player.passed_hu_tile, Some(Tile::Wan(1)));
    
    // 2. 检查是否可以胡 1 番的点炮（应该被屏蔽）
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(2), 1, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    
    // 3. 检查是否可以胡 2 番的点炮（应该被屏蔽）
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(2), 2, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    
    // 4. 检查是否可以胡同一张牌（1万），即使番数更高（应该被屏蔽）
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(1), 3, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    
    // 5. 检查是否可以胡 3 番的点炮（不同牌，应该可以，因为番数更高）
    assert!(rules::check_passed_win_restriction(
        Tile::Wan(2), 3, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    
    // 6. 检查自摸（应该可以，自摸不受过胡限制）
    assert!(rules::check_passed_win_restriction(
        Tile::Wan(1), 1, player.passed_hu_fan, player.passed_hu_tile, true
    ));
    assert!(rules::check_passed_win_restriction(
        Tile::Wan(1), 2, player.passed_hu_fan, player.passed_hu_tile, true
    ));
    
    // 7. 清除过胡锁定
    player.clear_passed_win();
    assert_eq!(player.passed_hu_fan, None);
    assert_eq!(player.passed_hu_tile, None);
    
    // 8. 清除后应该可以胡任何番数的点炮
    assert!(rules::check_passed_win_restriction(
        Tile::Wan(1), 1, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    assert!(rules::check_passed_win_restriction(
        Tile::Wan(1), 2, player.passed_hu_fan, player.passed_hu_tile, false
    ));
}

#[test]
fn test_record_passed_win_multiple_times() {
    // 测试多次过胡的情况
    
    let mut player = Player::new(0);
    
    // 第一次过胡：放弃 3 番（1万）
    player.record_passed_win(Tile::Wan(1), 3);
    assert_eq!(player.passed_hu_fan, Some(3));
    assert_eq!(player.passed_hu_tile, Some(Tile::Wan(1)));
    
    // 第二次过胡：放弃 2 番（2万，应该更新为更小的值，更严格的限制）
    player.record_passed_win(Tile::Wan(2), 2);
    assert_eq!(player.passed_hu_fan, Some(2));
    assert_eq!(player.passed_hu_tile, Some(Tile::Wan(2)));
    
    // 第三次过胡：放弃 5 番（3万，不应该更新，因为 5 > 2）
    player.record_passed_win(Tile::Wan(3), 5);
    assert_eq!(player.passed_hu_fan, Some(2));
    assert_eq!(player.passed_hu_tile, Some(Tile::Wan(2)));
    
    // 检查：不能胡 1 番和 2 番，但可以胡 3 番及以上（不同牌）
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(4), 1, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(4), 2, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    assert!(rules::check_passed_win_restriction(
        Tile::Wan(4), 3, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    
    // 检查：不能胡同一张牌（2万），即使番数更高
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(2), 5, player.passed_hu_fan, player.passed_hu_tile, false
    ));
}

#[test]
fn test_passed_win_clear_on_draw() {
    // 测试摸牌后清除过胡锁定
    
    let mut player = Player::new(0);
    player.record_passed_win(Tile::Wan(1), 2);
    assert_eq!(player.passed_hu_fan, Some(2));
    assert_eq!(player.passed_hu_tile, Some(Tile::Wan(1)));
    
    // 模拟摸牌（应该清除过胡锁定）
    player.clear_passed_win();
    assert_eq!(player.passed_hu_fan, None);
    assert_eq!(player.passed_hu_tile, None);
    
    // 清除后应该可以胡任何番数的点炮
    assert!(rules::check_passed_win_restriction(
        Tile::Wan(1), 1, player.passed_hu_fan, player.passed_hu_tile, false
    ));
}

