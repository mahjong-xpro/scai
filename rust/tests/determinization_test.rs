use scai_engine::tile::{Tile, Suit};
use scai_engine::game::state::GameState;
use scai_engine::game::player::Player;
use scai_engine::game::scoring::Meld;

/// 测试确定性填充功能
#[test]
fn test_fill_unknown_cards_basic() {
    let mut state = GameState::new();
    let viewer_id: u8 = 0;
    
    // 设置观察者的手牌（已知）
    state.players[viewer_id as usize].hand.add_tile(Tile::Wan(1));
    state.players[viewer_id as usize].hand.add_tile(Tile::Wan(2));
    state.players[viewer_id as usize].hand.add_tile(Tile::Wan(3));
    
    // 设置一些弃牌（已知）
    state.discard_history.push(scai_engine::game::state::DiscardRecord {
        player_id: 1,
        tile: Tile::Tong(1),
        turn: 1,
    });
    
    // 设置对手的明牌（已知）
    state.players[1].melds.push(Meld::Triplet { tile: Tile::Tiao(1) });
    
    // 计算牌墙剩余牌数（假设已抽取 13*4 + 1 = 53 张，剩余 55 张）
    let remaining_wall_count = 55;
    
    // 执行确定性填充
    state.fill_unknown_cards(viewer_id, remaining_wall_count, 12345);
    
    // 验证：对手的手牌应该被填充
    // 对手 1：初始 13 张，碰了 3 张，应该还有 10 张手牌
    let opponent1_hand_size = state.players[1].hand.total_count();
    assert_eq!(opponent1_hand_size, 10, "对手 1 应该有 10 张手牌（13 - 3）");
    
    // 对手 2 和 3：初始 13 张，没有碰/杠，应该还有 13 张手牌
    let opponent2_hand_size = state.players[2].hand.total_count();
    let opponent3_hand_size = state.players[3].hand.total_count();
    assert_eq!(opponent2_hand_size, 13, "对手 2 应该有 13 张手牌");
    assert_eq!(opponent3_hand_size, 13, "对手 3 应该有 13 张手牌");
    
    // 验证：观察者的手牌没有被修改
    assert_eq!(state.players[viewer_id as usize].hand.total_count(), 3,
               "观察者的手牌不应该被修改");
}

/// 测试确定性填充的确定性（相同 seed 产生相同结果）
#[test]
fn test_fill_unknown_cards_deterministic() {
    let mut state1 = GameState::new();
    let mut state2 = GameState::new();
    let viewer_id: u8 = 0;
    
    // 设置相同的初始状态
    state1.players[viewer_id as usize].hand.add_tile(Tile::Wan(1));
    state2.players[viewer_id as usize].hand.add_tile(Tile::Wan(1));
    
    // 使用相同的 seed 执行确定性填充
    let seed = 54321;
    let remaining_wall_count = 50;
    
    state1.fill_unknown_cards(viewer_id, remaining_wall_count, seed);
    state2.fill_unknown_cards(viewer_id, remaining_wall_count, seed);
    
    // 验证：两次填充的结果应该相同（确定性）
    for i in 1..4 {
        let hand1: Vec<Tile> = state1.players[i].hand.to_sorted_vec();
        let hand2: Vec<Tile> = state2.players[i].hand.to_sorted_vec();
        assert_eq!(hand1, hand2, "相同 seed 应该产生相同的填充结果（对手 {}）", i);
    }
}

/// 测试确定性填充处理已离场的玩家
#[test]
fn test_fill_unknown_cards_player_out() {
    let mut state = GameState::new();
    let viewer_id: u8 = 0;
    
    // 标记玩家 2 已离场
    state.players[2].mark_out();
    
    // 执行确定性填充
    let remaining_wall_count = 50;
    state.fill_unknown_cards(viewer_id, remaining_wall_count, 99999);
    
    // 验证：已离场的玩家不应该被填充
    assert_eq!(state.players[2].hand.total_count(), 0,
               "已离场的玩家不应该被填充");
    
    // 验证：其他对手应该被填充
    assert_eq!(state.players[1].hand.total_count(), 13,
               "未离场的对手应该被填充");
    assert_eq!(state.players[3].hand.total_count(), 13,
               "未离场的对手应该被填充");
}

/// 测试确定性填充处理碰/杠的情况
#[test]
fn test_fill_unknown_cards_with_melds() {
    let mut state = GameState::new();
    let viewer_id: u8 = 0;
    
    // 对手 1：碰了 1 次（3 张），应该还有 10 张手牌
    state.players[1].melds.push(Meld::Triplet { tile: Tile::Wan(5) });
    
    // 对手 2：杠了 1 次（4 张），应该还有 9 张手牌
    state.players[2].melds.push(Meld::Kong { tile: Tile::Tong(5), is_concealed: false });
    
    // 对手 3：碰了 2 次（6 张），应该还有 7 张手牌
    state.players[3].melds.push(Meld::Triplet { tile: Tile::Tiao(1) });
    state.players[3].melds.push(Meld::Triplet { tile: Tile::Tiao(2) });
    
    // 执行确定性填充
    let remaining_wall_count = 50;
    state.fill_unknown_cards(viewer_id, remaining_wall_count, 11111);
    
    // 验证：对手的手牌数量应该正确
    assert_eq!(state.players[1].hand.total_count(), 10,
               "对手 1 应该有 10 张手牌（13 - 3）");
    assert_eq!(state.players[2].hand.total_count(), 9,
               "对手 2 应该有 9 张手牌（13 - 4）");
    assert_eq!(state.players[3].hand.total_count(), 7,
               "对手 3 应该有 7 张手牌（13 - 6）");
}

/// 测试确定性填充不会超过每种牌的最大数量（4 张）
#[test]
fn test_fill_unknown_cards_max_tiles() {
    let mut state = GameState::new();
    let viewer_id: u8 = 0;
    
    // 对手 1 已经有 3 张万子 1
    for _ in 0..3 {
        state.players[1].hand.add_tile(Tile::Wan(1));
    }
    
    // 设置已知牌：观察者有 1 张万子 1（总共 4 张已知）
    state.players[viewer_id as usize].hand.add_tile(Tile::Wan(1));
    
    // 执行确定性填充
    let remaining_wall_count = 50;
    state.fill_unknown_cards(viewer_id, remaining_wall_count, 22222);
    
    // 验证：对手 1 的万子 1 不应该超过 4 张
    assert!(state.players[1].hand.tile_count(Tile::Wan(1)) <= 4,
            "每种牌最多 4 张");
}

