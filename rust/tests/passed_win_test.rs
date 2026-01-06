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
    // 测试多次过胡的情况：应该记录最大番数（而不是最小番数）
    
    let mut player = Player::new(0);
    
    // 第一次过胡：放弃 2 番（1万）
    player.record_passed_win(Tile::Wan(1), 2);
    assert_eq!(player.passed_hu_fan, Some(2));
    assert_eq!(player.passed_hu_tile, Some(Tile::Wan(1)));
    
    // 第二次过胡：放弃 1 番（2万，不应该更新，因为 1 < 2，应该保持 2）
    player.record_passed_win(Tile::Wan(2), 1);
    assert_eq!(player.passed_hu_fan, Some(2)); // 应该是 2，不是 1
    assert_eq!(player.passed_hu_tile, Some(Tile::Wan(1))); // 应该保持第一次的牌
    
    // 第三次过胡：放弃 5 番（3万，应该更新，因为 5 > 2）
    player.record_passed_win(Tile::Wan(3), 5);
    assert_eq!(player.passed_hu_fan, Some(5)); // 应该是 5
    assert_eq!(player.passed_hu_tile, Some(Tile::Wan(3))); // 应该更新为第三次的牌
    
    // 检查：不能胡 1 番、2 番、3 番、4 番和 5 番，但可以胡 6 番及以上（不同牌）
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(4), 1, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(4), 2, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(4), 5, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    assert!(rules::check_passed_win_restriction(
        Tile::Wan(4), 6, player.passed_hu_fan, player.passed_hu_tile, false
    ));
    
    // 检查：不能胡同一张牌（3万），即使番数更高
    assert!(!rules::check_passed_win_restriction(
        Tile::Wan(3), 10, player.passed_hu_fan, player.passed_hu_tile, false
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

    #[test]
    fn test_passed_win_record_maximum_fans() {
        // 测试记录最大番数（而不是最小番数）
        // 规则：如果玩家先放弃了 2 番，然后放弃了 1 番，
        // 应该记录 2 番（因为不能胡 2 番或更低的点炮）
        
        let mut player = Player::new(0);
        
        // 先放弃 2 番
        player.record_passed_win(Tile::Wan(1), 2);
        assert_eq!(player.passed_hu_fan, Some(2));
        
        // 然后放弃 1 番（应该保持 2 番，而不是更新为 1 番）
        player.record_passed_win(Tile::Wan(2), 1);
        assert_eq!(player.passed_hu_fan, Some(2)); // 应该是 2，不是 1
        
        // 如果记录 1 番，玩家可以胡 2 番的点炮（错误！）
        // 如果记录 2 番，玩家不能胡 2 番或更低的点炮（正确！）
    }

    #[test]
    fn test_passed_win_threshold_check() {
        // 测试番数阈值检查
        
        let mut player = Player::new(0);
        
        // 玩家放弃了 2 番的点炮
        player.record_passed_win(Tile::Wan(1), 2);
        
        // 不能胡 2 番或更低的点炮
        assert!(!rules::check_passed_win_restriction(
            Tile::Wan(2), 1, player.passed_hu_fan, player.passed_hu_tile, false
        ));
        assert!(!rules::check_passed_win_restriction(
            Tile::Wan(2), 2, player.passed_hu_fan, player.passed_hu_tile, false
        ));
        
        // 可以胡 3 番或更高的点炮
        assert!(rules::check_passed_win_restriction(
            Tile::Wan(2), 3, player.passed_hu_fan, player.passed_hu_tile, false
        ));
    }

    #[test]
    fn test_passed_win_self_draw_unrestricted() {
        // 测试自摸不受限制
        
        let mut player = Player::new(0);
        
        // 玩家放弃了 2 番的点炮
        player.record_passed_win(Tile::Wan(1), 2);
        
        // 自摸不受限制，可以胡任何番数
        assert!(rules::check_passed_win_restriction(
            Tile::Wan(2), 1, player.passed_hu_fan, player.passed_hu_tile, true // 自摸
        ));
        assert!(rules::check_passed_win_restriction(
            Tile::Wan(2), 2, player.passed_hu_fan, player.passed_hu_tile, true // 自摸
        ));
    }

    #[test]
    fn test_passed_win_same_tile_restriction() {
        // 测试同一张牌不能胡
        
        let mut player = Player::new(0);
        
        // 玩家放弃了 1 万的点炮（2 番）
        player.record_passed_win(Tile::Wan(1), 2);
        
        // 不能胡同一张牌（即使番数更高）
        assert!(!rules::check_passed_win_restriction(
            Tile::Wan(1), 3, player.passed_hu_fan, player.passed_hu_tile, false
        ));
        
        // 可以胡其他牌（如果番数更高）
        assert!(rules::check_passed_win_restriction(
            Tile::Wan(2), 3, player.passed_hu_fan, player.passed_hu_tile, false
        ));
    }

