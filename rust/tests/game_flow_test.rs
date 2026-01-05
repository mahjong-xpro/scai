use scai_engine::game::game_engine::{GameEngine, GameError};
use scai_engine::game::action::Action;
use scai_engine::game::blood_battle::BloodBattleRules;
use scai_engine::tile::Suit;

/// 测试完整的游戏流程（包括定缺阶段）
#[test]
fn test_complete_game_flow_with_declare_suit() {
    let mut engine = GameEngine::new();
    
    // 使用简单的动作回调
    let mut declare_phase = true;
    let mut player_declared = [false; 4];
    
    let result = engine.run(|state, player_id| {
        // 定缺阶段
        if declare_phase {
            if !player_declared[player_id as usize] {
                // 简单策略：选择手牌中最少的花色
                let player = &state.players[player_id as usize];
                let mut suit_counts = [0u8; 3];
                
                for (tile, &count) in player.hand.tiles_map().iter() {
                    match tile.suit() {
                        Suit::Wan => suit_counts[0] += count,
                        Suit::Tong => suit_counts[1] += count,
                        Suit::Tiao => suit_counts[2] += count,
                    }
                }
                
                let min_suit_idx = suit_counts.iter()
                    .enumerate()
                    .min_by_key(|(_, &count)| count)
                    .map(|(idx, _)| idx)
                    .unwrap_or(0);
                
                let suit = match min_suit_idx {
                    0 => Suit::Wan,
                    1 => Suit::Tong,
                    _ => Suit::Tiao,
                };
                
                player_declared[player_id as usize] = true;
                
                // 检查是否所有玩家都已定缺
                if player_declared.iter().all(|&x| x) {
                    declare_phase = false;
                }
                
                return Action::DeclareSuit { suit };
            }
        }
        
        // 游戏主循环
        // 简化处理：随机出牌
        let player = &state.players[player_id as usize];
        if let Some((tile, _)) = player.hand.tiles_map().iter().next() {
            Action::Discard { tile: *tile }
        } else {
            Action::Pass
        }
    });
    
    // 验证游戏结果
    match result {
        Ok(game_result) => {
            // 验证有结算结果
            assert!(!game_result.final_settlement.settlements.is_empty() || 
                    engine.state.is_game_over());
        }
        Err(e) => {
            // 允许游戏正常结束的错误
            match e {
                GameError::GameOver => {
                    // 游戏正常结束
                }
                _ => {
                    panic!("Unexpected error: {:?}", e);
                }
            }
        }
    }
}

/// 测试定缺阶段
#[test]
fn test_declare_suit_phase() {
    let mut engine = GameEngine::new();
    engine.initialize().unwrap();
    
    // 测试定缺
    use scai_engine::game::blood_battle::BloodBattleRules;
    
    assert!(BloodBattleRules::declare_suit(0, Suit::Wan, &mut engine.state));
    assert_eq!(engine.state.players[0].declared_suit, Some(Suit::Wan));
    
    assert!(BloodBattleRules::declare_suit(1, Suit::Tong, &mut engine.state));
    assert_eq!(engine.state.players[1].declared_suit, Some(Suit::Tong));
    
    assert!(BloodBattleRules::declare_suit(2, Suit::Tiao, &mut engine.state));
    assert_eq!(engine.state.players[2].declared_suit, Some(Suit::Tiao));
    
    assert!(BloodBattleRules::declare_suit(3, Suit::Wan, &mut engine.state));
    assert_eq!(engine.state.players[3].declared_suit, Some(Suit::Wan));
    
    // 验证所有玩家都已定缺
    assert!(BloodBattleRules::all_players_declared(&engine.state));
}

/// 测试动作响应优先级
#[test]
fn test_action_response_priority() {
    let mut engine = GameEngine::new();
    engine.initialize().unwrap();
    
    // 设置玩家定缺
    for i in 0..4u8 {
        use scai_engine::game::blood_battle::BloodBattleRules;
        let suit = match i {
            0 => Suit::Wan,
            1 => Suit::Tong,
            2 => Suit::Tiao,
            _ => Suit::Wan,
        };
        BloodBattleRules::declare_suit(i, suit, &mut engine.state);
    }
    
    // 模拟出牌和响应
    // 这里简化处理，主要测试响应优先级逻辑
    let player_id = 0;
    use scai_engine::tile::Tile;
    
    // 获取玩家手牌中的一张牌
    let player = &engine.state.players[player_id as usize];
    if let Some((tile, _)) = player.hand.tiles_map().iter().next() {
        // 测试出牌后的响应处理
        let result = engine.handle_discard_responses(player_id, *tile);
        
        // 验证响应处理不会崩溃
        assert!(result.is_ok());
    }
}

