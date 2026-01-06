#[cfg(test)]
mod tests {
    use scai_engine::game::game_engine::{GameEngine, GameError};
    use scai_engine::game::action::Action;
    use scai_engine::game::blood_battle::BloodBattleRules;
    use scai_engine::tile::{Tile, Suit};
    use scai_engine::game::state::GameState;

    /// 测试牌墙耗尽的处理
    #[test]
    fn test_wall_exhaustion() {
        let mut engine = GameEngine::new();
        engine.initialize().unwrap();
        
        // 所有玩家定缺
        for i in 0..4 {
            BloodBattleRules::declare_suit(i, Suit::Wan, &mut engine.state);
        }
        
        // 模拟牌墙即将耗尽的情况
        // 抽取大部分牌，只留少量牌
        let total_tiles = 108;
        let initial_draw = 52; // 4 个玩家 × 13 张 = 52 张
        let remaining = total_tiles - initial_draw;
        
        // 继续抽取牌，直到只剩 1 张
        for _ in 0..(remaining - 1) {
            let _ = engine.wall.draw();
        }
        
        // 验证牌墙状态
        assert_eq!(engine.wall.remaining_count(), 1);
        assert!(!engine.state.is_last_tile); // 还没有标记为最后一张
        
        // 尝试摸牌（应该成功，并设置 is_last_tile）
        let draw_result = engine.process_action(0, Action::Draw);
        assert!(draw_result.is_ok());
        
        // 验证 is_last_tile 已被设置
        assert!(engine.state.is_last_tile);
        
        // 再次尝试摸牌（应该失败，返回 GameOver）
        let draw_result = engine.process_action(0, Action::Draw);
        assert!(matches!(draw_result, Err(GameError::GameOver)));
    }

    /// 测试所有玩家都离场的情况
    #[test]
    fn test_all_players_out() {
        let mut state = GameState::new();
        
        // 初始状态：所有玩家都活跃
        assert_eq!(state.out_count, 0);
        assert!(!state.is_game_over());
        
        // 玩家 0 离场
        state.mark_player_out(0);
        assert_eq!(state.out_count, 1);
        assert!(!state.is_game_over()); // 还有 3 个玩家
        
        // 玩家 1 离场
        state.mark_player_out(1);
        assert_eq!(state.out_count, 2);
        assert!(!state.is_game_over()); // 还有 2 个玩家
        
        // 玩家 2 离场
        state.mark_player_out(2);
        assert_eq!(state.out_count, 3);
        assert!(state.is_game_over()); // 只剩 1 个玩家，游戏结束
        
        // 验证最后一个玩家（玩家 3）未离场
        assert!(!state.players[3].is_out);
        
        // 尝试让最后一个玩家也离场（不应该影响游戏状态）
        state.mark_player_out(3);
        assert_eq!(state.out_count, 4);
        assert!(state.is_game_over());
    }

    /// 测试过胡锁定的边界情况：多次过胡后手牌变化
    #[test]
    fn test_passed_win_lock_edge_cases() {
        use scai_engine::game::player::Player;
        use scai_engine::game::rules;
        
        let mut player = Player::new(0);
        
        // 1. 测试：过胡后手牌变化，锁定应该清除
        player.record_passed_win(Tile::Wan(1), 2);
        assert_eq!(player.passed_hu_fan, Some(2));
        
        // 手牌变化（添加一张牌）
        player.add_tile_to_hand(Tile::Wan(2));
        assert_eq!(player.passed_hu_fan, None, "手牌变化后，过胡锁定应该清除");
        
        // 2. 测试：过胡后手牌变化（移除一张牌），锁定应该清除
        player.record_passed_win(Tile::Wan(3), 3);
        assert_eq!(player.passed_hu_fan, Some(3));
        
        player.remove_tile_from_hand(Tile::Wan(2));
        assert_eq!(player.passed_hu_fan, None, "手牌变化后，过胡锁定应该清除");
        
        // 3. 测试：多次过胡，应该记录最大番数
        player.record_passed_win(Tile::Wan(1), 2);
        assert_eq!(player.passed_hu_fan, Some(2));
        
        player.record_passed_win(Tile::Wan(2), 1); // 更小的番数，不应该更新
        assert_eq!(player.passed_hu_fan, Some(2), "应该保持最大番数");
        
        player.record_passed_win(Tile::Wan(3), 4); // 更大的番数，应该更新
        assert_eq!(player.passed_hu_fan, Some(4), "应该更新为最大番数");
        
        // 4. 测试：自摸不受过胡限制
        assert!(
            rules::check_passed_win_restriction(
                Tile::Wan(1),
                1,
                player.passed_hu_fan,
                player.passed_hu_tile,
                true // 自摸
            ),
            "自摸应该不受过胡限制"
        );
        
        // 5. 测试：不同牌的高番可以胡
        assert!(
            rules::check_passed_win_restriction(
                Tile::Wan(4),
                5, // 更高番数
                player.passed_hu_fan,
                player.passed_hu_tile,
                false // 点炮
            ),
            "不同牌的高番应该可以胡"
        );
        
        // 6. 测试：同一张牌不能胡（即使番数更高）
        if let Some(passed_tile) = player.passed_hu_tile {
            assert!(
                !rules::check_passed_win_restriction(
                    passed_tile,
                    5, // 更高番数
                    player.passed_hu_fan,
                    player.passed_hu_tile,
                    false // 点炮
                ),
                "同一张牌不能胡，即使番数更高"
            );
        }
    }

