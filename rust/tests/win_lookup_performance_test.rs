use scai_engine::tile::{Hand, Tile, Suit};
use scai_engine::tile::win_lookup::get_lookup_table;
use scai_engine::tile::win_check::WinChecker;
use std::time::Instant;

/// 测试查表法的性能
#[test]
fn test_lookup_performance() {
    let lookup_table = get_lookup_table();
    let size = lookup_table.size();
    println!("查表大小: 2={}, 5={}, 8={}, 11={}, 14={}", 
             size.0, size.1, size.2, size.3, size.4);
    
    // 创建一个测试手牌（基本胡牌型）
    let mut hand = Hand::new();
    // 对子
    hand.add_tile(Tile::Wan(1));
    hand.add_tile(Tile::Wan(1));
    // 顺子 1
    hand.add_tile(Tile::Wan(2));
    hand.add_tile(Tile::Wan(3));
    hand.add_tile(Tile::Wan(4));
    // 顺子 2
    hand.add_tile(Tile::Tong(1));
    hand.add_tile(Tile::Tong(2));
    hand.add_tile(Tile::Tong(3));
    // 顺子 3
    hand.add_tile(Tile::Tong(4));
    hand.add_tile(Tile::Tong(5));
    hand.add_tile(Tile::Tong(6));
    // 顺子 4
    hand.add_tile(Tile::Tiao(1));
    hand.add_tile(Tile::Tiao(2));
    hand.add_tile(Tile::Tiao(3));
    
    assert_eq!(hand.total_count(), 14);
    
    // 测试查表法
    let start = Instant::now();
    let is_win = lookup_table.is_win(&hand);
    let lookup_time = start.elapsed();
    
    // 测试递归算法
    let mut checker = WinChecker::new();
    let start = Instant::now();
    let result = checker.check_win(&hand);
    let recursive_time = start.elapsed();
    
    println!("查表法: {} (耗时: {:?})", is_win, lookup_time);
    println!("递归算法: {} (耗时: {:?})", result.is_win, recursive_time);
    
    assert_eq!(is_win, result.is_win);
    assert!(is_win); // 这个手牌应该可以胡
}

/// 测试查表法在大量调用下的性能
#[test]
fn test_lookup_performance_batch() {
    let lookup_table = get_lookup_table();
    
    // 创建多个测试手牌
    let mut hands = Vec::new();
    
    // 手牌 1: 基本胡牌型
    let mut hand1 = Hand::new();
    hand1.add_tile(Tile::Wan(1)); hand1.add_tile(Tile::Wan(1));
    hand1.add_tile(Tile::Wan(2)); hand1.add_tile(Tile::Wan(3)); hand1.add_tile(Tile::Wan(4));
    hand1.add_tile(Tile::Tong(1)); hand1.add_tile(Tile::Tong(2)); hand1.add_tile(Tile::Tong(3));
    hand1.add_tile(Tile::Tong(4)); hand1.add_tile(Tile::Tong(5)); hand1.add_tile(Tile::Tong(6));
    hand1.add_tile(Tile::Tiao(1)); hand1.add_tile(Tile::Tiao(2)); hand1.add_tile(Tile::Tiao(3));
    hands.push(hand1);
    
    // 手牌 2: 不能胡
    let mut hand2 = Hand::new();
    for _ in 0..14 {
        hand2.add_tile(Tile::Wan(1));
    }
    hands.push(hand2);
    
    // 测试查表法性能（1000 次调用）
    let iterations = 1000;
    let start = Instant::now();
    for _ in 0..iterations {
        for hand in &hands {
            let _ = lookup_table.is_win(hand);
        }
    }
    let lookup_time = start.elapsed();
    
    // 测试递归算法性能（1000 次调用）
    let mut checker = WinChecker::new();
    let start = Instant::now();
    for _ in 0..iterations {
        for hand in &hands {
            let _ = checker.check_win(hand);
        }
    }
    let recursive_time = start.elapsed();
    
    println!("查表法 {} 次调用: {:?} (平均: {:?})", 
             iterations * hands.len(), lookup_time, lookup_time / (iterations * hands.len()) as u32);
    println!("递归算法 {} 次调用: {:?} (平均: {:?})", 
             iterations * hands.len(), recursive_time, recursive_time / (iterations * hands.len()) as u32);
    
    // 查表法在大量调用时应该更快（虽然单次调用可能因为编码开销而稍慢）
    // 但在强化学习场景下，查表法可以避免递归计算，总体性能更好
    println!("性能对比: 查表法 {} vs 递归算法 {}", 
             lookup_time.as_nanos(), recursive_time.as_nanos());
    
    // 注意：查表法的主要优势是在复杂手牌情况下避免递归计算
    // 对于简单手牌，递归算法可能更快，但查表法更稳定
}

