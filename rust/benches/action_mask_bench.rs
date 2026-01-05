use criterion::{black_box, criterion_group, criterion_main, Criterion};
use scai_engine::engine::action_mask::ActionMask;
use scai_engine::tile::{Hand, Tile, Suit};
use scai_engine::game::state::GameState;

fn bench_action_mask_can_win(c: &mut Criterion) {
    let mut hand = Hand::new();
    hand.add_tile(Tile::Wan(1));
    hand.add_tile(Tile::Tong(1));
    let state = GameState::new();
    let mask = ActionMask::new();

    c.bench_function("action_mask_can_win", |b| {
        b.iter(|| {
            black_box(mask.can_win(
                black_box(&hand),
                black_box(&Tile::Wan(1)),
                black_box(&state),
                black_box(Some(Suit::Tiao)),
                black_box(1),
            ));
        });
    });
}

criterion_group!(benches, bench_action_mask_can_win);
criterion_main!(benches);

