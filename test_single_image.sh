#!/bin/bash
# 快速测试单张图像生成

set -e

OUTPUT_DIR="output/test_single"
IMAGE_INDEX=0
SEED=1000

echo "=========================================="
echo "单张图像生成测试"
echo "=========================================="
echo "输出目录: $OUTPUT_DIR"
echo "图像索引: $IMAGE_INDEX"
echo "随机种子: $SEED"
echo "=========================================="
echo ""

# 清理旧文件（可选）
# rm -rf "$OUTPUT_DIR"

# 运行生成（生产环境参数）
blenderproc run generate_mountainous_solar_site.py "$OUTPUT_DIR" \
    --image_index "$IMAGE_INDEX" \
    --seed "$SEED" \
    --use_clusters \
    --use_advanced_features \
    --use_gpu \
    --max_samples 50 \
    --render_width 5280 \
    --render_height 3956

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "检查输出："
echo "  图像: $OUTPUT_DIR/images/$(printf "%06d" $IMAGE_INDEX).png"
echo "  标注: $OUTPUT_DIR/labels/$(printf "%06d" $IMAGE_INDEX).txt"
echo ""
echo "查看图像："
echo "  open $OUTPUT_DIR/images/$(printf "%06d" $IMAGE_INDEX).png"
echo ""

