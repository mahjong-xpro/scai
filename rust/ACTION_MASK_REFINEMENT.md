# 动作掩码精细化：定缺色限制

## 问题描述

顶级 AI 容易在初期学坏。例如在定缺色没打完时尝试胡牌（虽然规则不允许，但 AI 会去试）。

## 整改方案

`get_legal_actions` 函数必须极其严格。在定缺色未打完时，强制 Mask 掉所有非定缺色的出牌、碰、杠。

## 实现细节

### 1. 定缺色状态检查

使用 `Player::has_declared_suit_tiles()` 检查玩家是否还有定缺门的牌：

```rust
let has_declared_suit_tiles = player.has_declared_suit_tiles();
let declared_suit = player.declared_suit;
```

### 2. 出牌动作限制

**规则**：如果还有定缺门的牌，只能出定缺色的牌，不能出其他牌。

```rust
if has_declared_suit_tiles {
    // 如果还有定缺门的牌，只能出定缺色的牌
    if let Some(declared) = declared_suit {
        if tile.suit() == declared {
            mask.can_discard.push(*tile);
        }
    }
} else {
    // 定缺门已打完，可以出任何牌
    mask.can_discard.push(*tile);
}
```

### 3. 碰牌动作限制

**规则**：如果还有定缺门的牌，不能碰非定缺色的牌。

```rust
if let Some(pongable) = PongHandler::get_pongable_tile(player, &tile) {
    if has_declared_suit_tiles {
        // 如果还有定缺门的牌，只能碰定缺色的牌
        if let Some(declared) = declared_suit {
            if tile.suit() == declared {
                mask.can_pong.push(pongable);
            }
        }
    } else {
        // 定缺门已打完，可以碰任何牌
        mask.can_pong.push(pongable);
    }
}
```

### 4. 杠牌动作限制

**规则**：如果还有定缺门的牌，不能杠非定缺色的牌（包括直杠、加杠、暗杠）。

```rust
// 直杠（响应别人的出牌）
if KongHandler::can_direct_kong(player, &tile).is_some() {
    if has_declared_suit_tiles {
        if let Some(declared) = declared_suit {
            if tile.suit() == declared {
                mask.can_gang.push(tile);
            }
        }
    } else {
        mask.can_gang.push(tile);
    }
}

// 加杠和暗杠（自己的回合）
for (tile, _) in player.hand.tiles_map() {
    if has_declared_suit_tiles {
        if let Some(declared) = declared_suit {
            if tile.suit() != declared {
                continue; // 跳过非定缺色的牌
            }
        }
    }
    // 检查加杠和暗杠
    ...
}
```

### 5. 胡牌动作限制

**规则**：如果还有定缺门的牌，不能胡非定缺色的牌。

```rust
if has_declared_suit_tiles {
    if let Some(declared) = declared_suit {
        if tile.suit() != declared {
            // 严格屏蔽：定缺色未打完时，不能胡非定缺色的牌
            return false;
        }
    }
}
```

### 6. validate_action 严格验证

在 `validate_action` 方法中也加强检查，确保所有动作都经过定缺色验证：

```rust
// 碰牌动作
if player.has_declared_suit_tiles() {
    if let Some(declared) = player.declared_suit {
        if tile.suit() != declared {
            return false; // 定缺色未打完，不能碰非定缺色的牌
        }
    }
}

// 杠牌动作
if player.has_declared_suit_tiles() {
    if let Some(declared) = player.declared_suit {
        if tile.suit() != declared {
            return false; // 定缺色未打完，不能杠非定缺色的牌
        }
    }
}

// 胡牌动作
if player.has_declared_suit_tiles() {
    if let Some(declared) = player.declared_suit {
        if tile.suit() != declared {
            return false; // 定缺色未打完，不能胡非定缺色的牌
        }
    }
}
```

## 测试覆盖

### 测试用例

1. **定缺色未打完时的出牌限制**
   - ✅ 只能出定缺色的牌
   - ✅ 不能出非定缺色的牌

2. **定缺色已打完后的出牌**
   - ✅ 可以出任何牌

3. **响应别人出牌时的碰牌限制**
   - ✅ 定缺色未打完时，不能碰非定缺色的牌
   - ✅ 定缺色未打完时，可以碰定缺色的牌

4. **响应别人出牌时的杠牌限制**
   - ✅ 定缺色未打完时，不能杠非定缺色的牌
   - ✅ 定缺色未打完时，可以杠定缺色的牌

5. **响应别人出牌时的胡牌限制**
   - ✅ 定缺色未打完时，不能胡非定缺色的牌

## 关键改进

### 1. 统一检查逻辑

所有动作（出牌、碰、杠、胡）都使用相同的定缺色检查逻辑：

```rust
if has_declared_suit_tiles {
    if let Some(declared) = declared_suit {
        if tile.suit() != declared {
            // 屏蔽该动作
        }
    }
}
```

### 2. 双重验证

- **生成阶段**：在 `generate` 方法中严格限制动作掩码
- **验证阶段**：在 `validate_action` 方法中再次验证

### 3. 防止 AI 学坏

通过严格的动作掩码，确保 AI 在训练初期就不会尝试非法动作，避免学习到错误的策略。

## 性能影响

- **检查开销**：每次生成动作掩码时，需要检查 `has_declared_suit_tiles()`，时间复杂度 O(n)，n 为手牌中不同牌的数量（通常 < 10）
- **内存开销**：无额外内存开销
- **总体影响**：可忽略不计

## 实现完成

✅ 出牌动作限制
✅ 碰牌动作限制
✅ 杠牌动作限制（直杠、加杠、暗杠）
✅ 胡牌动作限制
✅ validate_action 严格验证
✅ 完整测试覆盖

动作掩码已精细化，确保在定缺色未打完时，严格屏蔽所有非定缺色的动作，防止 AI 在训练初期学坏。

