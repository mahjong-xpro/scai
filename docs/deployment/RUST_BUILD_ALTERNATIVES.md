# Rust 扩展构建替代方案

## 问题

如果无法安装 `maturin`，可以使用以下替代方案构建 Rust Python 扩展。

## 方案 1: 手动编译脚本（推荐）

### 步骤

1. **进入 Rust 目录**
   ```bash
   cd rust
   ```

2. **运行手动构建脚本**
   ```bash
   chmod +x build_manual.sh
   ./build_manual.sh
   ```

3. **验证安装**
   ```bash
   python3 -c "import scai_engine; print('✓ 导入成功')"
   ```

### 工作原理

- 使用 `cargo build --release --features python` 直接编译
- 自动查找生成的 `.so` 或 `.dylib` 文件
- 复制到 Python 的 `site-packages` 目录
- 创建 `__init__.py` 用于导入

### 优点

- 不需要 maturin
- 只需要 Rust 和 Python
- 自动化程度高

### 缺点

- 需要手动处理库文件路径
- 跨平台兼容性需要测试

---

## 方案 2: 使用 setuptools（更标准）

### 步骤

1. **进入 Rust 目录**
   ```bash
   cd rust
   ```

2. **运行 setuptools 构建脚本**
   ```bash
   python3 build_with_setuptools.py build_ext --inplace
   python3 build_with_setuptools.py install
   ```

   或者直接安装：
   ```bash
   pip install -e .  # 如果 setup.py 存在
   ```

3. **验证安装**
   ```bash
   python3 -c "import scai_engine; print('✓ 导入成功')"
   ```

### 工作原理

- 使用 `setuptools` 的 `build_ext` 命令
- 自动编译 Rust 代码
- 自动安装到 Python 环境

### 优点

- 使用标准 Python 构建工具
- 更好的集成到 Python 包管理
- 支持开发模式安装

### 缺点

- 需要创建 `setup.py` 或使用构建脚本

---

## 方案 3: 完全手动编译（最基础）

### 步骤

1. **编译 Rust 库**
   ```bash
   cd rust
   cargo build --release --features python
   ```

2. **查找生成的库文件**
   ```bash
   # Linux
   find target/release -name "libscai_engine.so"
   
   # macOS
   find target/release -name "libscai_engine.dylib"
   ```

3. **手动复制到 Python 路径**
   ```bash
   # 获取 Python site-packages 路径
   python3 -c "import site; print(site.getsitepackages()[0])"
   
   # 创建目录
   mkdir -p $(python3 -c "import site; print(site.getsitepackages()[0])")/scai_engine
   
   # 复制库文件（Linux 示例）
   cp target/release/libscai_engine.so \
      $(python3 -c "import site; print(site.getsitepackages()[0])")/scai_engine/scai_engine.so
   ```

4. **创建 __init__.py**
   
   创建文件：`$(python3 -c "import site; print(site.getsitepackages()[0])")/scai_engine/__init__.py`
   
   内容：
   ```python
   """SCAI Engine - Rust 游戏引擎 Python 绑定"""
   
   import os
   import sys
   from pathlib import Path
   
   _MODULE_DIR = Path(__file__).parent
   
   if sys.platform == "darwin":
       _LIB_EXT = "dylib"
   elif sys.platform.startswith("linux"):
       _LIB_EXT = "so"
   else:
       raise RuntimeError(f"Unsupported platform: {sys.platform}")
   
   _LIB_PATH = _MODULE_DIR / f"scai_engine.{_LIB_EXT}"
   
   if not _LIB_PATH.exists():
       raise ImportError(f"scai_engine library not found at {_LIB_PATH}")
   
   try:
       import importlib.util
       spec = importlib.util.spec_from_file_location("scai_engine", str(_LIB_PATH))
       if spec is None or spec.loader is None:
           raise ImportError(f"Failed to create module spec")
       
       _module = importlib.util.module_from_spec(spec)
       sys.modules["scai_engine"] = _module
       spec.loader.exec_module(_module)
       
       PyGameEngine = _module.PyGameEngine
       PyGameState = _module.PyGameState
       PyActionMask = _module.PyActionMask
       state_to_tensor = _module.state_to_tensor
       action_mask_to_array = _module.action_mask_to_array
       
   except Exception as e:
       raise ImportError(f"Failed to load scai_engine: {e}") from e
   
   __all__ = ["PyGameEngine", "PyGameState", "PyActionMask", "state_to_tensor", "action_mask_to_array"]
   ```

