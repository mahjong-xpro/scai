#[cfg(test)]
mod tests {
    use crate::game::game_engine::GameEngine;
    use crate::game::action::Action;
    use crate::tile::Tile;
    use crate::game::payment::{PaymentTracker, PaymentReason};

    /// 测试杠上炮"呼叫转移"：A 杠了 B 的牌，然后 A 点炮给 C
    /// 应该退还最近一次杠的钱给 C
    #[test]
    fn test_gang_pao_call_transfer() {
        // TODO: 实现完整的测试用例
        // 1. 创建游戏引擎
        // 2. 初始化游戏（发牌、定缺）
        // 3. A 杠了 B 的牌（记录支付记录）
        // 4. A 出牌点炮给 C
        // 5. 检查：
        //    - instant_payments 中是否有 GangPaoRefund 记录
        //    - A 的 gang_earnings 是否正确减少
        //    - C 的 gang_earnings 是否正确增加
        //    - 退税金额是否等于最近一次杠的收入
    }

    /// 测试多次杠牌后的杠上炮：A 杠了 B 和 C 的牌，然后 A 点炮给 D
    /// 应该只退还最近一次杠的钱（不是所有杠钱）
    #[test]
    fn test_gang_pao_multiple_kongs() {
        // TODO: 实现完整的测试用例
        // 1. A 杠了 B 的牌（2分）
        // 2. A 杠了 C 的牌（2分）
        // 3. A 出牌点炮给 D
        // 4. 检查：
        //    - 退税金额应该是 2 分（最近一次杠），而不是 4 分（所有杠钱）
        //    - A 的 gang_earnings 应该减少 2 分，而不是清零
    }

    /// 测试杠上炮的追溯性：检查是否能追溯到杠钱的原始支付者
    #[test]
    fn test_gang_pao_traceability() {
        // TODO: 实现完整的测试用例
        // 1. A 杠了 B 的牌（2分）
        // 2. A 出牌点炮给 C
        // 3. 检查：
        //    - 使用 PaymentTracker::get_latest_kong_payers 能找到 B
        //    - instant_payments 中有从 B 到 A 的支付记录
        //    - instant_payments 中有从 A 到 C 的退税记录（GangPaoRefund）
    }
}

