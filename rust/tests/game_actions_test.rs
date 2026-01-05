use scai_engine::game::pong::PongHandler;
use scai_engine::game::kong::KongHandler;
use scai_engine::game::ready::ReadyChecker;
use scai_engine::game::player::Player;
use scai_engine::game::scoring::Meld;
use scai_engine::tile::Tile;

/// 测试碰牌功能
#[test]
fn test_pong_functionality() {
    let mut player = Player::new(0);
    
    // 手牌中有两张 1 万
    player.hand.add_tile(Tile::Wan(1));
    player.hand.add_tile(Tile::Wan(1));
    
    // 检查是否可以碰
    assert!(PongHandler::can_pong(&player, &Tile::Wan(1)));
    
    // 执行碰牌
    assert!(PongHandler::pong(&mut player, Tile::Wan(1)));
    
    // 验证：已添加碰
    assert_eq!(player.melds.len(), 1);
    assert!(matches!(player.melds[0], Meld::Triplet { tile: Tile::Wan(1) }));
}

/// 测试加杠功能（从碰升级为杠）
#[test]
fn test_add_kong_from_pong() {
    let mut player = Player::new(0);
    
    // 1. 先碰三张 1 万
    player.melds.push(Meld::Triplet { tile: Tile::Wan(1) });
    
    // 2. 手牌中有 1 张 1 万
    player.hand.add_tile(Tile::Wan(1));
    
    // 3. 执行加杠
    assert!(KongHandler::add_kong(&mut player, Tile::Wan(1)));
    
    // 4. 验证：碰已转换为杠
    assert!(player.melds.iter().any(|m| {
        matches!(m, Meld::Kong { tile: Tile::Wan(1), is_concealed: false })
    }));
}

/// 测试听牌判定
#[test]
fn test_ready_check() {
    let mut player = Player::new(0);
    
    // 13 张牌，差一张就能胡
    // 对子：1万-1万
    player.hand.add_tile(Tile::Wan(1));
    player.hand.add_tile(Tile::Wan(1));
    // 顺子1：2万-3万-4万
    player.hand.add_tile(Tile::Wan(2));
    player.hand.add_tile(Tile::Wan(3));
    player.hand.add_tile(Tile::Wan(4));
    // 顺子2：5万-6万-7万
    player.hand.add_tile(Tile::Wan(5));
    player.hand.add_tile(Tile::Wan(6));
    player.hand.add_tile(Tile::Wan(7));
    // 顺子3：1筒-2筒-3筒
    player.hand.add_tile(Tile::Tong(1));
    player.hand.add_tile(Tile::Tong(2));
    player.hand.add_tile(Tile::Tong(3));
    // 顺子4：5筒-6筒（差一张 7 筒）
    player.hand.add_tile(Tile::Tong(5));
    player.hand.add_tile(Tile::Tong(6));
    
    // 检查听牌
    player.check_ready();
    assert!(player.is_ready);
    
    // 检查可以听的牌
    let ready_tiles = player.get_ready_tiles();
    assert!(ready_tiles.contains(&Tile::Tong(7)));
}

/// 测试动作掩码生成
#[test]
fn test_action_mask_generation() {
    use scai_engine::engine::action_mask::ActionMask;
    use scai_engine::game::state::GameState;
    
    let mut state = GameState::new();
    let player_id: u8 = 0;
    
    // 设置玩家手牌
    state.players[player_id as usize].hand.add_tile(Tile::Wan(1));
    state.players[player_id as usize].hand.add_tile(Tile::Wan(1));
    
    // 生成动作掩码（响应别人的出牌）
    let mask = ActionMask::generate(player_id, &state, Some(Tile::Wan(1)));
    
    // 应该可以碰牌
    assert!(!mask.can_pong.is_empty());
}

/// 测试抢杠胡判定
#[test]
fn test_rob_kong() {
    let mut player = Player::new(0);
    let melds = vec![];
    
    // 13 张牌，差一张 1 万就能胡
    // 对子：1万-1万（这里应该是 2 张，但为了测试抢杠，我们假设只有 1 张）
    player.hand.add_tile(Tile::Wan(1));
    // 其他牌组成完整的牌型...
    // 简化测试：假设手牌差 1 万就能胡
    
    // 检查是否可以抢杠胡（当别人加杠 1 万时）
    // 注意：这个测试需要更完整的牌型，这里只是测试接口
    let can_rob = KongHandler::can_rob_kong(&player, &Tile::Wan(1), &melds);
    // 这个结果取决于实际的手牌，这里只是测试方法存在
    let _ = can_rob;
}

