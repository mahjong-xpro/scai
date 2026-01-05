/// 位运算优化示例
/// 
/// 演示如何使用位掩码快速检测顺子、刻子、对子

use scai_engine::{Hand, Tile, Suit, HandMask};

fn main() {
    println!("位运算优化示例\n");

    // 创建手牌
    let mut hand = Hand::new();
    
    // 添加一些牌：万子顺子 1-2-3，筒子刻子 5-5-5，条子对子 7-7
    hand.add_tile(Tile::Wan(1));
    hand.add_tile(Tile::Wan(2));
    hand.add_tile(Tile::Wan(3));
    hand.add_tile(Tile::Tong(5));
    hand.add_tile(Tile::Tong(5));
    hand.add_tile(Tile::Tong(5));
    hand.add_tile(Tile::Tiao(7));
    hand.add_tile(Tile::Tiao(7));
    
    println!("手牌：");
    for tile in hand.to_sorted_vec() {
        let suit_str = match tile.suit() {
            Suit::Wan => "万",
            Suit::Tong => "筒",
            Suit::Tiao => "条",
        };
        print!("{}{} ", tile.rank(), suit_str);
    }
    println!("\n");

    // 创建位掩码
    let mask = HandMask::from_hand(&hand);
    
    // 检测顺子
    println!("检测顺子：");
    let sequences = mask.detect_all_sequences();
    if sequences.is_empty() {
        println!("  无顺子");
    } else {
        for (suit, start) in &sequences {
            let suit_str = match suit {
                Suit::Wan => "万",
                Suit::Tong => "筒",
                Suit::Tiao => "条",
            };
            println!("  {}{}-{}{}-{}{}", 
                     start, suit_str, 
                     start + 1, suit_str, 
                     start + 2, suit_str);
        }
    }
    println!();

    // 检测刻子
    println!("检测刻子：");
    let triplets = mask.detect_all_triplets();
    if triplets.is_empty() {
        println!("  无刻子");
    } else {
        for (suit, rank) in &triplets {
            let suit_str = match suit {
                Suit::Wan => "万",
                Suit::Tong => "筒",
                Suit::Tiao => "条",
            };
            println!("  {}{} (3张)", rank, suit_str);
        }
    }
    println!();

    // 检测对子
    println!("检测对子：");
    let pairs = mask.detect_all_pairs();
    if pairs.is_empty() {
        println!("  无对子");
    } else {
        for (suit, rank) in &pairs {
            let suit_str = match suit {
                Suit::Wan => "万",
                Suit::Tong => "筒",
                Suit::Tiao => "条",
            };
            println!("  {}{} (2张)", rank, suit_str);
        }
    }
    println!();

    // 性能对比示例
    println!("性能说明：");
    println!("  位运算检测使用位掩码，时间复杂度 O(1) 到 O(9)");
    println!("  相比传统遍历方法，性能提升显著");
}