5. **验证**
   ```bash
   python3 -c "import scai_engine; print('✓ 导入成功')"
   ```

### 优点

- 完全控制
- 不需要额外工具
- 适合调试

### 缺点

- 步骤繁琐
- 容易出错
- 需要手动处理路径

---

## 方案 4: 使用虚拟环境中的路径（推荐用于开发）

### 步骤

1. **激活虚拟环境**
   ```bash
   source .venv/bin/activate  # 或你的虚拟环境路径
   ```

2. **编译到虚拟环境**
   ```bash
   cd rust
   cargo build --release --features python
   ```

3. **创建符号链接或复制**
   ```bash
   # 获取虚拟环境的 site-packages
   VENV_SITE=$(python -c "import site; print(site.getsitepackages()[0])")
   
   # 创建目录
   mkdir -p "$VENV_SITE/scai_engine"
   
   # 复制库文件
   cp target/release/libscai_engine.so "$VENV_SITE/scai_engine/scai_engine.so"
   
   # 创建 __init__.py（使用方案 3 的内容）
   # ...
   ```

### 优点

- 隔离环境
- 不影响系统 Python
- 适合开发

---

## 常见问题

### Q1: 编译失败，提示找不到 pyo3

**解决方案**:
```bash
# 检查 Cargo.toml 中是否有 pyo3 依赖
grep pyo3 rust/Cargo.toml

# 如果没有，需要添加
cd rust
cargo add pyo3 --features extension-module,abi3-py38
```

### Q2: 导入时提示 "undefined symbol"

**原因**: PyO3 版本不匹配或 Python 版本不匹配

**解决方案**:
```bash
# 检查 Python 版本
python3 --version  # 需要 3.8+

# 检查 PyO3 配置
grep "abi3-py" rust/Cargo.toml  # 应该匹配 Python 版本

# 清理并重新编译
cd rust
cargo clean
cargo build --release --features python
```

### Q3: 找不到编译后的库文件

**原因**: crate-type 配置不正确

**解决方案**:
检查 `rust/Cargo.toml`:
```toml
[lib]
name = "scai_engine"
crate-type = ["cdylib", "rlib"]  # 必须有 cdylib
```

### Q4: 权限错误

**解决方案**:
```bash
# 检查文件权限
ls -l target/release/libscai_engine.so

# 如果需要，修改权限
chmod 755 target/release/libscai_engine.so
```

### Q5: 在虚拟环境中找不到模块

**原因**: 库文件安装到了系统 Python 而不是虚拟环境

**解决方案**:
- 确保虚拟环境已激活
- 使用虚拟环境的 Python 路径
- 检查 `sys.path` 是否包含虚拟环境路径

---

## 推荐方案

### 开发环境
使用 **方案 1（手动编译脚本）** 或 **方案 4（虚拟环境）**

### 生产环境
使用 **方案 2（setuptools）** 或创建 wheel 包分发

### 快速测试
使用 **方案 3（完全手动）** 进行一次性测试

---

## 验证安装

无论使用哪种方案，最后都要验证：

```bash
# 1. 检查模块是否可以导入
python3 -c "import scai_engine; print('✓ 导入成功')"

# 2. 检查主要类
python3 -c "from scai_engine import PyGameEngine; print('✓ PyGameEngine 可用')"

# 3. 测试创建引擎
python3 -c "
import scai_engine
engine = scai_engine.PyGameEngine()
engine.initialize()
print('✓ 引擎创建和初始化成功')
"
```

---

## 更新部署文档

如果使用替代方案，更新 `DEPLOYMENT_GUIDE.md` 中的构建步骤：

```markdown
### 构建 Rust 扩展（不使用 maturin）

如果无法安装 maturin，可以使用手动构建脚本：

```bash
cd rust
chmod +x build_manual.sh
./build_manual.sh
```

详细说明请参考: [Rust 构建替代方案](./RUST_BUILD_ALTERNATIVES.md)
```

---

*最后更新: 2024年*

