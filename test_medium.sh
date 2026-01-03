#!/bin/bash
# 中等复杂度测试脚本

set -e

OUTPUT_DIR="output/test_medium"
IMAGE_INDEX=0
SEED=2000

echo "=========================================="
echo "中等复杂度测试"
echo "=========================================="
echo "输出目录: $OUTPUT_DIR"
echo "图像索引: $IMAGE_INDEX"
echo "随机种子: $SEED"
echo "=========================================="
echo ""

# 中等复杂度参数
blenderproc run generate_mountainous_solar_site.py "$OUTPUT_DIR" \
    --image_index "$IMAGE_INDEX" \
    --seed "$SEED" \
    --use_clusters \
    --num_clusters 3 \
    --min_piles_per_cluster 40 \
    --max_piles_per_cluster 60 \
    --render_width 2640 \
    --render_height 1978 \
    --max_samples 50 \
    --noise_threshold 0.03 \
    --use_gpu

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "检查输出："
echo "  图像: $OUTPUT_DIR/images/$(printf "%06d" $IMAGE_INDEX).png"
echo "  标注: $OUTPUT_DIR/labels/$(printf "%06d" $IMAGE_INDEX).txt"
echo ""

