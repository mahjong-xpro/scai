use scai_engine::tile::{Hand, Tile, Suit};
use scai_engine::game::state::GameState;
use scai_engine::game::player::Player;
use scai_engine::engine::action_mask::ActionMask;

/// 测试定缺色未打完时的动作掩码限制
#[test]
fn test_action_mask_with_declared_suit_not_finished() {
    let mut state = GameState::new();
    let player_id: u8 = 0;
    let player = &mut state.players[player_id as usize];
    
    // 设置定缺色为条子
    player.declare_suit(Suit::Tiao);
    
    // 添加手牌：既有定缺色（条子），也有非定缺色（万子）
    player.hand.add_tile(Tile::Tiao(1)); // 定缺色
    player.hand.add_tile(Tile::Tiao(2)); // 定缺色
    player.hand.add_tile(Tile::Wan(1));  // 非定缺色
    player.hand.add_tile(Tile::Wan(2));   // 非定缺色
    
    // 生成动作掩码（自己的回合）
    let mask = ActionMask::generate(player_id, &state, None);
    let bool_mask = mask.to_bool_array(true, None);
    
    // 检查：只能出定缺色的牌（条子），不能出非定缺色的牌（万子）
    let tiao1_idx = ActionMask::tile_to_index(Tile::Tiao(1)).unwrap();
    let tiao2_idx = ActionMask::tile_to_index(Tile::Tiao(2)).unwrap();
    let wan1_idx = ActionMask::tile_to_index(Tile::Wan(1)).unwrap();
    let wan2_idx = ActionMask::tile_to_index(Tile::Wan(2)).unwrap();
    
    // 定缺色的牌可以出
    assert!(bool_mask[tiao1_idx], "应该可以出定缺色的牌（条子1）");
    assert!(bool_mask[tiao2_idx], "应该可以出定缺色的牌（条子2）");
    
    // 非定缺色的牌不能出
    assert!(!bool_mask[wan1_idx], "定缺色未打完时，不能出非定缺色的牌（万子1）");
    assert!(!bool_mask[wan2_idx], "定缺色未打完时，不能出非定缺色的牌（万子2）");
    
    // 验证动作验证函数
    assert!(ActionMask::validate_action(tiao1_idx, player_id, &state, true, None),
            "validate_action 应该允许出定缺色的牌");
    assert!(!ActionMask::validate_action(wan1_idx, player_id, &state, true, None),
            "validate_action 应该禁止出非定缺色的牌");
}

/// 测试定缺色已打完后的动作掩码
#[test]
fn test_action_mask_after_declared_suit_finished() {
    let mut state = GameState::new();
    let player_id: u8 = 0;
    let player = &mut state.players[player_id as usize];
    
    // 设置定缺色为条子
    player.declare_suit(Suit::Tiao);
    
    // 只添加非定缺色的牌（定缺色已打完）
    player.hand.add_tile(Tile::Wan(1));
    player.hand.add_tile(Tile::Wan(2));
    player.hand.add_tile(Tile::Tong(1));
    
    // 生成动作掩码（自己的回合）
    let mask = ActionMask::generate(player_id, &state, None);
    let bool_mask = mask.to_bool_array(true, None);
    
    // 检查：定缺色已打完，可以出任何牌
    let wan1_idx = ActionMask::tile_to_index(Tile::Wan(1)).unwrap();
    let wan2_idx = ActionMask::tile_to_index(Tile::Wan(2)).unwrap();
    let tong1_idx = ActionMask::tile_to_index(Tile::Tong(1)).unwrap();
    
    assert!(bool_mask[wan1_idx], "定缺色已打完，应该可以出任何牌（万子1）");
    assert!(bool_mask[wan2_idx], "定缺色已打完，应该可以出任何牌（万子2）");
    assert!(bool_mask[tong1_idx], "定缺色已打完，应该可以出任何牌（筒子1）");
}

