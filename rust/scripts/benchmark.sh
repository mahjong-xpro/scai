#!/bin/bash
# 性能基准测试脚本
# 用于运行基准测试并生成报告

set -e

cd "$(dirname "$0")/.."

echo "运行性能基准测试..."
echo "================================"

# 运行基准测试
cargo bench --bench win_check_bench --bench scoring_bench --bench action_mask_bench

echo ""
echo "基准测试完成！"
echo "结果保存在 target/criterion/ 目录中"

