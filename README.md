# SCAI - 血战到底麻将 AI 引擎

高性能的 Rust 实现的血战到底麻将游戏引擎，支持 Python 绑定用于强化学习训练。

## 项目概述

本项目旨在开发一个基于强化学习的血战到底麻将 AI，采用 Rust 实现高性能游戏引擎，通过 PyO3 提供 Python 接口，使用 PyTorch 进行神经网络训练。

## 技术栈

- **Rust**: 高性能游戏引擎实现
- **PyO3**: Python 绑定
- **PyTorch/JAX**: 深度学习框架（Python 端）
- **Ray/Tokio**: 分布式管理和异步并发

## 项目结构

```
scai/
├── rust/              # Rust 游戏引擎
│   ├── src/           # 源代码
│   ├── tests/         # 测试
│   └── benches/       # 性能基准测试
├── checklist.md       # 开发清单
├── 方案.md            # 技术方案
├── 胡牌规则.md        # 胡牌规则文档
└── tests/             # Python 测试
```

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
cd rust
cargo test

# Python 测试（需要先编译 Python 扩展）
cd ..
python tests/test_python_bindings.py
```

## 功能特性

- ✅ 完整的血战到底规则实现
- ✅ 所有胡牌类型判定
- ✅ 番数计算系统
- ✅ 动作处理（碰、杠、听牌）
- ✅ 游戏主循环
- ✅ Python 绑定
- ✅ Tensor 转换

## 文档

- [checklist.md](checklist.md) - 开发清单
- [方案.md](方案.md) - 技术方案
- [胡牌规则.md](胡牌规则.md) - 胡牌规则
- [rust/README.md](rust/README.md) - Rust 引擎文档
- [rust/PYTHON_BINDINGS.md](rust/PYTHON_BINDINGS.md) - Python 绑定文档

## 许可证

[待定]

## 贡献

欢迎提交 Issue 和 Pull Request！