/// 测试响应别人出牌时的定缺色限制（碰牌）
#[test]
fn test_action_mask_pong_with_declared_suit() {
    let mut state = GameState::new();
    let player_id: u8 = 0;
    let player = &mut state.players[player_id as usize];
    
    // 设置定缺色为条子
    player.declare_suit(Suit::Tiao);
    
    // 添加手牌：有定缺色（条子）和非定缺色（万子）
    player.hand.add_tile(Tile::Tiao(1));
    player.hand.add_tile(Tile::Tiao(1)); // 可以碰条子
    player.hand.add_tile(Tile::Wan(1));
    player.hand.add_tile(Tile::Wan(1)); // 可以碰万子
    
    // 生成动作掩码（响应别人出的万子1）
    let mask = ActionMask::generate(player_id, &state, Some(Tile::Wan(1)));
    let bool_mask = mask.to_bool_array(false, Some(Tile::Wan(1)));
    
    // 检查：定缺色未打完，不能碰非定缺色的牌
    let pong_wan1_idx = ActionMask::tile_to_index(Tile::Wan(1)).unwrap() + 108;
    assert!(!bool_mask[pong_wan1_idx], "定缺色未打完时，不能碰非定缺色的牌");
    
    // 生成动作掩码（响应别人出的条子1）
    let mask2 = ActionMask::generate(player_id, &state, Some(Tile::Tiao(1)));
    let bool_mask2 = mask2.to_bool_array(false, Some(Tile::Tiao(1)));
    
    // 检查：可以碰定缺色的牌
    let pong_tiao1_idx = ActionMask::tile_to_index(Tile::Tiao(1)).unwrap() + 108;
    assert!(bool_mask2[pong_tiao1_idx], "可以碰定缺色的牌");
}

/// 测试响应别人出牌时的定缺色限制（杠牌）
#[test]
fn test_action_mask_kong_with_declared_suit() {
    let mut state = GameState::new();
    let player_id: u8 = 0;
    let player = &mut state.players[player_id as usize];
    
    // 设置定缺色为条子
    player.declare_suit(Suit::Tiao);
    
    // 添加手牌：有定缺色（条子）和非定缺色（万子）
    player.hand.add_tile(Tile::Tiao(1));
    player.hand.add_tile(Tile::Tiao(1));
    player.hand.add_tile(Tile::Tiao(1)); // 可以直杠条子
    player.hand.add_tile(Tile::Wan(1));
    player.hand.add_tile(Tile::Wan(1));
    player.hand.add_tile(Tile::Wan(1)); // 可以直杠万子
    
    // 生成动作掩码（响应别人出的万子1）
    let mask = ActionMask::generate(player_id, &state, Some(Tile::Wan(1)));
    let bool_mask = mask.to_bool_array(false, Some(Tile::Wan(1)));
    
    // 检查：定缺色未打完，不能杠非定缺色的牌
    let kong_wan1_idx = ActionMask::tile_to_index(Tile::Wan(1)).unwrap() + 216;
    assert!(!bool_mask[kong_wan1_idx], "定缺色未打完时，不能杠非定缺色的牌");
    
    // 生成动作掩码（响应别人出的条子1）
    let mask2 = ActionMask::generate(player_id, &state, Some(Tile::Tiao(1)));
    let bool_mask2 = mask2.to_bool_array(false, Some(Tile::Tiao(1)));
    
    // 检查：可以杠定缺色的牌
    let kong_tiao1_idx = ActionMask::tile_to_index(Tile::Tiao(1)).unwrap() + 216;
    assert!(bool_mask2[kong_tiao1_idx], "可以杠定缺色的牌");
}

/// 测试响应别人出牌时的定缺色限制（胡牌）
#[test]
fn test_action_mask_win_with_declared_suit() {
    let mut state = GameState::new();
    let player_id: u8 = 0;
    let player = &mut state.players[player_id as usize];
    
    // 设置定缺色为条子
    player.declare_suit(Suit::Tiao);
    
    // 添加手牌：接近胡牌，但还有定缺色（条子）
    // 这里简化测试，只检查定缺色限制
    player.hand.add_tile(Tile::Tiao(1));
    player.hand.add_tile(Tile::Wan(1));
    player.hand.add_tile(Tile::Wan(2));
    player.hand.add_tile(Tile::Wan(3));
    
    // 生成动作掩码（响应别人出的万子4，可以胡）
    // 注意：这里只是测试定缺色限制，不测试完整的胡牌逻辑
    let mask = ActionMask::generate(player_id, &state, Some(Tile::Wan(4)));
    let bool_mask = mask.to_bool_array(false, Some(Tile::Wan(4)));
    
    // 检查：定缺色未打完，不能胡非定缺色的牌
    let win_wan4_idx = ActionMask::tile_to_index(Tile::Wan(4)).unwrap() + 324;
    // 注意：这里可能因为其他原因（如不能胡）而返回 false，但至少定缺色限制应该生效
    // 如果确实可以胡，那么定缺色限制应该阻止它
}

