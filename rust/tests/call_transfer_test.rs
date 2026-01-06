#[cfg(test)]
mod tests {
    use scai_engine::game::game_engine::GameEngine;
    use scai_engine::game::action::Action;
    use scai_engine::tile::{Tile, Suit};
    use scai_engine::game::payment::{PaymentTracker, PaymentReason};
    use scai_engine::game::blood_battle::BloodBattleRules;
    use scai_engine::game::state::DiscardRecord;

    /// 测试杠上炮"呼叫转移"：A 杠了 B 的牌，然后 A 点炮给 C
    /// 应该退还最近一次杠的钱给 C
    #[test]
    fn test_gang_pao_call_transfer() {
        let mut engine = GameEngine::new();
        engine.initialize().unwrap();
        
        // 所有玩家定缺
        for i in 0..4 {
            BloodBattleRules::declare_suit(i, Suit::Wan, &mut engine.state);
        }
        
        // 设置场景：A (0) 杠了 B (1) 的牌，然后 A 点炮给 C (2)
        // 记录初始状态
        let initial_gang_earnings_a = engine.state.players[0].gang_earnings;
        let initial_gang_earnings_c = engine.state.players[2].gang_earnings;
        
        // 设置 A 的手牌：有 3 张 1 万，可以直杠
        for _ in 0..3 {
            engine.state.players[0].hand.add_tile(Tile::Wan(1));
        }
        
        // 设置 B 的手牌：有 1 张 1 万（可以被打出）
        engine.state.players[1].hand.add_tile(Tile::Wan(1));
        
        // 设置 C 的手牌：可以胡 1 万（简化：设置一个可以胡牌的手牌）
        // 注意：这里简化处理，实际测试中需要设置完整的可胡手牌
        for i in 2..=9 {
            engine.state.players[2].hand.add_tile(Tile::Tong(i));
        }
        // 添加一个对子，使手牌可以胡
        engine.state.players[2].hand.add_tile(Tile::Tong(1));
        engine.state.players[2].hand.add_tile(Tile::Tong(1));
        
        // 1. B 出 1 万
        engine.state.current_player = 1;
        let discard_result = engine.process_action(1, Action::Discard { tile: Tile::Wan(1) });
        assert!(discard_result.is_ok());
        
        // 2. A 直杠 B 的 1 万
        engine.state.current_player = 0;
        engine.state.turn += 1;
        
        let gang_result = engine.process_action(0, Action::Gang { tile: Tile::Wan(1), is_concealed: false });
        assert!(gang_result.is_ok(), "A 应该可以直杠 B 的 1 万");
        
        // 验证杠牌后的状态
        let gang_earnings_after_kong = engine.state.players[0].gang_earnings;
        assert!(gang_earnings_after_kong > initial_gang_earnings_a, "A 的杠钱应该增加");
        
        // 验证有支付记录
        let kong_payments = PaymentTracker::get_kong_payments_received(
            &engine.state.instant_payments,
            0,
        );
        assert!(!kong_payments.is_empty(), "应该有杠钱支付记录");
        
        // 3. A 出牌点炮给 C
        // 设置 A 的手牌，使其可以出 1 万点炮
        engine.state.current_player = 0;
        // 添加 1 万到 A 的手牌（杠后补牌）
        engine.state.players[0].hand.add_tile(Tile::Wan(1));
        
        // A 出 1 万（点炮给 C）
        let discard_result = engine.process_action(0, Action::Discard { tile: Tile::Wan(1) });
        assert!(discard_result.is_ok(), "A 应该可以出 1 万");
        
        // 4. C 胡牌
        engine.state.current_player = 2;
        let win_result = engine.process_action(2, Action::Win);
        assert!(win_result.is_ok(), "C 应该可以胡牌");
        
        // 5. 检查杠上炮退税
        // 检查 instant_payments 中是否有 GangPaoRefund 记录
        let refund_payments: Vec<_> = engine.state.instant_payments
            .iter()
            .filter(|p| p.reason == PaymentReason::GangPaoRefund)
            .collect();
        
        assert!(!refund_payments.is_empty(), "应该有杠上炮退税记录");
        
        // 检查退税金额
        let refund_amount: i32 = refund_payments
            .iter()
            .map(|p| p.amount)
            .sum();
        
        assert!(refund_amount > 0, "退税金额应该大于 0");
        
        // 检查 A 的 gang_earnings 是否正确减少
        let final_gang_earnings_a = engine.state.players[0].gang_earnings;
        assert_eq!(
            final_gang_earnings_a,
            gang_earnings_after_kong - refund_amount,
            "A 的杠钱应该减少退税金额"
        );
        
        // 检查 C 的 gang_earnings 是否正确增加
        let final_gang_earnings_c = engine.state.players[2].gang_earnings;
        assert_eq!(
            final_gang_earnings_c,
            initial_gang_earnings_c + refund_amount,
            "C 的杠钱应该增加退税金额"
        );
        
        // 检查退税金额是否等于最近一次杠的收入
        let latest_kong_payers = PaymentTracker::get_latest_kong_payers(
            &engine.state.instant_payments,
            0,
        );
        let expected_refund: i32 = latest_kong_payers
            .iter()
            .map(|(_, amount)| *amount)
            .sum();
        
        assert_eq!(
            refund_amount,
            expected_refund,
            "退税金额应该等于最近一次杠的收入"
        );
    }

