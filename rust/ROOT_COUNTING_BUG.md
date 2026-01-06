# 根数统计逻辑审计报告

## 问题描述

在四川麻将中，番数是 $2^n$ 的指数增长，最容易出错的是"根（Gen）"的统计。

### 核心规则

1. **根的定义**：只要手牌中有 4 张相同的牌（无论是否开杠），就是 1 个根
2. **常见错误**：将"杠"等同于"根"
3. **正确逻辑**：
   - 如果手牌中有 4 张相同的牌（未开杠），计算 1 个根
   - 如果 4 张相同的牌被开杠了（变成 `Meld::Kong`），也应该计算 1 个根
   - **关键**：同一个 4 张相同的牌，不能既在手牌中计算，又在 `melds` 中计算

### 番数计算示例

如果是"带幺九"加"2个根"，结算应该是：
- 基础番：带幺九 = 4（$2^2$）
- 根数：2 个根
- 总番数：$4 \times 2^2 = 16$ 倍

## 当前实现分析

### 当前代码（`rust/src/game/scoring.rs:28-47`）

```rust
pub fn count_roots(hand: &Hand, melds: &[Meld]) -> u8 {
    let mut root_count = 0u8;

    // 统计手牌中 4 张相同牌的数量
    for (_, &count) in hand.tiles_map() {
        if count == 4 {
            root_count += 1;
        }
    }

    // 统计已开杠的牌
    for meld in melds {
        if matches!(meld, Meld::Kong { .. }) {
            root_count += 1;
        }
    }

    // 确保不超过 4 个根
    root_count.min(4)
}
```

### 潜在问题

1. **逻辑正确性**：
   - ✅ 如果手牌中有 4 张相同的牌（未开杠），计算 1 个根
   - ✅ 如果 4 张相同的牌被开杠了，它们会从手牌中移除，变成 `Meld::Kong`，计算 1 个根
   - ✅ 不会重复计算（因为开杠后手牌中不再有这 4 张牌）

2. **但是**：当前实现依赖于"开杠后手牌中不再有这 4 张牌"的假设。如果这个假设不成立，就会重复计算。

3. **更安全的实现**：使用统一的计数器数组，统计所有可见牌（手牌 + 碰/杠），避免重复计算。

## 改进方案

### 方案1：使用统一的计数器数组（推荐）

建立一个计数器数组，统计所有可见牌（手牌 + 碰/杠），计数为 4 的张数即为根的总数。

```rust
pub fn count_roots(hand: &Hand, melds: &[Meld]) -> u8 {
    // 建立计数器数组：27 种牌（3 种花色 × 9 种牌）
    let mut tile_counts = [0u8; 27];
    
    // 统计手牌中的牌
    for (tile, &count) in hand.tiles_map() {
        if let Some(idx) = tile_to_index(tile) {
            tile_counts[idx] += count;
        }
    }
    
    // 统计已碰/杠的牌
    for meld in melds {
        match meld {
            Meld::Triplet { tile } => {
                // 碰：3 张相同的牌
                if let Some(idx) = tile_to_index(tile) {
                    tile_counts[idx] += 3;
                }
            }
            Meld::Kong { tile, .. } => {
                // 杠：4 张相同的牌
                if let Some(idx) = tile_to_index(tile) {
                    tile_counts[idx] += 4;
                }
            }
        }
    }
    
    // 统计计数为 4 的张数（即为根的总数）
    let mut root_count = 0u8;
    for &count in &tile_counts {
        if count == 4 {
            root_count += 1;
        }
    }
    
    // 确保不超过 4 个根
    root_count.min(4)
}
```

### 方案2：保持当前逻辑，但添加验证

如果当前实现已经正确（开杠后手牌中不再有这 4 张牌），可以保持当前逻辑，但添加验证确保不会重复计算。

## 测试用例

### 测试1：手牌中有 4 张相同的牌（未开杠）

```rust
let mut hand = Hand::new();
// 4 张 1 万（1 个根）
for _ in 0..4 {
    hand.add_tile(Tile::Wan(1));
}
let roots = RootCounter::count_roots(&hand, &[]);
assert_eq!(roots, 1);
```

### 测试2：已开杠的牌

```rust
let hand = Hand::new();
let melds = vec![
    Meld::Kong { tile: Tile::Wan(1), is_concealed: true },
];
let roots = RootCounter::count_roots(&hand, &melds);
assert_eq!(roots, 1);
```

### 测试3：手牌中有 4 张相同的牌 + 已开杠的牌（不同牌）

```rust
let mut hand = Hand::new();
// 4 张 1 万（1 个根）
for _ in 0..4 {
    hand.add_tile(Tile::Wan(1));
}
let melds = vec![
    Meld::Kong { tile: Tile::Tong(5), is_concealed: true },
];
let roots = RootCounter::count_roots(&hand, &melds);
assert_eq!(roots, 2); // 1 万（手牌）+ 5 筒（杠）= 2 个根
```

### 测试4：带幺九 + 2 个根

```rust
// 基础番：带幺九 = 4（2^2）
// 根数：2 个根
// 总番数：4 × 2^2 = 16
let settlement = Settlement::new(4, 2, 0);
assert_eq!(settlement.total_fans(), Some(16));
```

## 结论

当前实现**逻辑上是正确的**，但**不够健壮**。建议使用统一的计数器数组来统计所有可见牌，这样可以：

1. 避免重复计算的潜在风险
2. 逻辑更清晰，易于理解和维护
3. 符合用户建议的实现方式

