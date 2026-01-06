# 仓库大小分析报告

## 问题
代码打包后发现总大小为 **1.4G**，远超预期。

## 分析结果

### 主要占用空间的文件/目录

1. **`rust/target/` 目录: ~1.0G** ⚠️
   - Rust 构建产物（编译后的二进制文件、库文件等）
   - 包含 `debug/` 和 `release/` 构建
   - 包含增量编译缓存（incremental compilation cache）
   - **应该被忽略，不应提交到仓库**

2. **`.venv/` 目录: ~29M** ⚠️
   - Python 虚拟环境
   - 包含所有 Python 依赖包
   - **应该被忽略，不应提交到仓库**

3. **`.git/` 目录: ~17M**
   - Git 仓库元数据
   - 这是正常的，但可以通过清理历史减小

### 实际代码大小

- **`python/` 目录: 468K** ✅
- **`rust/src/` 目录: 很小** ✅
- **`docs/` 目录: 196K** ✅
- **其他文档: ~100K** ✅

**实际代码大小应该只有 ~1MB 左右**

## 问题原因

虽然 `.gitignore` 文件中已经包含了：
```
/target/
rust/target/
venv/
.venv/
```

但是这些目录可能在添加到 `.gitignore` **之前**就已经被提交到 Git 仓库中了。Git 只会忽略未被跟踪的文件，已经跟踪的文件即使添加到 `.gitignore` 也不会被自动忽略。

## 解决方案

### 方案 1: 从 Git 中移除已跟踪的大文件（推荐）

```bash
# 1. 从 Git 索引中移除（但保留本地文件）
git rm -r --cached rust/target
git rm -r --cached .venv

# 2. 确认 .gitignore 已正确配置
# 检查 .gitignore 中是否有：
#   /target/
#   rust/target/
#   venv/
#   .venv/

# 3. 提交更改
git add .gitignore
git commit -m "chore: 从仓库中移除构建产物和虚拟环境"

# 4. 清理 Git 历史（可选，减小 .git 目录大小）
git gc --aggressive --prune=now
```

### 方案 2: 使用 Git LFS（如果必须保留某些大文件）

如果将来需要跟踪某些大文件（如预训练模型），可以使用 Git LFS：

```bash
# 安装 Git LFS
git lfs install

# 跟踪大文件类型
git lfs track "*.pt"
git lfs track "*.pth"
git lfs track "*.ckpt"

# 提交 .gitattributes
git add .gitattributes
git commit -m "chore: 配置 Git LFS 跟踪大文件"
```

### 方案 3: 更新 .gitignore（确保完整）

确保 `.gitignore` 包含所有应该忽略的内容：

```gitignore
# Rust
/target/
rust/target/
**/*.rs.bk
Cargo.lock
rust/Cargo.lock

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/
build/
dist/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs
*.log

# Temporary files
*.tmp
*.temp

# OS
.DS_Store
Thumbs.db

# Project specific
*.md.bak

# Test and benchmark output
*.profdata

# Checkpoints and models (如果不想提交)
checkpoints/
*.pt
*.pth
*.ckpt
*.h5
*.pb

# Logs directory
logs/

# Coach documents (如果不想提交)
coach_documents/
```

## 验证步骤

### 1. 检查当前跟踪的大文件

```bash
# 查看被 Git 跟踪的大文件
git ls-files | xargs -I {} du -h {} 2>/dev/null | sort -hr | head -20
```

### 2. 检查 .gitignore 是否生效

```bash
# 测试 .gitignore 规则
git check-ignore -v rust/target .venv
```

### 3. 检查仓库大小

```bash
# Git 仓库大小
du -sh .git

# 工作目录大小（排除 .git）
du -sh --exclude=.git .
```

### 4. 清理后的预期大小

- **代码**: ~1MB
- **.git 目录**: ~5-10MB（清理后）
- **总计**: ~10-15MB

## 预防措施

### 1. 在项目开始时设置 .gitignore

在首次提交之前就设置好 `.gitignore`，避免提交不应该跟踪的文件。

### 2. 使用 pre-commit 钩子

创建 `.git/hooks/pre-commit` 检查是否有大文件：

```bash
#!/bin/bash
# 检查是否有大于 10MB 的文件
files=$(git diff --cached --name-only | xargs ls -lh 2>/dev/null | awk '{if ($5+0 > 10485760) print $9}')
if [ ! -z "$files" ]; then
    echo "警告: 以下文件大于 10MB:"
    echo "$files"
    read -p "是否继续提交? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
```

### 3. 定期清理

```bash
# 清理未跟踪的文件
git clean -fd

# 清理 Git 历史
git gc --aggressive --prune=now
```

## 总结

**当前问题**: 1.4G 的大小主要是因为：
- `rust/target/` (1.0G) - 构建产物
- `.venv/` (29M) - 虚拟环境
- `.git/` (17M) - Git 历史（可能包含已删除的大文件）

**解决方案**: 从 Git 中移除这些文件，它们应该只存在于本地，不应该提交到仓库。

**预期结果**: 清理后仓库大小应该只有 ~10-15MB。

---

*生成时间: 2024年*

