# 相机位置调试记录

## 问题描述

在生成太阳能桩数据集时，遇到的主要问题是：
1. **纯色图像**：生成的图像几乎完全是纯色，看不到场景内容
2. **Pile对象不可见**：即使创建了pile对象，在分割图中检测不到
3. **Pile位置偏边缘**：偶尔能检测到pile，但位置在图像边缘（左侧或右侧）

## 开发时间线

### 阶段1：基础功能实现
- ✅ 创建了简化脚本 `generate_solar_farm_simple.py`
- ✅ 实现了基础场景创建（地面 + pile网格）
- ✅ 实现了YOLO标注生成功能
- ✅ 验证了分割渲染设置正确

### 阶段2：相机位置调试
- ⚠️ 尝试了多种相机位置和角度
- ⚠️ 部分配置能看到pile，但位置不理想

## 所有尝试的配置

### 配置1：初始工作配置（simple_fixed）
**参数：**
- 相机高度：10-12m
- 相机距离：max_extent * 0.7
- 相机角度：0°（沿X轴）
- 相机pitch：-45°
- Pile数量：8x6 = 48个

**结果：**
- ✅ 能检测到1个pile对象
- ✅ 生成了YOLO标注
- ⚠️ Pile位置在右侧边缘（center_x=0.992）

**输出目录：** `output/simple_fixed/`

### 配置2：调整相机角度到45°（simple_centered_view）
**参数：**
- 相机高度：10-12m
- 相机距离：max_extent * 0.7
- 相机角度：180°（从对面看向场景中心）
- 相机pitch：-45°

**结果：**
- ❌ 检测不到pile对象
- ❌ 分割图只有背景（ID=1）

### 配置3：调整相机高度和距离（simple_improved_view）
**参数：**
- 相机高度：11-13m（更高）
- 相机距离：max_extent * 0.75（更远）
- 相机角度：45°（对角线视角）
- 相机pitch：-45°

**结果：**
- ❌ 检测不到pile对象
- ❌ 图像唯一值只有24（接近纯色）

### 配置4：增加Pile数量（simple_more_piles）
**参数：**
- 相机参数：同配置1
- Pile数量：10x8 = 80个

**结果：**
- ❌ 检测不到pile对象
- ⚠️ 可能pile太多，相机视野不够

## 代码关键部分

### 相机位置设置（当前版本）

```python
# 在 generate_solar_farm_simple.py 中
if pitch >= -60:
    # Oblique view: use proven working parameters
    height = np.random.uniform(10, 12)  # Proven working range
    distance = max_extent * 0.7  # Proven working distance
    angle = np.random.uniform(0, 2 * np.pi) if args.num_cameras > 1 else 0.0
    x = scene_center[0] + distance * np.cos(angle)
    y = scene_center[1] + distance * np.sin(angle)
    yaw = np.arctan2(scene_center[1] - y, scene_center[0] - x)
```

### Pile创建

```python
def create_simple_pile(location: np.ndarray, radius: float = 0.4, height: float = 3.0):
    pile = bproc.object.create_primitive("CYLINDER", radius=radius, depth=height)
    pile.set_location([location[0], location[1], location[2] + height/2])
    pile.blender_obj.hide_set(False)
    pile.blender_obj.hide_render = False
    # 材质设置
    pile_material = pile.new_material("pile_material")
    pile_material.set_principled_shader_value("Base Color", [0.5, 0.5, 0.55, 1.0])
    pile_material.set_principled_shader_value("Metallic", 0.85)
    pile_material.set_principled_shader_value("Roughness", 0.25)
    return pile
```

### 场景中心计算

```python
if len(piles) > 0:
    pile_locations = np.array([pile.get_location() for pile in piles])
    scene_center = pile_locations.mean(axis=0)
    scene_size = pile_locations.max(axis=0) - pile_locations.min(axis=0)
    max_extent = max(scene_size[0], scene_size[1])
```

## 发现的问题

### 1. 相机位置计算问题
- **问题**：相机位置基于场景中心计算，但pile网格可能不在原点
- **现象**：Pile位置偏右（center_x=0.992），说明相机没有正对场景中心
- **可能原因**：
  - 场景中心计算正确，但相机yaw角度计算有误
  - 或者pile网格位置偏移了

### 2. 相机视野问题
- **问题**：即使调整相机位置，也只能看到1个pile
- **现象**：创建了48个pile，但只检测到1个
- **可能原因**：
  - 相机视野（FOV）太小
  - 相机距离太近
  - Pile太小，在图像中不可见

