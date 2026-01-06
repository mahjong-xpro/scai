#!/bin/bash
# 手动构建 Rust Python 扩展脚本（不使用 maturin）
# 适用于无法安装 maturin 的环境

set -e

echo "开始手动构建 Rust Python 扩展..."

# 检查 Rust 是否安装
if ! command -v rustc &> /dev/null; then
    echo "错误: Rust 未安装。请先安装 Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: Python 3 未安装"
    exit 1
fi

# 获取 Python 版本和路径
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_INCLUDE=$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))")
PYTHON_LIBDIR=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")

echo "Python 版本: $PYTHON_VERSION"
echo "Python 头文件路径: $PYTHON_INCLUDE"
echo "Python 库目录: $PYTHON_LIBDIR"

# 检查 PyO3 依赖
echo "检查 PyO3 依赖..."
if ! grep -q "pyo3" Cargo.toml; then
    echo "错误: Cargo.toml 中未找到 pyo3 依赖"
    exit 1
fi

# 设置环境变量
export PYO3_PYTHON=python3
export PYO3_NO_PYTHON_VERSION_MESSAGE=1

# 构建 release 版本
echo "构建 release 版本..."
cargo build --release --features python

# 查找生成的 .so 文件
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    LIB_EXT="so"
    LIB_NAME="libscai_engine.so"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    LIB_EXT="dylib"
    LIB_NAME="libscai_engine.dylib"
else
    echo "错误: 不支持的操作系统: $OSTYPE"
    exit 1
fi

LIB_PATH="target/release/$LIB_NAME"

if [ ! -f "$LIB_PATH" ]; then
    echo "错误: 未找到编译后的库文件: $LIB_PATH"
    echo "请检查 Cargo.toml 中的 crate-type 配置"
    exit 1
fi

echo "✓ 编译成功: $LIB_PATH"

# 获取 Python site-packages 路径
SITE_PACKAGES=$(python3 -c "import site; print(site.getsitepackages()[0])")
echo "Python site-packages: $SITE_PACKAGES"

# 创建安装目录
INSTALL_DIR="$SITE_PACKAGES/scai_engine"
mkdir -p "$INSTALL_DIR"

# 复制库文件
echo "安装到: $INSTALL_DIR"
cp "$LIB_PATH" "$INSTALL_DIR/scai_engine.$LIB_EXT"

# 创建 __init__.py
cat > "$INSTALL_DIR/__init__.py" << 'EOF'
"""SCAI Engine - Rust 游戏引擎 Python 绑定"""

import os
import sys
from pathlib import Path

# 获取当前模块目录
_MODULE_DIR = Path(__file__).parent

# 确定库文件扩展名
if sys.platform == "darwin":
    _LIB_EXT = "dylib"
elif sys.platform.startswith("linux"):
    _LIB_EXT = "so"
elif sys.platform.startswith("win"):
    _LIB_EXT = "dll"
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}")

# 库文件路径
_LIB_PATH = _MODULE_DIR / f"scai_engine.{_LIB_EXT}"

if not _LIB_PATH.exists():
    raise ImportError(
        f"scai_engine library not found at {_LIB_PATH}. "
        "Please run: cd rust && ./build_manual.sh"
    )

# 使用 pyo3 的导入机制
try:
    # PyO3 扩展模块会自动处理导入
    import importlib.util
    spec = importlib.util.spec_from_file_location("scai_engine", str(_LIB_PATH))
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create module spec from {_LIB_PATH}")
    
    # 加载模块
    _module = importlib.util.module_from_spec(spec)
    sys.modules["scai_engine"] = _module
    spec.loader.exec_module(_module)
    
    # 导出主要类
    PyGameEngine = _module.PyGameEngine
    PyGameState = _module.PyGameState
    PyActionMask = _module.PyActionMask
    state_to_tensor = _module.state_to_tensor
    action_mask_to_array = _module.action_mask_to_array
    
except Exception as e:
    raise ImportError(
        f"Failed to load scai_engine from {_LIB_PATH}: {e}\n"
        "This might be a compatibility issue. Please check:\n"
        "1. Python version matches the build (3.8+)\n"
        "2. Library dependencies are available\n"
        "3. Run: cd rust && cargo clean && ./build_manual.sh"
    ) from e

__all__ = [
    "PyGameEngine",
    "PyGameState", 
    "PyActionMask",
    "state_to_tensor",
    "action_mask_to_array",
]
EOF

echo "✓ 安装完成！"
echo ""
echo "验证安装:"
echo "  python3 -c 'import scai_engine; print(\"✓ scai_engine 导入成功\")'"
echo ""
echo "如果导入失败，请检查:"
echo "  1. Python 版本是否匹配 (3.8+)"
echo "  2. 库文件权限"
echo "  3. 依赖库是否完整"

