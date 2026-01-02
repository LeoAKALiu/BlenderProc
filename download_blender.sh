#!/bin/bash
# 手动下载 Blender 的辅助脚本

set -e

echo "正在下载 Blender 4.2.1 for macOS ARM64..."
echo ""

# 设置下载路径
DOWNLOAD_DIR="$HOME/Downloads"
BLENDER_DMG="$DOWNLOAD_DIR/blender-4.2.1-macos-arm64.dmg"
BLENDER_URL="https://download.blender.org/release/Blender4.2/blender-4.2.1-macos-arm64.dmg"

# 检查是否已下载
if [ -f "$BLENDER_DMG" ]; then
    echo "✓ Blender DMG 文件已存在: $BLENDER_DMG"
    echo "  请手动安装: 双击打开 DMG 文件，将 Blender.app 拖到 Applications 文件夹"
    exit 0
fi

# 尝试下载（使用 curl，通常 SSL 证书问题较少）
echo "使用 curl 下载..."
if curl -L -o "$BLENDER_DMG" "$BLENDER_URL"; then
    echo ""
    echo "✓ 下载完成: $BLENDER_DMG"
    echo ""
    echo "下一步："
    echo "1. 打开下载的文件: open $BLENDER_DMG"
    echo "2. 将 Blender.app 拖到 Applications 文件夹"
    echo "3. 然后运行:"
    echo "   blenderproc run generate_solar_farm_dataset.py output/solar_farm \\"
    echo "     --custom-blender-path \"/Applications/Blender.app/Contents/MacOS/Blender\" \\"
    echo "     --num_cameras 5"
else
    echo ""
    echo "✗ 下载失败。请手动下载："
    echo "  访问: https://www.blender.org/download/"
    echo "  或直接链接: $BLENDER_URL"
    exit 1
fi






