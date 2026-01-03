# 新生成脚本测试指南

本文档提供详细的测试步骤，帮助验证 `generate_mountainous_solar_site.py` 的功能。

## 🚀 快速测试（推荐首次使用）

### 步骤 1: 单张图像测试（最快验证）

```bash
# 基础测试（使用默认参数）
blenderproc run generate_mountainous_solar_site.py output/test \
    --image_index 0 \
    --seed 1000 \
    --use_clusters \
    --use_advanced_features \
    --use_gpu \
    --max_samples 50
```

**预期结果**：
- 生成 `output/test/images/000000.png`
- 生成 `output/test/labels/000000.txt`
- 控制台显示生成进度和统计信息

**检查点**：
```bash
# 检查输出文件
ls -lh output/test/images/000000.png
ls -lh output/test/labels/000000.txt

# 查看图像（如果系统支持）
open output/test/images/000000.png  # macOS
# 或
xdg-open output/test/images/000000.png  # Linux

# 查看标注文件内容
cat output/test/labels/000000.txt
```

### 步骤 2: 验证高级功能

```bash
# 测试黄土高原预设
blenderproc run generate_mountainous_solar_site.py output/test \
    --image_index 1 \
    --seed 1001 \
    --use_clusters \
    --use_advanced_features \
    --geological_preset loess \
    --use_gpu \
    --max_samples 50

# 测试南方丘陵预设
blenderproc run generate_mountainous_solar_site.py output/test \
    --image_index 2 \
    --seed 1002 \
    --use_clusters \
    --use_advanced_features \
    --geological_preset hills \
    --use_gpu \
    --max_samples 50
```

**检查点**：
- 图像中应该看到不同类型的桩基（PHC、螺旋钢桩、灌注桩）
- 地面应该有车辙痕迹
- 桩基周围应该有施工废料
- 不同预设的地面颜色应该不同

### 步骤 3: 小批量测试（验证批量生成）

```bash
# 生成5张图像（2个并行进程）
./run_parallel.sh 2 5 output/test_batch 2000
```

**预期结果**：
- 生成 5 张图像：`000000.png` 到 `000004.png`
- 生成 5 个标注文件：`000000.txt` 到 `000004.txt`
- 生成日志文件：`output/test_batch/logs/image_*.log`

**检查点**：
```bash
# 检查所有文件
ls -lh output/test_batch/images/*.png | wc -l  # 应该显示 5
ls -lh output/test_batch/labels/*.txt | wc -l  # 应该显示 5

# 检查日志
ls -lh output/test_batch/logs/*.log | wc -l  # 应该显示 5

# 查看是否有错误
grep -i "error\|warning\|failed" output/test_batch/logs/*.log
```

## 📋 详细测试清单

### 功能测试

#### ✅ 测试 1: 基础功能
- [ ] 脚本可以正常运行
- [ ] 生成图像文件（PNG格式）
- [ ] 生成YOLO标注文件（TXT格式）
- [ ] 图像尺寸正确（默认5280x3956）
- [ ] 标注文件格式正确（`class_id x_center y_center width height`）

#### ✅ 测试 2: 高级功能
- [ ] 启用 `--use_advanced_features` 后使用新模块
- [ ] 生成不同类型的桩基（PHC、螺旋钢桩、灌注桩）
- [ ] 桩基排布符合规范（阶梯状、工程容差）
- [ ] 环境细节（车辙、废料）正确生成
- [ ] 地质预设生效（loess/hills）

#### ✅ 测试 3: 参数测试
- [ ] 不同 `--seed` 生成不同图像
- [ ] `--geological_preset` 参数生效
- [ ] `--use_clusters` vs 不使用集群模式
- [ ] `--max_samples` 影响渲染质量
- [ ] `--use_gpu` 加速渲染

#### ✅ 测试 4: 批量生成
- [ ] 并行脚本可以正常运行
- [ ] 多进程不冲突
- [ ] 所有图像都成功生成
- [ ] 日志文件正确记录

### 输出验证

#### 图像验证
```bash
# 检查图像文件
file output/test/images/000000.png  # 应该是 PNG 图像
identify output/test/images/000000.png  # ImageMagick，显示尺寸等信息

# 检查图像是否为空或损坏
python3 << 'EOF'
import cv2
import numpy as np

img = cv2.imread('output/test/images/000000.png')
if img is None:
    print("❌ 图像无法读取（可能损坏）")
else:
    print(f"✅ 图像尺寸: {img.shape}")
    print(f"✅ 像素值范围: {img.min()} - {img.max()}")
    if img.max() == img.min():
        print("⚠️  警告：图像可能是纯色")
    else:
        print("✅ 图像包含变化（不是纯色）")
EOF
```

