#!/bin/bash
# 标准复杂度测试脚本（接近生产环境）

set -e

OUTPUT_DIR="output/test_standard"
IMAGE_INDEX=0
SEED=3000

echo "=========================================="
echo "标准复杂度测试（接近生产环境）"
echo "=========================================="
echo "输出目录: $OUTPUT_DIR"
echo "图像索引: $IMAGE_INDEX"
echo "随机种子: $SEED"
echo "=========================================="
echo ""

# 标准复杂度参数（接近真实数据）
blenderproc run generate_mountainous_solar_site.py "$OUTPUT_DIR" \
    --image_index "$IMAGE_INDEX" \
    --seed "$SEED" \
    --use_clusters \
    --num_clusters 5 \
    --min_piles_per_cluster 50 \
    --max_piles_per_cluster 80 \
    --render_width 5280 \
    --render_height 3956 \
    --max_samples 50 \
    --noise_threshold 0.05 \
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

