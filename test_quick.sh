#!/bin/bash
# 快速测试脚本 - 使用更少的对象和更低的采样数

set -e

OUTPUT_DIR="output/test_quick"
IMAGE_INDEX=0
SEED=1000

echo "=========================================="
echo "快速测试（低复杂度）"
echo "=========================================="
echo "输出目录: $OUTPUT_DIR"
echo "图像索引: $IMAGE_INDEX"
echo "随机种子: $SEED"
echo "=========================================="
echo ""

# 运行生成 - 使用更少的对象和更低的采样数
blenderproc run generate_mountainous_solar_site.py "$OUTPUT_DIR" \
    --image_index "$IMAGE_INDEX" \
    --seed "$SEED" \
    --use_clusters \
    --num_clusters 2 \
    --min_piles_per_cluster 20 \
    --max_piles_per_cluster 30 \
    --render_width 1920 \
    --render_height 1080 \
    --max_samples 25 \
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