#### 标注验证
```bash
# 检查标注文件格式
python3 << 'EOF'
import os

label_file = 'output/test/labels/000000.txt'
if not os.path.exists(label_file):
    print("❌ 标注文件不存在")
else:
    with open(label_file, 'r') as f:
        lines = f.readlines()
    
    print(f"✅ 标注数量: {len(lines)}")
    
    for i, line in enumerate(lines[:5]):  # 显示前5个
        parts = line.strip().split()
        if len(parts) == 5:
            class_id, x, y, w, h = parts
            print(f"  标注 {i+1}: class={class_id}, center=({x}, {y}), size=({w}, {h})")
            
            # 验证值范围
            x, y, w, h = float(x), float(y), float(w), float(h)
            if 0 <= x <= 1 and 0 <= y <= 1 and 0 <= w <= 1 and 0 <= h <= 1:
                print(f"    ✅ 值在有效范围内 [0, 1]")
            else:
                print(f"    ❌ 值超出范围！")
        else:
            print(f"  ❌ 格式错误: {line.strip()}")
EOF
```

## 🔧 常见问题排查

### 问题 1: 脚本无法运行

**症状**：`blenderproc run` 命令失败

**排查步骤**：
```bash
# 1. 检查 BlenderProc 是否安装
blenderproc --version

# 2. 检查 Blender 是否可用
blenderproc run --help

# 3. 检查脚本语法
python3 -m py_compile generate_mountainous_solar_site.py

# 4. 检查模块导入
python3 << 'EOF'
try:
    import pile_factory
    import pile_layout_engine
    import environmental_storytelling
    print("✅ 所有模块可以导入")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
EOF
```

### 问题 2: 生成纯色图像

**症状**：图像是单一颜色（白色、黑色等）

**排查步骤**：
```bash
# 检查日志中的警告
grep -i "warning\|error" output/test/logs/*.log

# 检查相机设置
# 在脚本中添加调试输出，检查：
# - 相机位置
# - 场景对象数量
# - 光照设置
```

**解决方案**：
- 确保使用了 `--use_advanced_features`
- 检查 `--asset_path` 是否正确（如果有纹理）
- 尝试不同的 `--seed` 值

### 问题 3: 没有生成标注文件

**症状**：有图像但没有标注文件

**排查步骤**：
```bash
# 检查日志
cat output/test/logs/image_000000.log | grep -i "annotation\|segmentation"

# 检查是否有对象被检测到
# 在脚本中，应该看到类似输出：
# "Generated X annotations -> output/test/labels/000000.txt"
```

**解决方案**：
- 确保对象设置了 `category_id = 0`
- 检查分割渲染是否启用
- 验证对象在相机视野内

### 问题 4: GPU 加速不工作

**症状**：渲染很慢，没有使用 GPU

**排查步骤**：
```bash
# 检查日志中的设备信息
grep -i "device\|gpu\|metal\|cpu" output/test/logs/*.log

# 应该看到类似：
# "Device Apple M3 Pro (GPU - 18 cores) of type METAL found and used."
```

**解决方案**：
- 确保使用 `--use_gpu` 参数
- 检查 Blender 是否支持 Metal（macOS）
- 尝试降低 `--max_samples` 以加快测试

### 问题 5: 并行脚本卡住

**症状**：`run_parallel.sh` 运行后卡住

**排查步骤**：
```bash
# 检查进程
ps aux | grep blenderproc

# 检查日志
tail -f output/test_batch/logs/image_*.log

# 检查资源使用
top  # 或 htop
```

**解决方案**：
- 减少并行进程数：`./run_parallel.sh 1 5 ...`（使用1个进程）
- 检查内存使用情况
- 查看具体哪个图像卡住，单独测试

## 📊 性能测试

### 单张图像渲染时间

```bash
# 测试不同采样数的影响
for samples in 25 50 100; do
    echo "测试 max_samples=$samples"
    time blenderproc run generate_mountainous_solar_site.py output/perf_test \
        --image_index 0 \
        --seed 1000 \
        --use_clusters \
        --use_advanced_features \
        --use_gpu \
        --max_samples $samples
done
```

### 批量生成性能

```bash
# 测试不同并行数
for parallel in 1 2 4; do
    echo "测试 parallel=$parallel"
    time ./run_parallel.sh $parallel 10 output/perf_test_$parallel 3000
done
```

## ✅ 测试检查表

完成以下检查表以确保一切正常：

- [ ] 单张图像可以生成
- [ ] 图像文件存在且可打开
- [ ] 标注文件存在且格式正确
- [ ] 高级功能正常工作（桩基类型、环境细节）
- [ ] 不同预设生成不同结果
- [ ] 批量生成可以正常运行
- [ ] 并行脚本不卡住
- [ ] 日志文件正确记录
- [ ] GPU 加速生效（如果可用）
- [ ] 输出文件命名正确（连续编号）

## 🎯 下一步

测试通过后，可以：

1. **生产环境使用**：
   ```bash
   ./run_parallel.sh 2 100 output/dataset 10000
   ```

2. **调整参数**：
   - 修改 `--max_samples` 平衡质量和速度
   - 调整 `--geological_preset` 生成不同风格
   - 使用不同的 `--seed` 范围确保多样性

3. **验证数据集**：
   - 使用 YOLO 训练工具验证标注格式
   - 检查图像质量和多样性
   - 统计对象数量和分布

## 📚 相关文档

- `QUICK_START.md` - 快速开始指南
- `PROJECT_INDEX.md` - 项目文件索引
- `docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` - 高级功能说明
- `docs/solar_farm/guides/GPU_ACCELERATION_README.md` - GPU 加速配置

---

**最后更新**：2026-01-02

