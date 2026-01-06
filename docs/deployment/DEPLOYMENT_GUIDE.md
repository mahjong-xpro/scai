# 部署指南

## 目录

1. [系统要求](#系统要求)
2. [环境准备](#环境准备)
3. [Rust 环境配置](#rust-环境配置)
4. [Python 环境配置](#python-环境配置)
5. [构建 Rust 扩展](#构建-rust-扩展)
6. [安装 Python 依赖](#安装-python-依赖)
7. [配置文件设置](#配置文件设置)
8. [GPU 配置](#gpu-配置)
9. [验证安装](#验证安装)
10. [启动训练](#启动训练)
11. [监控和管理](#监控和管理)
12. [故障排查](#故障排查)
13. [性能优化](#性能优化)

---

## 系统要求

### 硬件要求

#### 最低配置
- **CPU**: 4 核心
- **内存**: 8GB RAM
- **存储**: 20GB 可用空间
- **GPU**: 可选（CPU 模式）

#### 推荐配置（当前服务器）
- **CPU**: 多核心（16+ 核心）
- **内存**: 64GB+ RAM
- **存储**: 100GB+ 可用空间（用于 checkpoints 和 logs）
- **GPU**: 8x NVIDIA RTX 4090（24GB 显存/卡）
  - 使用前 4 张 GPU（GPU 0, 1, 2, 3）

### 软件要求

#### 操作系统
- **Linux**: Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- **macOS**: 10.15+ (仅用于开发，生产环境建议 Linux)
- **Windows**: 不支持（可通过 WSL2 运行）

#### 必需软件
- **Rust**: 1.70.0+ (用于构建游戏引擎)
- **Python**: 3.8+ (推荐 3.9 或 3.10)
- **CUDA**: 11.8+ (如果使用 GPU)
- **cuDNN**: 8.6+ (如果使用 GPU)
- **Git**: 2.0+

#### 可选软件
- **Docker**: 20.10+ (容器化部署)
- **tmux/screen**: (后台运行训练)

---

## 环境准备

### 1. 系统更新

```bash
# Ubuntu/Debian
sudo apt update
sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 2. 安装基础工具

```bash
# Ubuntu/Debian
sudo apt install -y \
    build-essential \
    curl \
    wget \
    git \
    pkg-config \
    libssl-dev \
    cmake \
    python3-dev \
    python3-pip \
    python3-venv

# CentOS/RHEL
sudo yum groupinstall -y "Development Tools"
sudo yum install -y \
    curl \
    wget \
    git \
    pkgconfig \
    openssl-devel \
    cmake \
    python3-devel \
    python3-pip
```

### 3. 检查 GPU（如果使用）

```bash
# 检查 NVIDIA 驱动
nvidia-smi

# 应该显示类似输出：
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 525.xx.xx    Driver Version: 525.xx.xx    CUDA Version: 12.0  |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
# | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
# |===============================+======================+======================|
# |   0  NVIDIA RTX 4090    Off  | 00000000:00:1E.0 Off |                  Off |
# | 30%   45C    P0    50W / 450W |      0MiB / 24576MiB |      0%      Default |
# ...
```

如果 `nvidia-smi` 命令不存在，需要安装 NVIDIA 驱动：

```bash
# Ubuntu/Debian
sudo apt install -y nvidia-driver-525  # 根据你的 GPU 型号选择驱动版本

# 重启系统
sudo reboot
```

---

## Rust 环境配置

### 1. 安装 Rust

```bash
# 使用官方安装脚本（推荐）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 按照提示选择默认选项（1 - Proceed with installation）

# 加载 Rust 环境
source $HOME/.cargo/env

# 验证安装
rustc --version
cargo --version
```

### 2. 配置 Rust 工具链

```bash
# 安装稳定版工具链（如果默认不是）
rustup default stable

# 更新 Rust
rustup update

# 添加编译目标（如果需要交叉编译）
# rustup target add x86_64-unknown-linux-gnu
```

### 3. 安装 maturin（用于构建 Python 扩展）

```bash
# 使用 cargo 安装
cargo install maturin

# 验证安装
maturin --version
```

**注意**: 如果安装失败，可能需要安装额外的系统依赖：

```bash
# Ubuntu/Debian
sudo apt install -y \
    python3-dev \
    libffi-dev \
    libssl-dev

# CentOS/RHEL
sudo yum install -y \
    python3-devel \
    libffi-devel \
    openssl-devel
```

---

## Python 环境配置

### 1. 创建虚拟环境

```bash
# 进入项目目录
cd /path/to/scai/python

# 创建虚拟环境（推荐使用项目根目录）
cd /path/to/scai
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows (WSL2)

# 验证虚拟环境
which python  # 应该显示 .venv/bin/python
python --version
```

### 2. 升级 pip

```bash
pip install --upgrade pip setuptools wheel
```

### 3. 安装系统级 Python 依赖（如果需要）

```bash
# Ubuntu/Debian
sudo apt install -y \
    python3-numpy \
    python3-yaml

# CentOS/RHEL
sudo yum install -y \
    python3-numpy \
    python3-pyyaml
```

---

## 构建 Rust 扩展

### 1. 进入 Rust 目录

```bash
cd /path/to/scai/rust
```

### 2. 检查 Rust 项目配置

```bash
# 查看 Cargo.toml
cat Cargo.toml | head -20

# 检查是否有编译错误
cargo check
```

### 3. 构建 Python 扩展

#### 方法 1: 使用 maturin（如果可用，推荐）

```bash
# 确保虚拟环境已激活
source ../.venv/bin/activate

# 安装 maturin（如果未安装）
cargo install maturin

# 开发模式构建（会安装到虚拟环境）
maturin develop --release
```

#### 方法 2: 手动编译脚本（推荐，不需要 maturin）⭐

如果无法安装 maturin，使用手动构建脚本：

```bash
# 确保虚拟环境已激活
source ../.venv/bin/activate

# 运行手动构建脚本
chmod +x build_manual.sh
./build_manual.sh
```

**优点**: 
- 不需要 maturin
- 只需要 Rust 和 Python
- 自动化程度高

详细说明请参考: [Rust 构建替代方案](../deployment/RUST_BUILD_ALTERNATIVES.md)

#### 方法 3: 使用 setuptools

```bash
# 确保虚拟环境已激活
source ../.venv/bin/activate

# 使用 setuptools 构建脚本
python3 build_with_setuptools.py build_ext --inplace
python3 build_with_setuptools.py install
```

#### 方法 4: 完全手动编译

如果以上方法都不可用，可以完全手动编译：

```bash
# 1. 编译 Rust 库
cargo build --release --features python

# 2. 查找生成的库文件
# Linux:
find target/release -name "libscai_engine.so"
# macOS:
find target/release -name "libscai_engine.dylib"

# 3. 手动安装（参考 RUST_BUILD_ALTERNATIVES.md）
```

详细步骤请参考: [Rust 构建替代方案](../deployment/RUST_BUILD_ALTERNATIVES.md)

### 4. 验证 Rust 扩展

```bash
# 在 Python 中测试
python -c "import scai_engine; print('✓ scai_engine 导入成功')"
python -c "import scai_engine; engine = scai_engine.PyGameEngine(); print('✓ 游戏引擎创建成功')"
python -c "
import scai_engine
engine = scai_engine.PyGameEngine()
engine.initialize()
print('✓ 引擎初始化成功')
"
```

如果出现错误，检查：
- Rust 是否正确安装
- Python 版本是否匹配 (3.8+)
- 虚拟环境是否激活
- 系统依赖是否完整
- 库文件路径是否正确

**如果 maturin 安装失败，强烈推荐使用方法 2（手动编译脚本）**

---

## 安装 Python 依赖

### 1. 安装训练框架依赖

```bash
# 进入 Python 目录
cd /path/to/scai/python

# 确保虚拟环境已激活
source ../.venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 验证关键依赖

```bash
# 检查 PyTorch
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"
python -c "import torch; print(f'GPU count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')"

# 检查 Ray
python -c "import ray; print(f'Ray: {ray.__version__}')"

# 检查其他依赖
python -c "import numpy, yaml, tqdm; print('✓ 基础依赖正常')"
```

### 3. 安装 CUDA 版本的 PyTorch（如果使用 GPU）

如果 `torch.cuda.is_available()` 返回 `False`，可能需要安装 CUDA 版本的 PyTorch：

```bash
# 卸载 CPU 版本
pip uninstall torch torchvision torchaudio

# 安装 CUDA 11.8 版本（根据你的 CUDA 版本选择）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 或 CUDA 12.1 版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

验证 CUDA：

```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU')"
```

---

## 配置文件设置

### 1. 复制配置文件模板

```bash
cd /path/to/scai/python

# 如果 config.yaml 不存在，从模板创建
# cp config.yaml.example config.yaml  # 如果有模板
```

### 2. 编辑配置文件

```bash
# 使用你喜欢的编辑器
vim config.yaml
# 或
nano config.yaml
```

### 3. 关键配置项

#### GPU 配置（8 卡服务器，使用前 4 张）

```yaml
gpu:
  enabled: true
  device_ids: [0, 1, 2, 3]  # 使用前 4 张 GPU
```

#### Ray 配置

```yaml
ray:
  init: true
  num_cpus: null  # 自动检测
  num_gpus: null  # 自动检测（会根据 gpu.device_ids 计算）
```

#### 训练配置

```yaml
training:
  batch_size: 4096
  num_iterations: 1000
  learning_rate: 3e-4
  save_interval: 100  # 每 100 次迭代保存一次
```

#### 自对弈配置

```yaml
selfplay:
  num_workers: 80  # 每张 GPU 约 20 个 worker
  games_per_worker: 10
```

#### 日志配置

```yaml
logging:
  log_dir: ./logs
  log_level: INFO
  console_output: true
  metrics_logging: true
```

### 4. 创建必要目录

```bash
# 创建 checkpoints 目录
mkdir -p checkpoints

# 创建 logs 目录
mkdir -p logs

# 创建 coach_documents 目录（如果使用课程学习）
mkdir -p coach_documents
```

---

## GPU 配置

### 1. 验证 GPU 可见性

```bash
# 检查所有 GPU
nvidia-smi

# 检查 PyTorch 能看到的 GPU
python -c "import torch; print(f'PyTorch sees {torch.cuda.device_count()} GPU(s)')"
```

### 2. 配置 GPU 使用

在 `config.yaml` 中设置：

```yaml
gpu:
  enabled: true
  device_ids: [0, 1, 2, 3]  # 使用前 4 张 GPU
```

### 3. 验证 GPU 配置

启动训练后，检查日志输出：

```
Using GPUs: [0, 1, 2, 3] (CUDA_VISIBLE_DEVICES=0,1,2,3)
PyTorch will see 4 GPU(s) as cuda:0 to cuda:3
Ray initialized with 4 GPU(s)
```

### 4. 监控 GPU 使用

```bash
# 实时监控 GPU
watch -n 1 nvidia-smi

# 或使用更详细的工具
gpustat -i 1
```

详细 GPU 配置请参考：[GPU 配置指南](../setup/GPU_CONFIGURATION.md)

---

## 验证安装

### 1. 运行完整验证脚本

创建验证脚本 `verify_installation.py`：

```python
#!/usr/bin/env python3
"""验证安装是否完整"""

import sys

def check_import(module_name, package_name=None):
    """检查模块是否可以导入"""
    try:
        __import__(module_name)
        print(f"✓ {package_name or module_name} 导入成功")
        return True
    except ImportError as e:
        print(f"✗ {package_name or module_name} 导入失败: {e}")
        return False

def main():
    print("=" * 60)
    print("验证安装")
    print("=" * 60)
    
    all_ok = True
    
    # 检查 Rust 扩展
    print("\n[1] 检查 Rust 扩展...")
    if not check_import("scai_engine", "scai_engine (Rust 扩展)"):
        all_ok = False
        print("  提示: 运行 'cd rust && maturin develop'")
    
    # 检查 PyTorch
    print("\n[2] 检查 PyTorch...")
    if check_import("torch", "PyTorch"):
        import torch
        print(f"  版本: {torch.__version__}")
        print(f"  CUDA 可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  GPU 数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
    else:
        all_ok = False
    
    # 检查 Ray
    print("\n[3] 检查 Ray...")
    if check_import("ray", "Ray"):
        import ray
        print(f"  版本: {ray.__version__}")
    else:
        all_ok = False
    
    # 检查其他依赖
    print("\n[4] 检查其他依赖...")
    dependencies = [
        ("numpy", "NumPy"),
        ("yaml", "PyYAML"),
        ("tqdm", "tqdm"),
    ]
    for module, name in dependencies:
        if not check_import(module, name):
            all_ok = False
    
    # 检查项目模块
    print("\n[5] 检查项目模块...")
    project_modules = [
        ("scai.models", "模型模块"),
        ("scai.training", "训练模块"),
        ("scai.selfplay", "自对弈模块"),
        ("scai.utils", "工具模块"),
    ]
    for module, name in project_modules:
        if not check_import(module, name):
            all_ok = False
    
    # 测试游戏引擎
    print("\n[6] 测试游戏引擎...")
    try:
        import scai_engine
        engine = scai_engine.PyGameEngine()
        engine.initialize()
        print("✓ 游戏引擎创建和初始化成功")
    except Exception as e:
        print(f"✗ 游戏引擎测试失败: {e}")
        all_ok = False
    
    # 总结
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ 所有检查通过！安装成功。")
        return 0
    else:
        print("✗ 部分检查失败，请根据提示修复。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

运行验证：

```bash
cd /path/to/scai/python
source ../.venv/bin/activate
python verify_installation.py
```

### 2. 快速测试

```bash
# 测试导入
python -c "from scai.models import DualResNet; print('✓ 模型导入成功')"

# 测试游戏引擎
python -c "import scai_engine; e = scai_engine.PyGameEngine(); e.initialize(); print('✓ 引擎初始化成功')"

# 测试训练脚本（不实际训练）
python train.py --config config.yaml --help
```

---

## 启动训练

### 1. 基本训练

```bash
cd /path/to/scai/python
source ../.venv/bin/activate

# 启动训练
python train.py --config config.yaml
```

### 2. 从 Checkpoint 恢复

```bash
# 恢复最新 checkpoint
python train.py --config config.yaml --resume checkpoints/latest.pt

# 恢复特定 checkpoint
python train.py --config config.yaml --resume checkpoints/checkpoint_iter_100_1234567890.pt
```

### 3. 仅评估模式

```bash
# 评估模型（不训练）
python train.py --config config.yaml --eval-only --checkpoint checkpoints/checkpoint_iter_100_1234567890.pt
```

### 4. 后台运行（使用 tmux）

```bash
# 创建新的 tmux 会话
tmux new -s training

# 在 tmux 中启动训练
cd /path/to/scai/python
source ../.venv/bin/activate
python train.py --config config.yaml

# 分离会话: Ctrl+B, 然后按 D
# 重新连接: tmux attach -t training
# 查看所有会话: tmux ls
```

### 5. 后台运行（使用 screen）

```bash
# 创建新的 screen 会话
screen -S training

# 在 screen 中启动训练
cd /path/to/scai/python
source ../.venv/bin/activate
python train.py --config config.yaml

# 分离会话: Ctrl+A, 然后按 D
# 重新连接: screen -r training
# 查看所有会话: screen -ls
```

### 6. 使用 nohup（简单后台运行）

```bash
cd /path/to/scai/python
source ../.venv/bin/activate

# 后台运行，输出到 nohup.out
nohup python train.py --config config.yaml > training.log 2>&1 &

# 查看进程
ps aux | grep train.py

# 查看日志
tail -f training.log
```

---

## 监控和管理

### 1. 查看训练日志

```bash
# 实时查看日志
tail -f logs/training_*.log

# 查看最近的日志
ls -lt logs/ | head -5

# 搜索错误
grep -i error logs/training_*.log
```

### 2. 查看训练指标

```bash
# 查看指标 JSON 文件
cat logs/metrics_*.json | jq '.' | less

# 或使用 Python
python -c "
import json
with open('logs/metrics_20240101_120000.json') as f:
    data = json.load(f)
    print(json.dumps(data, indent=2))
"
```

### 3. 监控 GPU 使用

```bash
# 实时监控
watch -n 1 nvidia-smi

# 使用 gpustat（需要安装: pip install gpustat）
gpustat -i 1

# 查看 GPU 内存使用
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv
```

### 4. 监控系统资源

```bash
# CPU 和内存使用
htop
# 或
top

# 磁盘使用
df -h
du -sh checkpoints/ logs/

# 网络使用（如果使用分布式训练）
iftop
```

### 5. Web 仪表板（如果启用）

如果启用了课程学习 Web 仪表板：

```bash
# 访问仪表板
# 浏览器打开: http://localhost:5000
# 或: http://服务器IP:5000
```

### 6. Ray Dashboard（如果使用 Ray）

```bash
# Ray 会自动启动 dashboard
# 访问: http://localhost:8265
# 或: http://服务器IP:8265
```

---

## 故障排查

### 1. Rust 扩展构建失败

**问题**: `maturin develop` 失败

**解决方案**:
```bash
# 检查 Rust 版本
rustc --version  # 需要 1.70.0+

# 更新 Rust
rustup update

# 清理构建缓存
cd rust
cargo clean
rm -rf target/

# 重新构建
maturin develop --release
```

### 2. PyTorch CUDA 不可用

**问题**: `torch.cuda.is_available()` 返回 `False`

**解决方案**:
```bash
# 检查 CUDA 版本
nvidia-smi  # 查看 CUDA Version

# 检查 PyTorch CUDA 版本
python -c "import torch; print(torch.version.cuda)"

# 如果不匹配，重新安装匹配的 PyTorch
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 3. Ray 初始化失败

**问题**: `ray.init()` 失败

**解决方案**:
```bash
# 检查端口是否被占用
netstat -tulpn | grep 8265  # Ray dashboard 端口
netstat -tulpn | grep 10001  # Ray 默认端口

# 杀死占用端口的进程
kill -9 <PID>

# 或指定不同的端口
# 在代码中: ray.init(..., _temp_dir="/tmp/ray")
```

### 4. GPU 内存不足 (OOM)

**问题**: `CUDA out of memory`

**解决方案**:
```yaml
# 减少 batch_size
training:
  batch_size: 2048  # 从 4096 减少到 2048

# 减少 worker 数量
selfplay:
  num_workers: 40  # 从 80 减少到 40

# 使用更少的 GPU
gpu:
  device_ids: [0, 1]  # 只使用 2 张 GPU
```

### 5. 数据收集失败

**问题**: Worker 崩溃或数据收集失败

**解决方案**:
```bash
# 检查日志
grep -i error logs/training_*.log

# 减少 worker 数量
# 在 config.yaml 中:
selfplay:
  num_workers: 20  # 减少 worker 数量

# 检查系统资源
free -h  # 内存
df -h    # 磁盘空间
```

### 6. Checkpoint 加载失败

**问题**: 无法加载 checkpoint

**解决方案**:
```bash
# 检查 checkpoint 文件
ls -lh checkpoints/

# 验证 checkpoint 完整性
python -c "
import torch
ckpt = torch.load('checkpoints/latest.pt', map_location='cpu')
print('Keys:', list(ckpt.keys()))
print('Iteration:', ckpt.get('iteration', 'N/A'))
"

# 使用非严格模式加载
# 在代码中: trainer.load_checkpoint(path, strict=False)
```

### 7. 导入错误

**问题**: `ModuleNotFoundError: No module named 'scai_engine'`

**解决方案**:
```bash
# 确保虚拟环境已激活
source .venv/bin/activate

# 重新构建 Rust 扩展
cd rust
maturin develop

# 验证安装
python -c "import scai_engine; print('OK')"
```

### 8. 权限问题

**问题**: 权限被拒绝

**解决方案**:
```bash
# 检查文件权限
ls -la

# 修复权限
chmod +x train.py
chmod -R 755 python/

# 如果使用 Docker，检查挂载权限
```

---

## 性能优化

### 1. 编译优化

```bash
# Rust release 模式构建（更快但构建时间更长）
cd rust
maturin develop --release

# 或设置环境变量
export CARGO_PROFILE_RELEASE_OPT_LEVEL=3
export CARGO_PROFILE_RELEASE_LTO=true
maturin build --release
```

### 2. PyTorch 优化

```python
# 在训练脚本中启用优化
torch.backends.cudnn.benchmark = True  # 如果输入大小固定
torch.backends.cudnn.deterministic = False  # 如果不需要完全确定性
```

### 3. Ray 优化

```yaml
# 在 config.yaml 中
ray:
  init: true
  num_cpus: 32  # 手动指定 CPU 数量
  num_gpus: 4   # 手动指定 GPU 数量
  object_store_memory: 20000000000  # 20GB 对象存储
```

### 4. 批次大小优化

根据 GPU 内存调整：

```yaml
training:
  # RTX 4090 (24GB) 推荐配置
  batch_size: 4096  # 单 GPU
  # 如果使用 4 张 GPU，可以增加到 8192 或 16384
```

### 5. Worker 数量优化

```yaml
selfplay:
  # 每张 GPU 约 10-20 个 worker
  # 4 张 GPU × 20 = 80 workers
  num_workers: 80
  games_per_worker: 10
```

### 6. 数据收集优化

```yaml
selfplay:
  # 减少验证开销
  validate_data: true
  strict_validation: false  # 非严格模式更快
```

---

## 部署检查清单

### 安装前
- [ ] 系统要求满足（CPU、内存、存储、GPU）
- [ ] 系统软件已更新
- [ ] 基础工具已安装

### Rust 环境
- [ ] Rust 1.70.0+ 已安装
- [ ] maturin 已安装
- [ ] Rust 工具链已配置

### Python 环境
- [ ] Python 3.8+ 已安装
- [ ] 虚拟环境已创建
- [ ] pip 已升级

### 构建和安装
- [ ] Rust 扩展构建成功
- [ ] Python 依赖安装成功
- [ ] PyTorch CUDA 版本正确（如果使用 GPU）

### 配置
- [ ] config.yaml 已配置
- [ ] GPU 配置正确（如果使用）
- [ ] 必要目录已创建

### 验证
- [ ] 验证脚本通过
- [ ] 游戏引擎测试成功
- [ ] GPU 可见性正确

### 启动
- [ ] 训练脚本可以运行
- [ ] 日志输出正常
- [ ] GPU 使用正常（如果使用）

---

## 快速参考

### 常用命令

```bash
# 激活虚拟环境
source .venv/bin/activate

# 构建 Rust 扩展
cd rust && maturin develop

# 启动训练
cd python && python train.py --config config.yaml

# 查看日志
tail -f logs/training_*.log

# 监控 GPU
watch -n 1 nvidia-smi

# 检查进程
ps aux | grep train.py
```

### 配置文件位置

- 主配置: `python/config.yaml`
- 日志目录: `python/logs/`
- Checkpoint 目录: `python/checkpoints/`
- 文档目录: `python/coach_documents/`

### 重要端口

- Ray Dashboard: `8265`
- Web 仪表板: `5000`（如果启用）

---

## 获取帮助

### 文档资源

- [GPU 配置指南](../setup/GPU_CONFIGURATION.md)
- [训练指南](../training/TRAINING_GUIDE.md)
- [课程学习指南](../training/CURRICULUM_LEARNING.md)
- [故障排查指南](./TROUBLESHOOTING.md)

### 日志文件

- 训练日志: `logs/training_*.log`
- 指标文件: `logs/metrics_*.json`
- Ray 日志: `~/.ray/logs/`

### 常见问题

查看 [故障排查](#故障排查) 部分获取常见问题的解决方案。

---

*最后更新: 2024年*
*适用于: SCAI v0.1.0*