### 3. 分割图问题
- **问题**：有时分割图只有背景（ID=1），没有pile对象
- **现象**：即使pile对象存在，分割图中也检测不到
- **可能原因**：
  - Pile对象太小（< 1像素）
  - Pile对象在相机视野外
  - 分割渲染设置问题

## 调试思路

### 思路1：验证场景中心
- 打印场景中心和pile位置
- 确认pile网格是否在预期位置
- 检查相机是否正对场景中心

### 思路2：调整相机FOV
- 当前使用默认FOV（可能太小）
- 尝试增大FOV以看到更多场景
- 使用 `bproc.camera.set_intrinsics_from_blender_params()` 设置FOV

### 思路3：调整相机高度和距离
- 当前高度：10-12m
- 当前距离：max_extent * 0.7
- 尝试：
  - 更高：15-20m
  - 更远：max_extent * 1.0 或 1.2

### 思路4：检查Pile大小
- 当前半径：0.4m
- 当前高度：2.5-3.5m
- 在1920x1080分辨率下，如果相机高度10m，pile可能只有几个像素
- 尝试增大pile尺寸或降低相机高度

### 思路5：使用正交相机
- 当前使用透视相机
- 尝试使用正交相机（orthographic）可能更适合正摄视角

## 下一步建议

### 短期目标
1. **修复相机位置**：让pile在图像中心区域（center_x在0.3-0.7之间）
2. **增加可见pile数量**：从1个增加到至少5-10个
3. **验证分割图**：确保所有可见的pile都在分割图中

### 中期目标
1. **调整到正摄视角**：从-45°逐步调整到-85°或-90°
2. **增加pile数量**：从8x6增加到15x10或20x15
3. **匹配真实数据**：分辨率5280x3956，对象大小30-40像素

### 长期目标
1. **添加地面纹理**：使用PBR纹理和displacement
2. **添加patch**：50%的pile有白色patch
3. **添加distractor对象**：蓝色和黄色的干扰物

## 测试命令

### 基础测试（8x6网格）
```bash
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
blenderproc run generate_solar_farm_simple.py output/test \
  --custom-blender-path "/Applications/Blender.app" \
  --num_piles_x 8 \
  --num_piles_y 6 \
  --pile_spacing 3.5 \
  --num_cameras 1
```

### 检查结果
```bash
# 查看图像
open output/test/images/image_000000.jpg

# 检查标注
cat output/test/labels/image_000000.txt

# 检查HDF5数据
python3 << 'EOF'
import h5py
import numpy as np
import ast

f = h5py.File('output/test/0.hdf5', 'r')
colors = f['colors'][:]
segmap = f['instance_segmaps'][:]
attr_str = f['instance_attribute_maps'][()].decode('utf-8')
attr_list = ast.literal_eval(attr_str)

print(f"图像: {colors.shape[1]}x{colors.shape[0]}")
print(f"唯一值: {len(np.unique(colors.flatten()))}")
print(f"分割ID: {np.unique(segmap)}")
print(f"Pile对象: {len([e for e in attr_list if e.get('category_id') == 0])}")
f.close()
EOF
```

## 相关文件

- `generate_solar_farm_simple.py` - 当前使用的简化脚本
- `generate_solar_farm_dataset.py` - 原始复杂脚本（有问题）
- `AGENTS.md` - 开发指南
- `NEW_APPROACH.md` - 新开发思路

## 输出目录说明

- `output/simple_fixed/` - 能检测到pile的配置（位置偏右）
- `output/simple_centered_view/` - 尝试调整到中心（失败）
- `output/simple_improved_view/` - 尝试优化视角（失败）
- `output/simple_more_piles/` - 尝试增加pile数量（失败）
- `output/simple_optimized/` - 最新优化尝试

## 关键发现

1. **唯一能检测到pile的配置**：`simple_fixed`（相机角度0°，高度10-12m，距离max_extent*0.7）
2. **Pile位置问题**：检测到的pile在右侧边缘（center_x=0.992），说明相机没有正对场景中心
3. **可见性限制**：即使创建48个pile，也只能看到1个，说明相机视野或位置需要调整

## 待解决问题

1. ❌ 为什么只能看到1个pile？（应该能看到更多）
2. ❌ 为什么pile在边缘而不是中心？
3. ❌ 如何调整相机位置让pile居中？
4. ❌ 如何增加可见pile数量？
5. ❌ 如何调整到正摄视角而不丢失可见性？

## 参考资料

- BlenderProc文档：https://github.com/DLR-RM/BlenderProc
- 真实数据分析：`REAL_DATA_ANALYSIS.md`
- 分割验证：`SEGMENTATION_VERIFICATION.md`
- 纯色图像问题：`PURE_COLOR_IMAGE_FIX.md`





