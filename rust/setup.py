"""
使用 setuptools 构建和安装 Rust 扩展（不使用 maturin）

安装方法:
    python setup.py build_ext --inplace
    python setup.py install

或者:
    pip install -e .
"""

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import subprocess
import shutil
import sys
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent


class RustExtension(Extension):
    """Rust 扩展定义"""
    def __init__(self, name):
        super().__init__(name, sources=[])


class RustBuildExt(build_ext):
    """构建 Rust 扩展"""
    
    def run(self):
        """运行构建"""
        print("=" * 60)
        print("构建 Rust Python 扩展（不使用 maturin）")
        print("=" * 60)
        
        # 检查 Rust
        if not shutil.which("cargo"):
            raise RuntimeError(
                "cargo 未找到。请先安装 Rust:\n"
                "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            )
        
        # 检查 Cargo.toml
        cargo_toml = ROOT_DIR / "Cargo.toml"
        if not cargo_toml.exists():
            raise RuntimeError(f"Cargo.toml 未找到: {cargo_toml}")
        
        # 构建 Rust 库
        print("\n[1/3] 编译 Rust 代码...")
        print(f"工作目录: {ROOT_DIR}")
        
        result = subprocess.run(
            ["cargo", "build", "--release", "--features", "python"],
            cwd=ROOT_DIR,
            check=False,
        )
        
        if result.returncode != 0:
            raise RuntimeError("Rust 编译失败。请检查错误信息。")
        
        # 确定库文件路径和名称
        if sys.platform == "darwin":
            lib_name = "libscai_engine.dylib"
            target_name = "scai_engine.dylib"
        elif sys.platform.startswith("linux"):
            lib_name = "libscai_engine.so"
            target_name = "scai_engine.so"
        elif sys.platform.startswith("win"):
            lib_name = "scai_engine.dll"
            target_name = "scai_engine.dll"
        else:
            raise RuntimeError(f"不支持的操作系统: {sys.platform}")
        
        lib_path = ROOT_DIR / "target" / "release" / lib_name
        
        if not lib_path.exists():
            raise RuntimeError(
                f"编译失败: 未找到 {lib_path}\n"
                "请检查 Cargo.toml 中的 crate-type 配置（需要包含 'cdylib'）"
            )
        
        print(f"✓ 编译成功: {lib_path}")
        
        # 复制到构建目录
        print("\n[2/3] 安装到 Python 环境...")
        build_lib = Path(self.build_lib)
        build_lib.mkdir(parents=True, exist_ok=True)
        
        ext_dir = build_lib / "scai_engine"
        ext_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制库文件
        target_lib = ext_dir / target_name
        shutil.copy2(lib_path, target_lib)
        print(f"✓ 复制到: {target_lib}")
        
        # 创建 __init__.py
        print("\n[3/3] 创建 Python 模块...")
        init_py = ext_dir / "__init__.py"
        init_py.write_text(self._generate_init_py(target_name))
        print(f"✓ 创建: {init_py}")
        
        print("\n" + "=" * 60)
        print("✓ 构建完成！")
        print("=" * 60)
        print("\n验证安装:")
        print(f"  python -c 'import scai_engine; print(\"✓ 导入成功\")'")
    
    def _generate_init_py(self, lib_name: str) -> str:
        """生成 __init__.py 内容"""
        return f'''"""SCAI Engine - Rust 游戏引擎 Python 绑定

使用 PyO3 绑定的 Rust 游戏引擎。
"""

import os
import sys
from pathlib import Path

# 获取当前模块目录
_MODULE_DIR = Path(__file__).parent

# 库文件路径
_LIB_PATH = _MODULE_DIR / "{lib_name}"

if not _LIB_PATH.exists():
    raise ImportError(
        f"scai_engine library not found at {{_LIB_PATH}}.\\n"
        "Please rebuild the extension:\\n"
        "  cd rust && python setup.py build_ext --inplace"
    )

# PyO3 扩展模块导入
try:
    import importlib.util
    
    # 创建模块规范
    spec = importlib.util.spec_from_file_location("scai_engine", str(_LIB_PATH))
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create module spec from {{_LIB_PATH}}")
    
    # 加载模块
    _module = importlib.util.module_from_spec(spec)
    sys.modules["scai_engine"] = _module
    spec.loader.exec_module(_module)
    
    # 导出主要类和函数
    PyGameEngine = _module.PyGameEngine
    PyGameState = _module.PyGameState
    PyActionMask = _module.PyActionMask
    state_to_tensor = _module.state_to_tensor
    action_mask_to_array = _module.action_mask_to_array
    
except Exception as e:
    raise ImportError(
        f"Failed to load scai_engine from {{_LIB_PATH}}: {{e}}\\n"
        "This might be a compatibility issue. Please check:\\n"
        "1. Python version matches the build (3.8+)\\n"
        "2. Library dependencies are available\\n"
        "3. Run: cd rust && cargo clean && python setup.py build_ext --inplace"
    ) from e

__version__ = "0.1.0"
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
    description="SCAI Mahjong Engine - Rust Python Extension (Built without maturin)",
    long_description="""
    SCAI Mahjong Engine - 高性能 Rust 实现的麻将游戏引擎
    
    这个包使用 PyO3 将 Rust 游戏引擎暴露给 Python，用于强化学习训练。
    
    构建方法（不使用 maturin）:
        1. cd rust
        2. python setup.py build_ext --inplace
        3. python setup.py install
    
    或者使用手动构建脚本:
        cd rust && ./build_manual.sh
    """,
    ext_modules=[RustExtension("scai_engine")],
    cmdclass={"build_ext": RustBuildExt},
    zip_safe=False,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Rust",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