    /// 测试多次杠牌后的杠上炮：A 杠了 B 和 C 的牌，然后 A 点炮给 D
    /// 应该只退还最近一次杠的钱（不是所有杠钱）
    #[test]
    fn test_gang_pao_multiple_kongs() {
        let mut engine = GameEngine::new();
        engine.initialize().unwrap();
        
        // 所有玩家定缺
        for i in 0..4 {
            BloodBattleRules::declare_suit(i, Suit::Wan, &mut engine.state);
        }
        
        // 设置场景：A (0) 杠了 B (1) 和 C (2) 的牌，然后点炮给 D (3)
        
        // 第一次杠：A 杠了 B 的 1 万
        for _ in 0..3 {
            engine.state.players[0].hand.add_tile(Tile::Wan(1));
        }
        engine.state.players[1].hand.add_tile(Tile::Wan(1));
        
        engine.state.current_player = 1;
        let _ = engine.process_action(1, Action::Discard { tile: Tile::Wan(1) });
        
        engine.state.current_player = 0;
        engine.state.turn += 1;
        let gang_result_1 = engine.process_action(0, Action::Gang { tile: Tile::Wan(1), is_concealed: false });
        assert!(gang_result_1.is_ok(), "A 应该可以直杠 B 的 1 万");
        
        let gang_earnings_after_first = engine.state.players[0].gang_earnings;
        assert!(gang_earnings_after_first > 0);
        
        // 第二次杠：A 杠了 C 的 2 万
        for _ in 0..3 {
            engine.state.players[0].hand.add_tile(Tile::Wan(2));
        }
        engine.state.players[2].hand.add_tile(Tile::Wan(2));
        
        engine.state.current_player = 2;
        let _ = engine.process_action(2, Action::Discard { tile: Tile::Wan(2) });
        
        engine.state.current_player = 0;
        engine.state.turn += 1;
        let gang_result_2 = engine.process_action(0, Action::Gang { tile: Tile::Wan(2), is_concealed: false });
        assert!(gang_result_2.is_ok(), "A 应该可以直杠 C 的 2 万");
        
        let gang_earnings_after_second = engine.state.players[0].gang_earnings;
        assert!(gang_earnings_after_second > gang_earnings_after_first);
        
        // 设置 D 的手牌：可以胡 3 万
        for i in 1..=9 {
            if i != 3 {
                engine.state.players[3].hand.add_tile(Tile::Tong(i));
            }
        }
        engine.state.players[3].hand.add_tile(Tile::Tong(1));
        engine.state.players[3].hand.add_tile(Tile::Tong(1));
        
        // A 出牌点炮给 D
        engine.state.current_player = 0;
        engine.state.players[0].hand.add_tile(Tile::Wan(3));
        
        let discard_result = engine.process_action(0, Action::Discard { tile: Tile::Wan(3) });
        assert!(discard_result.is_ok(), "A 应该可以出 3 万");
        
        // D 胡牌
        engine.state.current_player = 3;
        let win_result = engine.process_action(3, Action::Win);
        assert!(win_result.is_ok(), "D 应该可以胡牌");
        
        // 检查退税金额应该是最近一次杠的收入（第二次杠），而不是所有杠钱
        let refund_payments: Vec<_> = engine.state.instant_payments
            .iter()
            .filter(|p| p.reason == PaymentReason::GangPaoRefund)
            .collect();
        
        assert!(!refund_payments.is_empty(), "应该有杠上炮退税记录");
        
        let refund_amount: i32 = refund_payments
            .iter()
            .map(|p| p.amount)
            .sum();
        
        // 退税金额应该是最近一次杠的收入（第二次杠），通常是 3 分（3 人 × 1 分）
        let expected_refund = gang_earnings_after_second - gang_earnings_after_first;
        assert_eq!(
            refund_amount,
            expected_refund,
            "退税金额应该是最近一次杠的收入，而不是所有杠钱"
        );
        
        // 检查 A 的 gang_earnings 应该减少最近一次杠的收入，而不是清零
        let final_gang_earnings_a = engine.state.players[0].gang_earnings;
        assert_eq!(
            final_gang_earnings_a,
            gang_earnings_after_second - refund_amount,
            "A 的杠钱应该只减少最近一次杠的收入"
        );
        
        // A 应该还保留第一次杠的收入
        assert!(
            final_gang_earnings_a >= gang_earnings_after_first,
            "A 应该还保留第一次杠的收入"
        );
    }

