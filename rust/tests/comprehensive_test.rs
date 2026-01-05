use scai_engine::tile::{Hand, Tile, Wall};
use scai_engine::tile::win_check::{WinChecker, WinType};

/// 测试边界情况和非法输入
mod edge_cases {
    use super::*;

    #[test]
    fn test_empty_hand() {
        let hand = Hand::new();
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(!result.is_win);
    }

    #[test]
    fn test_single_tile() {
        let mut hand = Hand::new();
        hand.add_tile(Tile::Wan(1));
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(!result.is_win);
    }

    #[test]
    fn test_too_many_tiles() {
        let mut hand = Hand::new();
        // 添加 15 张牌（超过 14 张）
        for rank in 1..=15 {
            hand.add_tile(Tile::Wan(rank.min(9)));
        }
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(!result.is_win);
    }

    #[test]
    fn test_13_tiles() {
        let mut hand = Hand::new();
        // 13 张牌（不是 14 张）
        for rank in 1..=13 {
            hand.add_tile(Tile::Wan(rank.min(9)));
        }
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(!result.is_win);
    }

    #[test]
    fn test_all_same_tile() {
        let mut hand = Hand::new();
        // 14 张相同的牌（不构成胡牌）
        for _ in 0..14 {
            hand.add_tile(Tile::Wan(1));
        }
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        // 14 张相同牌不构成标准胡牌型
        assert!(!result.is_win);
    }

    #[test]
    fn test_invalid_combination() {
        let mut hand = Hand::new();
        // 随机组合，不构成任何胡牌型
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Wan(5));
        hand.add_tile(Tile::Wan(7));
        hand.add_tile(Tile::Tong(2));
        hand.add_tile(Tile::Tong(4));
        hand.add_tile(Tile::Tong(6));
        hand.add_tile(Tile::Tong(8));
        hand.add_tile(Tile::Tiao(1));
        hand.add_tile(Tile::Tiao(3));
        hand.add_tile(Tile::Tiao(5));
        hand.add_tile(Tile::Tiao(7));
        hand.add_tile(Tile::Wan(9));
        hand.add_tile(Tile::Tong(9));
        
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(!result.is_win);
    }

    #[test]
    fn test_mixed_valid_invalid() {
        let mut hand = Hand::new();
        // 部分有效组合 + 无效牌
        // 对子
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        // 顺子
        hand.add_tile(Tile::Wan(2));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Wan(4));
        // 无效组合
        hand.add_tile(Tile::Tong(1));
        hand.add_tile(Tile::Tong(3));
        hand.add_tile(Tile::Tong(5));
        hand.add_tile(Tile::Tong(7));
        hand.add_tile(Tile::Tong(9));
        hand.add_tile(Tile::Tiao(2));
        hand.add_tile(Tile::Tiao(4));
        hand.add_tile(Tile::Tiao(6));
        
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(!result.is_win);
    }
}

/// 测试所有基本胡牌型的各种组合
mod win_type_combinations {
    use super::*;

    #[test]
    fn test_normal_win_with_sequences() {
        let mut hand = Hand::new();
        // 1 个对子 + 4 个顺子
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
        
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(result.is_win);
        assert_eq!(result.win_type, WinType::Normal);
    }

    #[test]
    fn test_normal_win_with_triplets() {
        let mut hand = Hand::new();
        // 1 个对子 + 4 个刻子
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        for _ in 0..3 {
            hand.add_tile(Tile::Wan(2));
        }
        for _ in 0..3 {
            hand.add_tile(Tile::Wan(3));
        }
        for _ in 0..3 {
            hand.add_tile(Tile::Tong(1));
        }
        for _ in 0..3 {
            hand.add_tile(Tile::Tong(2));
        }
        
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(result.is_win);
        // 应该是 AllTriplets（对对胡）
        assert_eq!(result.win_type, WinType::AllTriplets);
    }

    #[test]
    fn test_normal_win_mixed() {
        let mut hand = Hand::new();
        // 1 个对子 + 2 个顺子 + 2 个刻子
        hand.add_tile(Tile::Wan(1));
        hand.add_tile(Tile::Wan(1));
        // 顺子 1
        hand.add_tile(Tile::Wan(2));
        hand.add_tile(Tile::Wan(3));
        hand.add_tile(Tile::Wan(4));
        // 顺子 2
        hand.add_tile(Tile::Wan(5));
        hand.add_tile(Tile::Wan(6));
        hand.add_tile(Tile::Wan(7));
        // 刻子 1
        for _ in 0..3 {
            hand.add_tile(Tile::Tong(1));
        }
        // 刻子 2
        for _ in 0..3 {
            hand.add_tile(Tile::Tong(2));
        }
        
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(result.is_win);
        assert_eq!(result.win_type, WinType::Normal);
    }

    #[test]
    fn test_seven_pairs_variations() {
        // 测试七对的各种组合
        let mut hand = Hand::new();
        // 七对（不同花色）
        for rank in [1, 2, 3, 4, 5, 6, 7] {
            hand.add_tile(Tile::Wan(rank));
            hand.add_tile(Tile::Wan(rank));
        }
        
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(result.is_win);
        assert_eq!(result.win_type, WinType::PureSevenPairs);
    }

    #[test]
    fn test_all_triplets_variations() {
        let mut hand = Hand::new();
        // 对对胡：4 个刻子 + 1 个对子（不同花色）
        for _ in 0..3 {
            hand.add_tile(Tile::Wan(1));
        }
        for _ in 0..3 {
            hand.add_tile(Tile::Wan(2));
        }
        for _ in 0..3 {
            hand.add_tile(Tile::Tong(1));
        }
        for _ in 0..3 {
            hand.add_tile(Tile::Tong(2));
        }
        hand.add_tile(Tile::Tiao(1));
        hand.add_tile(Tile::Tiao(1));
        
        let mut checker = WinChecker::new();
        let result = checker.check_win(&hand);
        assert!(result.is_win);
        assert_eq!(result.win_type, WinType::AllTriplets);
    }
}