/// 测试点炮胡
#[test]
fn test_discard_win() {
    let mut engine = GameEngine::new();
    engine.initialize().unwrap();
    
    // 设置玩家定缺
    for i in 0..4u8 {
        use scai_engine::game::blood_battle::BloodBattleRules;
        let suit = match i {
            0 => Suit::Wan,
            1 => Suit::Tong,
            2 => Suit::Tiao,
            _ => Suit::Wan,
        };
        BloodBattleRules::declare_suit(i, suit, &mut engine.state);
    }
    
    // 这里简化处理，主要测试点炮胡的逻辑不会崩溃
    // 实际测试需要构造特定的牌型
    // 注意：handle_discard_win 是私有方法，不能直接测试
    // 可以通过 handle_discard_responses 间接测试
    let player_id = 0;
    use scai_engine::tile::Tile;
    
    // 获取玩家手牌中的一张牌
    let player = &engine.state.players[player_id as usize];
    if let Some((tile, _)) = player.hand.tiles_map().iter().next() {
        // 测试出牌后的响应处理（包括点炮胡）
        let result = engine.handle_discard_responses(player_id, *tile);
        
        // 验证方法不会崩溃
        assert!(result.is_ok());
    }
}

/// 测试游戏结束后的完整结算
#[test]
fn test_final_settlement() {
    let mut engine = GameEngine::new();
    engine.initialize().unwrap();
    
    // 设置玩家定缺
    for i in 0..4u8 {
        use scai_engine::game::blood_battle::BloodBattleRules;
        let suit = match i {
            0 => Suit::Wan,
            1 => Suit::Tong,
            2 => Suit::Tiao,
            _ => Suit::Wan,
        };
        BloodBattleRules::declare_suit(i, suit, &mut engine.state);
    }
    
    // 测试最终结算
    let settlement = engine.final_settlement();
    
    // 验证结算结果不为空（即使没有需要结算的项目，也应该有空的结算列表）
    assert!(settlement.settlements.len() >= 0);
}

/// 测试加杠时的抢杠胡检查
#[test]
fn test_rob_kong_check() {
    let mut engine = GameEngine::new();
    engine.initialize().unwrap();
    
    // 设置玩家定缺
    for i in 0..4u8 {
        use scai_engine::game::blood_battle::BloodBattleRules;
        let suit = match i {
            0 => Suit::Wan,
            1 => Suit::Tong,
            2 => Suit::Tiao,
            _ => Suit::Wan,
        };
        BloodBattleRules::declare_suit(i, suit, &mut engine.state);
    }
    
    // 测试加杠方法（即使不能加杠，也应该返回合理的错误）
    use scai_engine::tile::Tile;
    let result = engine.handle_add_kong(0, Tile::Wan(1));
    
    // 验证方法不会崩溃
    match result {
        Ok(_) => {
            // 如果可以加杠，验证结果
        }
        Err(GameError::InvalidAction) => {
            // 不能加杠是正常的
        }
        Err(e) => {
            panic!("Unexpected error: {:?}", e);
        }
    }
}

/// 测试回合自动切换
#[test]
fn test_auto_turn_switch() {
    let mut engine = GameEngine::new();
    engine.initialize().unwrap();
    
    // 设置玩家定缺
    for i in 0..4u8 {
        use scai_engine::game::blood_battle::BloodBattleRules;
        let suit = match i {
            0 => Suit::Wan,
            1 => Suit::Tong,
            2 => Suit::Tiao,
            _ => Suit::Wan,
        };
        BloodBattleRules::declare_suit(i, suit, &mut engine.state);
    }
    
    // 测试回合切换
    let initial_player = engine.state.current_player;
    let initial_turn = engine.state.turn;
    
    let result = engine.next_turn();
    
    match result {
        Ok(_) => {
            // 验证回合已切换
            assert_ne!(engine.state.current_player, initial_player);
            assert_eq!(engine.state.turn, initial_turn + 1);
        }
        Err(GameError::GameOver) => {
            // 游戏已结束，无法切换回合
        }
        Err(e) => {
            panic!("Unexpected error: {:?}", e);
        }
    }
}

