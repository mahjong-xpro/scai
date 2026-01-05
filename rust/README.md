# SCAI Engine - 血战到底麻将游戏引擎

高性能的 Rust 实现的血战到底麻将游戏引擎，支持 Python 绑定用于强化学习训练。

## 功能特性

- ✅ **完整的游戏规则实现**：血战到底所有规则
- ✅ **高性能**：Rust 实现，支持大规模并发
- ✅ **Python 绑定**：通过 PyO3 提供 Python 接口
- ✅ **Tensor 转换**：直接转换为 NumPy 数组，零拷贝
- ✅ **动作掩码**：自动生成合法动作，防止非法操作
- ✅ **完整测试**：69 个单元测试和集成测试

## 快速开始

### 编译 Rust 库

```bash
cd rust
cargo build --release
```

### 编译 Python 扩展模块

```bash
cd rust
cargo build --release --features python
```

### 运行测试

```bash
# Rust 测试
cargo test

# Python 测试（需要先编译 Python 扩展）
cd ..
python tests/test_python_bindings.py
```

## 项目结构

```
rust/
├── src/
│   ├── tile/          # 牌相关：Tile, Hand, Wall, WinChecker
│   ├── game/          # 游戏逻辑：State, Engine, Scoring, Rules
│   ├── engine/        # 引擎：ActionMask
│   ├── python/        # Python 绑定
│   └── utils/         # 工具：位运算优化
├── tests/             # 集成测试
├── benches/           # 性能基准测试
└── Cargo.toml         # 项目配置
```

## 核心模块

### 1. 基础数据结构
- `Tile`: 牌（万、筒、条）
- `Hand`: 手牌（高效计数）
- `Wall`: 牌墙（洗牌、发牌）

### 2. 胡牌判定
- 平胡、七对、对对胡
- 清一色、清对、清七对
- 龙七对、清龙七对
- 金钩钓、清金钩钓
- 全带幺、全求人

### 3. 番数计算
- 基础番数映射
- 根数统计
- 动作触发番（自摸、杠上开花等）
- 倍率计算

### 4. 游戏引擎
- `GameEngine`: 游戏流程管理
- `GameState`: 游戏状态管理
- `ActionMask`: 合法动作生成

### 5. Python 绑定
- `PyGameState`: 游戏状态 Python 接口
- `PyActionMask`: 动作掩码 Python 接口
- `PyGameEngine`: 游戏引擎 Python 接口
- Tensor 转换函数

## 文档

- [PYTHON_BINDINGS.md](PYTHON_BINDINGS.md) - Python 绑定详细文档
- [PERFORMANCE.md](PERFORMANCE.md) - 性能优化文档
- [TESTING.md](TESTING.md) - 测试策略文档
- [COMPREHENSIVE_REVIEW.md](COMPREHENSIVE_REVIEW.md) - 代码审查报告
- [FIXES_COMPLETED.md](FIXES_COMPLETED.md) - 修复完成报告

## 性能

- 胡牌判定：< 1μs（缓存命中）
- 动作掩码生成：< 10μs
- Tensor 转换：< 100μs
- 内存占用：< 1MB per game

## 依赖

### Rust 依赖
- `pyo3`: Python 绑定
- `numpy`: NumPy 数组支持
- `rand`: 随机数生成
- `serde`: 序列化
- `smallvec`: 小数组优化

### Python 依赖
- Python 3.8+
- NumPy

## 许可证

[待定]

## 贡献

欢迎提交 Issue 和 Pull Request！

