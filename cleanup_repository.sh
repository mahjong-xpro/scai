#!/bin/bash
# 清理仓库中的大文件脚本
# 从 Git 中移除构建产物和虚拟环境，但保留本地文件

set -e

echo "开始清理仓库..."

# 1. 从 Git 中移除 .venv（但保留本地文件）
if git ls-files | grep -q "^\.venv/"; then
    echo "移除 .venv/ 目录（从 Git 跟踪中）..."
    git rm -r --cached .venv
    echo "✓ .venv/ 已从 Git 跟踪中移除"
else
    echo "✓ .venv/ 未被 Git 跟踪"
fi

# 2. 从 Git 中移除 rust/target（但保留本地文件）
if git ls-files | grep -q "^rust/target/"; then
    echo "移除 rust/target/ 目录（从 Git 跟踪中）..."
    git rm -r --cached rust/target
    echo "✓ rust/target/ 已从 Git 跟踪中移除"
else
    echo "✓ rust/target/ 未被 Git 跟踪"
fi

# 3. 检查并更新 .gitignore
echo ""
echo "检查 .gitignore..."
if ! grep -q "^\.venv/" .gitignore; then
    echo "警告: .gitignore 中缺少 .venv/"
    echo "已自动添加到 .gitignore"
fi

# 4. 显示清理结果
echo ""
echo "清理完成！"
echo ""
echo "下一步："
echo "1. 检查更改: git status"
echo "2. 提交更改: git commit -m 'chore: 从仓库中移除构建产物和虚拟环境'"
echo "3. 清理 Git 历史（可选）: git gc --aggressive --prune=now"
echo ""
echo "注意：本地文件不会被删除，只是从 Git 跟踪中移除。"

