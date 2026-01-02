#!/bin/bash
# 安装 BlenderProc 所需的所有依赖包到 Blender 的 Python 环境

BLENDER_PYTHON="/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11"

if [ ! -f "$BLENDER_PYTHON" ]; then
    echo "错误: 找不到 Blender Python: $BLENDER_PYTHON"
    echo "请确保 Blender 已安装在 /Applications/Blender.app"
    exit 1
fi

echo "正在安装 BlenderProc 依赖包到 Blender Python 环境..."
echo ""

# 核心依赖
$BLENDER_PYTHON -m pip install --upgrade pip wheel

# BlenderProc 需要的依赖（根据文档和实际使用）
$BLENDER_PYTHON -m pip install \
    pyyaml \
    imageio \
    scipy \
    scikit-image \
    pypng \
    gitpython \
    trimesh \
    matplotlib \
    numpy \
    Pillow \
    h5py \
    opencv-python \
    scikit-learn \
    rich \
    python-dateutil \
    pytz

echo ""
echo "✓ 依赖安装完成！"
echo ""
echo "现在可以运行脚本："
echo "export PATH=\"/Users/leo/Library/Python/3.12/bin:\$PATH\""
echo "blenderproc run generate_solar_farm_dataset.py output/solar_farm \\"
echo "  --custom-blender-path \"/Applications/Blender.app\" \\"
echo "  --num_cameras 5"

