use scai_engine::tile::{Hand, Tile, Wall};
use scai_engine::tile::win_check::WinChecker;
use scai_engine::game::state::GameState;
use scai_engine::game::action::Action;
use std::thread;

/// 测试完整的牌局流程
#[test]
fn test_complete_game_flow() {
    // 1. 创建牌墙并洗牌
    let mut wall = Wall::new();
    wall.shuffle();
    
    // 2. 发牌给 4 个玩家（每人 13 张）
    let mut hands = [Hand::new(), Hand::new(), Hand::new(), Hand::new()];
    for i in 0..4 {
        for _ in 0..13 {
            if let Some(tile) = wall.draw() {
                hands[i].add_tile(tile);
            }
        }
    }
    
    // 3. 模拟游戏流程
    let mut game_state = GameState::new();
    // 注意：GameState 现在使用 players 而不是 hands
    for i in 0..4 {
        game_state.players[i].hand = hands[i].clone();
    }
    game_state.current_player = 0;
    
    // 4. 玩家 0 摸牌
    if let Some(tile) = wall.draw() {
        game_state.players[0].hand.add_tile(tile);
        game_state.last_action = Some(Action::Draw);
        
        // 5. 检查是否可以胡牌
        let mut checker = WinChecker::new();
        let result = checker.check_win(&game_state.players[0].hand);
        
        // 如果胡牌，设置动作标志
        if result.is_win {
            game_state.check_zi_mo();
        }
    }
    
    // 验证游戏状态
    assert_eq!(game_state.current_player, 0);
}

/// 测试多线程并发场景
#[test]
fn test_multithreaded_win_check() {
    use std::sync::mpsc;
    
    // 创建测试手牌
    let create_test_hand = || {
        let mut hand = Hand::new();
        // 基本胡牌型
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        for rank in 2..=4 {
            hand.add_tile(Tile::Wan(rank));
        }
        for rank in 5..=7 {
            hand.add_tile(Tile::Wan(rank));
        }
        for rank in 1..=3 {
            hand.add_tile(Tile::Tong(rank));
        }
        for rank in 4..=6 {
            hand.add_tile(Tile::Tong(rank));
        }
        hand
    };
    
    let (tx, rx) = mpsc::channel();
    let num_threads = 4;
    let iterations_per_thread = 100;
    
    // 启动多个线程
    for _ in 0..num_threads {
        let tx = tx.clone();
        thread::spawn(move || {
            let hand = create_test_hand();
            let mut checker = WinChecker::new();
            
            for _ in 0..iterations_per_thread {
                let result = checker.check_win(&hand);
                assert!(result.is_win);
            }
            
            tx.send(()).unwrap();
        });
    }
    
    // 等待所有线程完成
    for _ in 0..num_threads {
        rx.recv().unwrap();
    }
}

/// 测试并发访问 WinChecker
#[test]
fn test_concurrent_win_checker() {
    use std::sync::Arc;
    use std::sync::Mutex;
    
    let create_test_hand = || {
        let mut hand = Hand::new();
        // 七对
        for rank in [1, 2, 3, 4, 5, 6, 7] {
            hand.add_tile(Tile::Wan(rank));
            hand.add_tile(Tile::Wan(rank));
        }
        hand
    };
    
    let checker = Arc::new(Mutex::new(WinChecker::new()));
    let num_threads = 8;
    let mut handles = vec![];
    
    for _ in 0..num_threads {
        let checker = Arc::clone(&checker);
        let hand = create_test_hand();
        let handle = thread::spawn(move || {
            let mut checker = checker.lock().unwrap();
            let result = checker.check_win(&hand);
            assert!(result.is_win);
        });
        handles.push(handle);
    }
    
    for handle in handles {
        handle.join().unwrap();
    }
}

/// 测试完整的发牌、出牌、胡牌流程
#[test]
fn test_game_flow_with_actions() {
    let mut wall = Wall::new();
    wall.shuffle();
    
    let mut game_state = GameState::new();
    
    // 发牌
    for i in 0..4 {
        for _ in 0..13 {
            if let Some(tile) = wall.draw() {
                game_state.players[i].hand.add_tile(tile);
            }
        }
    }
    
    // 模拟几轮游戏
    for turn in 0..10 {
        game_state.turn = turn;
        let player = (turn % 4) as u8;
        game_state.current_player = player;
        
        // 摸牌
        if let Some(tile) = wall.draw() {
            game_state.players[player as usize].hand.add_tile(tile);
            game_state.last_action = Some(Action::Draw);
            
            // 检查胡牌
            let mut checker = WinChecker::new();
            let result = checker.check_win(&game_state.players[player as usize].hand);
            
            if result.is_win {
                game_state.check_zi_mo();
                break; // 有人胡牌，游戏结束
            }
            
            // 出牌
            if let Some(tile_to_discard) = game_state.players[player as usize].hand.distinct_tiles().into_iter().next() {
                game_state.players[player as usize].hand.remove_tile(tile_to_discard);
                game_state.last_action = Some(Action::Discard { tile: tile_to_discard });
            }
        }
    }
}

