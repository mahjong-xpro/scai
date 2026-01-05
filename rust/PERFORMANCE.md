# 性能优化文档

## 性能目标

- **胡牌判定**：< 10μs
- **番数计算**：< 1μs
- **动作掩码生成**：< 5μs

## 已实施的优化

### 1. 内联优化
- `WinChecker::check_win()` - 主要入口函数
- `WinChecker::check_seven_pairs()` - 快速路径
- `WinChecker::hand_hash()` - 缓存哈希计算
- `WinChecker::is_pure_suit()` - 清一色检查
- `BaseFansCalculator::base_fans()` - 基础番数计算
- `RootCounter::count_roots()` - 根数统计
- `ActionFlags::count()` - 动作统计
- `Settlement::total_fans()` - 总番数计算

### 2. 缓存优化
- 限制缓存大小（默认 1000 个条目）
- 简单的 LRU 策略：缓存满时清空
- 使用 `HashMap` 进行快速查找

### 3. 内存优化
- 使用 `SmallVec` 优化小数组（已实现）
- 使用 `#[repr(C)]` 确保内存布局（已实现）
- 使用 `Box<[T]>` 优化固定大小数组（已实现）

### 4. 算法优化
- 七对检查使用快速路径
- 递归回溯算法优化
- 位运算优化（已实现）

## 性能测试

### 运行基准测试

```bash
# 运行所有基准测试
cargo bench

# 运行特定基准测试
cargo bench --bench win_check_bench
cargo bench --bench scoring_bench
cargo bench --bench action_mask_bench

# 使用脚本运行
./scripts/benchmark.sh
```

### 性能回归测试

```bash
# 运行性能回归测试
./scripts/performance_check.sh
```

## CI/CD 集成

性能测试已集成到 GitHub Actions 工作流中（`.github/workflows/performance.yml`）。

## 性能分析工具

### 使用 perf（Linux）

```bash
perf record cargo bench --bench win_check_bench
perf report
```

### 使用 flamegraph

```bash
cargo install flamegraph
cargo flamegraph --bench win_check_bench
```

## 未来优化方向

1. **更智能的缓存策略**：实现真正的 LRU 缓存
2. **SIMD 优化**：使用 SIMD 指令加速位运算
3. **并行化**：对独立的手牌判定进行并行处理
4. **预计算表**：为常见牌型创建预计算表

