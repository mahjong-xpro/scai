# 快速开始指南

## 5 分钟快速部署

### 前提条件

- Linux 服务器（Ubuntu 20.04+）
- 8x NVIDIA RTX 4090 GPU（使用前 4 张）
- 已安装 NVIDIA 驱动和 CUDA

### 步骤 1: 安装 Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
cargo install maturin
```

### 步骤 2: 设置 Python 环境

```bash
cd /path/to/scai
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### 步骤 3: 构建 Rust 扩展

```bash
cd rust
maturin develop --release
cd ..
```

### 步骤 4: 安装 Python 依赖

```bash
cd python
pip install -r requirements.txt
```

### 步骤 5: 配置

编辑 `python/config.yaml`:

```yaml
gpu:
  enabled: true
  device_ids: [0, 1, 2, 3]
```

创建目录:

```bash
mkdir -p checkpoints logs coach_documents
```

### 步骤 6: 验证

```bash
python -c "import scai_engine; print('OK')"
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

### 步骤 7: 启动训练

```bash
python train.py --config config.yaml
```

---

## 详细文档

完整部署指南请参考: [部署指南](./DEPLOYMENT_GUIDE.md)