    /// 测试过胡锁定的边界情况：碰牌后锁定清除
    #[test]
    fn test_passed_win_lock_cleared_by_pong() {
        use scai_engine::game::player::Player;
        use scai_engine::game::pong::PongHandler;
        
        let mut player = Player::new(0);
        
        // 设置手牌：有 2 张 1 万
        player.hand.add_tile(Tile::Wan(1));
        player.hand.add_tile(Tile::Wan(1));
        
        // 过胡
        player.record_passed_win(Tile::Wan(2), 2);
        assert_eq!(player.passed_hu_fan, Some(2));
        
        // 碰牌（会修改手牌，应该清除过胡锁定）
        let pong_success = PongHandler::pong(&mut player, Tile::Wan(1));
        assert!(pong_success);
        assert_eq!(player.passed_hu_fan, None, "碰牌后，过胡锁定应该清除");
    }

    /// 测试过胡锁定的边界情况：杠牌后锁定清除
    #[test]
    fn test_passed_win_lock_cleared_by_kong() {
        use scai_engine::game::player::Player;
        use scai_engine::game::kong::KongHandler;
        
        let mut player = Player::new(0);
        
        // 设置手牌：有 3 张 1 万
        for _ in 0..3 {
            player.hand.add_tile(Tile::Wan(1));
        }
        
        // 过胡
        player.record_passed_win(Tile::Wan(2), 2);
        assert_eq!(player.passed_hu_fan, Some(2));
        
        // 直杠（会修改手牌，应该清除过胡锁定）
        let kong_success = KongHandler::direct_kong(&mut player, Tile::Wan(1));
        assert!(kong_success);
        assert_eq!(player.passed_hu_fan, None, "杠牌后，过胡锁定应该清除");
    }

    /// 测试牌墙耗尽时的结算
    #[test]
    fn test_settlement_on_wall_exhaustion() {
        let mut engine = GameEngine::new();
        engine.initialize().unwrap();
        
        // 所有玩家定缺
        for i in 0..4 {
            BloodBattleRules::declare_suit(i, Suit::Wan, &mut engine.state);
        }
        
        // 模拟牌墙耗尽的情况
        // 抽取所有牌
        while engine.wall.remaining_count() > 0 {
            let _ = engine.wall.draw();
        }
        
        // 设置 is_last_tile 标志
        engine.state.is_last_tile = true;
        
        // 验证游戏应该结束
        assert!(engine.state.is_game_over());
        
        // 尝试执行动作应该返回 GameOver
        let draw_result = engine.process_action(0, Action::Draw);
        assert!(matches!(draw_result, Err(GameError::GameOver)));
    }

    /// 测试所有玩家离场时的结算
    #[test]
    fn test_settlement_on_all_players_out() {
        let mut state = GameState::new();
        
        // 模拟所有玩家依次离场
        for i in 0..3 {
            state.mark_player_out(i);
            assert_eq!(state.out_count, (i + 1) as u8);
            
            if i < 2 {
                assert!(!state.is_game_over(), "还有玩家未离场，游戏应该继续");
            } else {
                assert!(state.is_game_over(), "只剩 1 个玩家，游戏应该结束");
            }
        }
        
        // 验证最后一个玩家未离场
        assert!(!state.players[3].is_out);
    }
}

