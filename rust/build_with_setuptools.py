#!/usr/bin/env python3
"""
使用 setuptools 构建和安装 Rust 扩展（不使用 maturin）

这个脚本会：
1. 编译 Rust 代码为动态库
2. 使用 setuptools 安装到 Python 环境
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

# 项目根目录
ROOT_DIR = Path(__file__).parent
RUST_DIR = ROOT_DIR
PYTHON_DIR = ROOT_DIR.parent / "python"


class RustExtension(Extension):
    """Rust 扩展定义"""
    def __init__(self, name, rust_path):
        super().__init__(name, sources=[])
        self.rust_path = rust_path


class RustBuildExt(build_ext):
    """构建 Rust 扩展"""
    
    def run(self):
        """运行构建"""
        print("构建 Rust 扩展...")
        
        # 检查 Rust
        if not shutil.which("cargo"):
            raise RuntimeError("cargo 未找到。请先安装 Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
        
        # 构建 Rust 库
        print("编译 Rust 代码...")
        result = subprocess.run(
            ["cargo", "build", "--release", "--features", "python"],
            cwd=RUST_DIR,
            check=True,
        )
        
        # 确定库文件路径
        if sys.platform == "darwin":
            lib_name = "libscai_engine.dylib"
        elif sys.platform.startswith("linux"):
            lib_name = "libscai_engine.so"
        elif sys.platform.startswith("win"):
            lib_name = "scai_engine.dll"
        else:
            raise RuntimeError(f"不支持的操作系统: {sys.platform}")
        
        lib_path = RUST_DIR / "target" / "release" / lib_name
        
        if not lib_path.exists():
            raise RuntimeError(f"编译失败: 未找到 {lib_path}")
        
        print(f"✓ 编译成功: {lib_path}")
        
        # 复制到构建目录
        build_lib = Path(self.build_lib)
        build_lib.mkdir(parents=True, exist_ok=True)
        
        ext_dir = build_lib / "scai_engine"
        ext_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制库文件
        if sys.platform == "darwin":
            target_name = "scai_engine.dylib"
        elif sys.platform.startswith("linux"):
            target_name = "scai_engine.so"
        else:
            target_name = lib_name
        
        shutil.copy2(lib_path, ext_dir / target_name)
        print(f"✓ 复制到: {ext_dir / target_name}")
        
        # 创建 __init__.py
        init_py = ext_dir / "__init__.py"
        init_py.write_text(self._generate_init_py(target_name))
        print(f"✓ 创建: {init_py}")
    
    def _generate_init_py(self, lib_name: str) -> str:
        """生成 __init__.py 内容"""
        return f'''"""SCAI Engine - Rust 游戏引擎 Python 绑定"""

import os
import sys
from pathlib import Path

# 获取当前模块目录
_MODULE_DIR = Path(__file__).parent

# 库文件路径
_LIB_PATH = _MODULE_DIR / "{lib_name}"

if not _LIB_PATH.exists():
    raise ImportError(
        f"scai_engine library not found at {{_LIB_PATH}}. "
        "Please rebuild the extension."
    )

# 使用 pyo3 的导入机制
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("scai_engine", str(_LIB_PATH))
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create module spec from {{_LIB_PATH}}")
    
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
        f"Failed to load scai_engine from {{_LIB_PATH}}: {{e}}"
    ) from e

__all__ = [
    "PyGameEngine",
    "PyGameState", 
    "PyActionMask",
    "state_to_tensor",
    "action_mask_to_array",
]
'''


setup(
    name="scai-engine",
    version="0.1.0",
    description="SCAI Mahjong Engine - Rust Python Extension",
    ext_modules=[RustExtension("scai_engine", RUST_DIR)],
    cmdclass={"build_ext": RustBuildExt},
    zip_safe=False,
)

