/// 可执行文件入口（用于测试和调试）

use scai_engine::{Wall, Hand, Suit};

fn main() {
    println!("血战到底 AI 引擎测试");
    
    // 测试牌墙
    let mut wall = Wall::new();
    println!("创建牌墙：{} 张牌", wall.total_count());
    
    wall.shuffle();
    println!("洗牌完成，剩余：{} 张", wall.remaining_count());
    
    // 测试手牌
    let mut hand = Hand::new();
    
    // 抽取 13 张牌（初始手牌）
    for _ in 0..13 {
        if let Some(tile) = wall.draw() {
            hand.add_tile(tile);
        }
    }
    
    println!("抽取 13 张牌后，手牌总数：{}", hand.total_count());
    println!("剩余牌数：{}", wall.remaining_count());
    
    // 显示手牌（排序后）
    let sorted = hand.to_sorted_vec();
    println!("手牌（排序后）：");
    for tile in sorted {
        let suit_str = match tile.suit() {
            Suit::Wan => "万",
            Suit::Tong => "筒",
            Suit::Tiao => "条",
        };
        print!("{}{} ", tile.rank(), suit_str);
    }
    println!();
}

