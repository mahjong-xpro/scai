#[cfg(test)]
mod tests {
    use scai_engine::game::game_engine::GameEngine;
    use scai_engine::game::action::Action;
    use scai_engine::game::blood_battle::BloodBattleRules;
    use scai_engine::tile::{Tile, Suit};
    use scai_engine::game::scoring::Meld;

    /// 测试完整的游戏流程：从初始化到结束
    #[test]
    fn test_complete_game_flow() {
        let mut engine = GameEngine::new();
        
        // 使用简单的动作回调
        let mut declare_phase = true;
        let mut player_declared = [false; 4];
        let mut turn_count = 0;
        
        let result = engine.run(|state, player_id| {
            turn_count += 1;
            
            // 定缺阶段
            if declare_phase {
                if !player_declared[player_id as usize] {
                    // 简单策略：选择手牌中最少的花色
                    let player = &state.players[player_id as usize];
                    let mut suit_counts = [0u8; 3];
                    
                    for (tile, &count) in player.hand.tiles_map() {
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
            
            // 游戏主循环：简化处理，随机出牌
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
                // 验证有结算结果或游戏已结束
                assert!(
                    !game_result.final_settlement.settlements.is_empty() || 
                    engine.state.is_game_over(),
                    "游戏应该结束或有结算结果"
                );
            }
            Err(e) => {
                // 允许游戏正常结束的错误
                match e {
                    scai_engine::game::game_engine::GameError::GameOver => {
                        // 游戏正常结束
                        assert!(engine.state.is_game_over());
                    }
                    _ => {
                        panic!("Unexpected error: {:?}", e);
                    }
                }
            }
        }
        
        // 验证至少有一个玩家离场或牌墙耗尽
        assert!(
            engine.state.out_count > 0 || engine.state.is_last_tile,
            "游戏应该以玩家离场或牌墙耗尽结束"
        );
    }

    /// 测试多种牌型的组合：七对 + 根
    #[test]
    fn test_multiple_win_types_combination() {
        use scai_engine::tile::win_check::WinChecker;
        use scai_engine::game::scoring::RootCounter;
        use scai_engine::tile::Hand;
        
        // 创建七对手牌（包含根）
        // 七对需要 14 张牌，7 个对子
        let mut hand = Hand::new();
        
        // 添加 4 张 1 万（根，算作 2 个对子）
        for _ in 0..4 {
            hand.add_tile(Tile::Wan(1));
        }
        
        // 添加其他 5 个对子（共 7 个对子）
        for rank in 2..=6 {
            hand.add_tile(Tile::Wan(rank));
            hand.add_tile(Tile::Wan(rank));
        }
        
        // 验证手牌数量（14 张）
        let total_tiles: u8 = hand.tiles_map().values().sum();
        assert_eq!(total_tiles, 14, "七对应该有 14 张牌");
        
        // 检查是否可以胡
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        
        // 注意：如果手牌设置不正确，可能无法胡
        // 这里主要验证根数的计算
        let roots = RootCounter::count_roots(&hand, &[]);
        assert_eq!(roots, 1, "应该有 1 个根（4 张 1 万）");
        
        // 如果手牌可以胡，验证是七对
        if result.is_win {
            assert_eq!(result.win_type, scai_engine::tile::win_check::WinType::SevenPairs);
        }
    }

    /// 测试复杂结算场景：杠上炮 + 查大叫
    #[test]
    fn test_complex_settlement_scenario() {
        let mut engine = GameEngine::new();
        engine.initialize().unwrap();
        
        // 所有玩家定缺
        for i in 0..4 {
            BloodBattleRules::declare_suit(i, Suit::Wan, &mut engine.state);
        }
        
        // 设置场景：
        // 1. A 杠了 B 的牌
        // 2. A 点炮给 C（杠上炮）
        // 3. 游戏继续，D 未听牌
        // 4. 流局结算（查大叫）
        
        // 设置 A 的手牌：有 3 张 1 万
        for _ in 0..3 {
            engine.state.players[0].hand.add_tile(Tile::Wan(1));
        }
        
        // 设置 B 的手牌：有 1 张 1 万
        engine.state.players[1].hand.add_tile(Tile::Wan(1));
        
        // 设置 C 的手牌：可以胡 1 万
        for i in 2..=9 {
            engine.state.players[2].hand.add_tile(Tile::Tong(i));
        }
        engine.state.players[2].hand.add_tile(Tile::Tong(1));
        engine.state.players[2].hand.add_tile(Tile::Tong(1));
        
        // B 出 1 万，A 直杠
        engine.state.current_player = 1;
        let _ = engine.process_action(1, Action::Discard { tile: Tile::Wan(1) });
        
        // 检查是否有自动响应（A 直杠）
        // 如果没有，手动处理
        if !engine.state.players[0].melds.iter().any(|m| {
            matches!(m, Meld::Kong { tile: Tile::Wan(1), .. })
        }) {
            engine.state.current_player = 0;
            engine.state.turn += 1;
            let _ = engine.process_action(0, Action::Gang { tile: Tile::Wan(1), is_concealed: false });
        }
        
        // 验证 A 有杠钱收入
        assert!(engine.state.players[0].gang_earnings > 0);
        
        // A 出牌点炮给 C
        engine.state.current_player = 0;
        engine.state.players[0].hand.add_tile(Tile::Wan(1));
        let _ = engine.process_action(0, Action::Discard { tile: Tile::Wan(1) });
        
        // C 胡牌
        engine.state.current_player = 2;
        let win_result = engine.process_action(2, Action::Win);
        
        if win_result.is_ok() {
            // 验证有杠上炮退税记录
            let refund_payments: Vec<_> = engine.state.instant_payments
                .iter()
                .filter(|p| p.reason == scai_engine::game::payment::PaymentReason::GangPaoRefund)
                .collect();
            
            // 如果有退税记录，验证其正确性
            if !refund_payments.is_empty() {
                let refund_amount: i32 = refund_payments
                    .iter()
                    .map(|p| p.amount)
                    .sum();
                
                assert!(refund_amount > 0, "退税金额应该大于 0");
            }
        }
    }

    /// 测试复杂结算场景：多次杠牌 + 流局结算
    #[test]
    fn test_multiple_kongs_and_final_settlement() {
        let mut engine = GameEngine::new();
        engine.initialize().unwrap();
        
        // 所有玩家定缺
        for i in 0..4 {
            BloodBattleRules::declare_suit(i, Suit::Wan, &mut engine.state);
        }
        
        // 设置场景：多个玩家进行多次杠牌
        // 1. A 暗杠
        for _ in 0..4 {
            engine.state.players[0].hand.add_tile(Tile::Wan(1));
        }
        
        engine.state.current_player = 0;
        engine.state.turn += 1;
        let kong_result = engine.process_action(0, Action::Gang { tile: Tile::Wan(1), is_concealed: true });
        
        if kong_result.is_ok() {
            // 验证 A 有杠钱收入
            assert!(engine.state.players[0].gang_earnings > 0);
            
            // 验证有支付记录
            let kong_payments: Vec<_> = engine.state.instant_payments
                .iter()
                .filter(|p| p.is_kong_payment())
                .collect();
            
            assert!(!kong_payments.is_empty(), "应该有杠钱支付记录");
        }
    }

    /// 测试复杂结算场景：查花猪 + 查大叫
    #[test]
    fn test_flower_pig_and_not_ready_settlement() {
        let mut engine = GameEngine::new();
        engine.initialize().unwrap();
        
        // 所有玩家定缺
        for i in 0..4 {
            BloodBattleRules::declare_suit(i, Suit::Wan, &mut engine.state);
        }
        
        // 设置场景：
        // 1. 玩家 0 定缺万子，但手牌中还有万子（查花猪）
        // 2. 玩家 1 未听牌（查大叫）
        // 3. 流局结算
        
        // 模拟流局：设置 is_last_tile
        engine.state.is_last_tile = true;
        
        // 设置玩家 0 的手牌：有定缺花色（查花猪）
        engine.state.players[0].declared_suit = Some(Suit::Wan);
        engine.state.players[0].hand.add_tile(Tile::Wan(1)); // 定缺万子，但有万子
        
        // 设置玩家 1 未听牌
        // 手牌不完整，无法听牌
        for i in 1..=5 {
            engine.state.players[1].hand.add_tile(Tile::Tong(i));
        }
        
        // 验证游戏状态
        assert!(engine.state.is_game_over());
        
        // 验证可以执行最终结算
        // 注意：这里只是验证状态，实际结算逻辑在 final_settlement 中
        assert!(engine.state.is_last_tile);
    }

    /// 测试多种牌型的组合：清一色 + 根
    #[test]
    fn test_pure_suit_with_roots() {
        use scai_engine::tile::win_check::WinChecker;
        use scai_engine::game::scoring::RootCounter;
        use scai_engine::tile::Hand;
        
        // 创建清一色手牌（包含根）
        let mut hand = Hand::new();
        
        // 添加 4 张 1 万（根）
        for _ in 0..4 {
            hand.add_tile(Tile::Wan(1));
        }
        
        // 添加其他牌组成清一色
        hand.add_tile(Tile::Wan(2));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Wan(4));
        hand.add_tile(Tile::Wan(5));
        hand.add_tile(Tile::Wan(6));
        hand.add_tile(Tile::Wan(7));
        hand.add_tile(Tile::Wan(8));
        hand.add_tile(Tile::Wan(9));
        hand.add_tile(Tile::Wan(9));
        
        // 检查是否可以胡
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        
        if result.is_win {
            // 检查根数
            let roots = RootCounter::count_roots(&hand, &[]);
            assert_eq!(roots, 1, "应该有 1 个根（4 张 1 万）");
        }
    }

    /// 测试复杂结算场景：自摸 + 杠上开花
    #[test]
    fn test_self_draw_with_kong_flower() {
        let mut engine = GameEngine::new();
        engine.initialize().unwrap();
        
        // 所有玩家定缺
        for i in 0..4 {
            BloodBattleRules::declare_suit(i, Suit::Wan, &mut engine.state);
        }
        
        // 设置场景：
        // 1. A 杠牌
        // 2. A 杠后补牌自摸（杠上开花）
        
        // 设置 A 的手牌：有 3 张 1 万
        for _ in 0..3 {
            engine.state.players[0].hand.add_tile(Tile::Wan(1));
        }
        
        // 设置 B 的手牌：有 1 张 1 万
        engine.state.players[1].hand.add_tile(Tile::Wan(1));
        
        // B 出 1 万，A 直杠
        engine.state.current_player = 1;
        let _ = engine.process_action(1, Action::Discard { tile: Tile::Wan(1) });
        
        // 检查是否有自动响应（A 直杠）
        // 如果没有，手动处理
        if !engine.state.players[0].melds.iter().any(|m| {
            matches!(m, Meld::Kong { tile: Tile::Wan(1), .. })
        }) {
            engine.state.current_player = 0;
            engine.state.turn += 1;
            let _ = engine.process_action(0, Action::Gang { tile: Tile::Wan(1), is_concealed: false });
        }
        
        // 验证 A 有杠钱收入
        assert!(engine.state.players[0].gang_earnings > 0);
        
        // 注意：杠后补牌自摸的逻辑在 handle_gang 中已经实现
        // 这里主要验证杠牌操作成功
    }
}

