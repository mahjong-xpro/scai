use criterion::{black_box, criterion_group, criterion_main, Criterion};
use scai_engine::tile::{Hand, Tile};
use scai_engine::tile::win_check::WinChecker;

fn bench_win_check_normal(c: &mut Criterion) {
    let mut hand = Hand::new();
    // 基本胡牌型
    hand.add_tile(Tile::Wan(1));
    hand.add_tile(Tile::Wan(1));
    hand.add_tile(Tile::Wan(2));
    hand.add_tile(Tile::Wan(3));
    hand.add_tile(Tile::Wan(4));
    hand.add_tile(Tile::Wan(5));
    hand.add_tile(Tile::Wan(6));
    hand.add_tile(Tile::Wan(7));
    hand.add_tile(Tile::Wan(8));
    hand.add_tile(Tile::Wan(9));
    hand.add_tile(Tile::Wan(9));
    hand.add_tile(Tile::Tong(1));
    hand.add_tile(Tile::Tong(2));
    hand.add_tile(Tile::Tong(3));

    c.bench_function("win_check_normal", |b| {
        let mut checker = WinChecker::new();
        b.iter(|| {
            black_box(checker.check_win(black_box(&hand)));
        });
    });
}

fn bench_win_check_seven_pairs(c: &mut Criterion) {
    let mut hand = Hand::new();
    // 七对
    for rank in [1, 2, 3, 4, 5, 6, 7] {
        hand.add_tile(Tile::Wan(rank));
        hand.add_tile(Tile::Wan(rank));
    }

    c.bench_function("win_check_seven_pairs", |b| {
        let mut checker = WinChecker::new();
        b.iter(|| {
            black_box(checker.check_win(black_box(&hand)));
        });
    });
}

criterion_group!(benches, bench_win_check_normal, bench_win_check_seven_pairs);
criterion_main!(benches);

