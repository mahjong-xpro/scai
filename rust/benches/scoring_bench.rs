use criterion::{black_box, criterion_group, criterion_main, Criterion};
use scai_engine::game::scoring::{Settlement, BaseFansCalculator, RootCounter, ActionFlags};
use scai_engine::tile::{Hand, Tile};
use scai_engine::tile::win_check::{WinType, WinResult};
use smallvec::SmallVec;

fn bench_base_fans(c: &mut Criterion) {
    c.bench_function("base_fans_all_types", |b| {
        b.iter(|| {
            for win_type in [
                WinType::Normal,
                WinType::AllTriplets,
                WinType::SevenPairs,
                WinType::PureSuit,
                WinType::AllTerminals,
                WinType::GoldenHook,
                WinType::PureAllTriplets,
                WinType::PureSevenPairs,
                WinType::PureGoldenHook,
                WinType::DragonSevenPairs,
                WinType::PureDragonSevenPairs,
            ] {
                black_box(BaseFansCalculator::base_fans(black_box(win_type)));
            }
        });
    });
}

fn bench_count_roots(c: &mut Criterion) {
    let mut hand = Hand::new();
    // 4 张相同牌
    for _ in 0..4 {
        hand.add_tile(Tile::Wan(1));
    }
    let melds = vec![];

    c.bench_function("count_roots", |b| {
        b.iter(|| {
            black_box(RootCounter::count_roots(black_box(&hand), black_box(&melds)));
        });
    });
}

fn bench_settlement_total_fans(c: &mut Criterion) {
    let settlement = Settlement::new(16, 2, 1);

    c.bench_function("settlement_total_fans", |b| {
        b.iter(|| {
            black_box(settlement.total_fans());
        });
    });
}

fn bench_settlement_calculate(c: &mut Criterion) {
    let win_result = WinResult {
        is_win: true,
        win_type: WinType::PureSevenPairs,
        pair: None,
        groups: SmallVec::new(),
    };
    let actions = ActionFlags {
        is_zi_mo: true,
        ..Default::default()
    };

    c.bench_function("settlement_calculate", |b| {
        b.iter(|| {
            black_box(Settlement::calculate(
                black_box(&win_result),
                black_box(1),
                black_box(&actions),
            ));
        });
    });
}

criterion_group!(
    benches,
    bench_base_fans,
    bench_count_roots,
    bench_settlement_total_fans,
    bench_settlement_calculate
);
criterion_main!(benches);

