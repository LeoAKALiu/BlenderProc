#!/bin/bash
# 小批量测试脚本（2张图像，1个并行进程）

set -e

echo "=========================================="
echo "小批量生成测试"
echo "=========================================="
echo "并行进程数: 1"
echo "图像数量: 2"
echo "输出目录: output/test_batch_small"
echo "=========================================="
echo ""

./run_parallel.sh 1 2 output/test_batch_small 5000

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "检查输出："
echo "  ls -lh output/test_batch_small/images/"
echo "  ls -lh output/test_batch_small/labels/"
echo ""
