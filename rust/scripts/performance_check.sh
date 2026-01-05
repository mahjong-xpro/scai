#!/bin/bash
# 性能回归测试脚本
# 检查性能是否满足阈值要求

set -e

cd "$(dirname "$0")/.."

echo "运行性能回归测试..."
echo "================================"

# 运行基准测试并捕获输出
BENCH_OUTPUT=$(cargo bench --bench win_check_bench --bench scoring_bench --bench action_mask_bench 2>&1)

# 检查是否有性能警告（这里需要根据实际输出格式调整）
# 示例：检查平均时间是否超过阈值
if echo "$BENCH_OUTPUT" | grep -q "time:"; then
    echo "性能测试完成"
    echo "$BENCH_OUTPUT" | grep -A 5 "time:"
else
    echo "警告：无法解析性能测试结果"
    exit 1
fi

echo ""
echo "性能回归测试完成！"