    /// 测试杠上炮的追溯性：检查是否能追溯到杠钱的原始支付者
    #[test]
    fn test_gang_pao_traceability() {
        let mut engine = GameEngine::new();
        engine.initialize().unwrap();
        
        // 所有玩家定缺
        for i in 0..4 {
            BloodBattleRules::declare_suit(i, Suit::Wan, &mut engine.state);
        }
        
        // 设置场景：A (0) 杠了 B (1) 的牌，然后 A 点炮给 C (2)
        
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
        
        // B 出 1 万
        engine.state.current_player = 1;
        let _ = engine.process_action(1, Action::Discard { tile: Tile::Wan(1) });
        
        // A 直杠 B 的 1 万
        engine.state.current_player = 0;
        engine.state.turn += 1;
        let gang_result = engine.process_action(0, Action::Gang { tile: Tile::Wan(1), is_concealed: false });
        assert!(gang_result.is_ok(), "A 应该可以直杠 B 的 1 万");
        
        // 检查支付记录：应该有从 B 到 A 的支付记录
        let kong_payments_from_b: Vec<_> = engine.state.instant_payments
            .iter()
            .filter(|p| p.from_player == 1 && p.to_player == 0 && p.is_kong_payment())
            .collect();
        
        assert!(!kong_payments_from_b.is_empty(), "应该有从 B 到 A 的杠钱支付记录");
        
        // 使用 PaymentTracker::get_latest_kong_payers 能找到 B
        let latest_kong_payers = PaymentTracker::get_latest_kong_payers(
            &engine.state.instant_payments,
            0,
        );
        
        assert!(!latest_kong_payers.is_empty(), "应该能找到最近一次杠的支付者");
        assert!(
            latest_kong_payers.iter().any(|(payer_id, _)| *payer_id == 1),
            "最近一次杠的支付者应该包括 B"
        );
        
        // A 出牌点炮给 C
        engine.state.current_player = 0;
        engine.state.players[0].hand.add_tile(Tile::Wan(1));
        
        let discard_result = engine.process_action(0, Action::Discard { tile: Tile::Wan(1) });
        assert!(discard_result.is_ok(), "A 应该可以出 1 万");
        
        // C 胡牌
        engine.state.current_player = 2;
        let win_result = engine.process_action(2, Action::Win);
        assert!(win_result.is_ok(), "C 应该可以胡牌");
        
        // 检查 instant_payments 中有从 A 到 C 的退税记录（GangPaoRefund）
        let refund_payments: Vec<_> = engine.state.instant_payments
            .iter()
            .filter(|p| {
                p.reason == PaymentReason::GangPaoRefund
                    && p.from_player == 0
                    && p.to_player == 2
            })
            .collect();
        
        assert!(!refund_payments.is_empty(), "应该有从 A 到 C 的杠上炮退税记录");
        
        // 验证追溯性：退税金额应该等于 B 支付给 A 的金额
        let refund_amount: i32 = refund_payments
            .iter()
            .map(|p| p.amount)
            .sum();
        
        let b_payment_amount: i32 = kong_payments_from_b
            .iter()
            .map(|p| p.amount)
            .sum();
        
        // 注意：退税金额可能包括所有支付者的金额，而不仅仅是 B
        // 但应该至少包括 B 的支付金额
        assert!(
            refund_amount >= b_payment_amount,
            "退税金额应该至少包括 B 的支付金额"
        );
    }
}

