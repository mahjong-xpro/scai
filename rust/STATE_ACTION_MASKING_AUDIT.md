# 状态转移与动作掩码审计 (State & Action Masking Audit)

## 审计结果

### ✅ 1. 定缺强制作业

**检查项**：只要 `player.hand` 里还有 `lack_color`（定缺色）的牌，除了打出（Discard）这些牌，其他所有碰、杠、胡动作是否都已被返回的 Mask 彻底封死？

**代码位置**：
- `rust/src/engine/action_mask.rs` - `ActionMask::generate()` 方法
- `rust/src/engine/action_mask.rs` - `ActionMask::validate_action()` 方法

**验证结果**：✅ **正确实现**

#### 实现细节

1. **胡牌动作（can_win）**：
   - 第 129 行：如果 `has_declared_suit_tiles && tile.suit() != declared`，则不会添加到 `can_win`
   - 第 501-506 行：`validate_action()` 中也有相同检查

2. **碰牌动作（can_pong）**：
   - 第 159-165 行：如果 `has_declared_suit_tiles`，只有当 `tile.suit() == declared` 时才添加到 `can_pong`
   - 第 467-472 行：`validate_action()` 中也有相同检查

3. **直杠动作（can_gang - 响应别人出牌）**：
   - 第 175-181 行：如果 `has_declared_suit_tiles`，只有当 `tile.suit() == declared` 时才添加到 `can_gang`
   - 第 480-485 行：`validate_action()` 中也有相同检查

4. **加杠/暗杠动作（can_gang - 自己回合）**：
   - 第 207-214 行：如果 `has_declared_suit_tiles`，只有当 `tile.suit() == declared` 时才添加到 `can_gang`
   - 第 480-485 行：`validate_action()` 中也有相同检查

5. **出牌动作（can_discard）**：
   - 第 191-197 行：如果 `has_declared_suit_tiles`，只有当 `tile.suit() == declared` 时才添加到 `can_discard`
   - 第 451-455 行：`validate_action()` 中也有相同检查

**结论**：✅ 当玩家手牌中还有定缺色的牌时，除了打出这些牌，其他所有碰、杠、胡动作都被 Mask 彻底封死。

---

### ✅ 2. 过胡状态解封

**检查项**：在 `Player` 结构体里，`passed_hu_fan` 是否在 `draw_card`（摸牌）事件触发时被重置为 `None`？

**代码位置**：
- `rust/src/game/player.rs` - `Player::clear_passed_win()` 方法
- `rust/src/game/game_engine.rs` - `GameEngine::handle_draw()` 方法

**验证结果**：✅ **正确实现**

#### 实现细节

1. **清除方法**：
   ```rust
   // rust/src/game/player.rs 第 135-137 行
   pub fn clear_passed_win(&mut self) {
       self.passed_hu_fan = None;
   }
   ```

2. **摸牌时调用**：
   ```rust
   // rust/src/game/game_engine.rs 第 131-155 行
   fn handle_draw(&mut self, player_id: u8) -> Result<ActionResult, GameError> {
       // ...
       if let Some(tile) = self.wall.draw() {
           let player = &mut self.state.players[player_id as usize];
           player.hand.add_tile(tile);
           // 清除过胡锁定（规则：过胡锁定只在"下一次摸牌前"有效）
           player.clear_passed_win();  // ✅ 第 142 行
           // ...
       }
   }
   ```

3. **游戏主循环中的调用**：
   ```rust
   // rust/src/game/game_engine.rs 第 319-320 行
   // 当前玩家摸牌
   self.handle_draw(current_player)?;  // ✅ 会调用 clear_passed_win()
   ```

**结论**：✅ `passed_hu_fan` 在每次摸牌时都会被重置为 `None`，确保过胡锁定只在"下一次摸牌前"有效。

---

## 测试验证

### 测试用例 1：定缺强制作业

**场景**：玩家定缺万子，手牌中还有万子，尝试碰/杠/胡非万子的牌

**预期**：
- ✅ 不能碰非万子的牌
- ✅ 不能杠非万子的牌
- ✅ 不能胡非万子的牌
- ✅ 只能出万子的牌

### 测试用例 2：过胡状态解封

**场景**：玩家放弃了一次点炮（记录 `passed_hu_fan`），然后摸牌

**预期**：
- ✅ 摸牌后 `passed_hu_fan` 被重置为 `None`
- ✅ 可以再次胡牌（不受过胡限制）

---

## 总结

- ✅ **定缺强制作业**：正确实现，所有非定缺色的碰、杠、胡动作都被 Mask 封死
- ✅ **过胡状态解封**：正确实现，每次摸牌时都会清除过胡锁定

两个关键逻辑都已正确实现，无需修改。

