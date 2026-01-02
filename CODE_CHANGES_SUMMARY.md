# 代码变更总结

## 文件清单

### 主要脚本
1. **`generate_solar_farm_simple.py`** - 简化版本（当前使用）
   - 约300行代码
   - 基础功能：场景创建、pile生成、YOLO标注
   - 状态：✅ 基础功能正常，⚠️ 相机位置需要优化

2. **`generate_solar_farm_dataset.py`** - 原始复杂版本
   - 约623行代码
   - 包含完整功能：地面纹理、patch、distractor等
   - 状态：❌ 有纯色图像问题，已暂停使用

### 辅助脚本
- `download_blender.sh` - Blender下载脚本
- `install_blender_dependencies.sh` - 依赖安装脚本

### 文档
- `AGENTS.md` - AI代理开发指南
- `NEW_APPROACH.md` - 新开发思路
- `PROJECT_SUMMARY.md` - 项目总结
- `CAMERA_POSITION_DEBUG.md` - 相机位置调试记录
- `REAL_DATA_ANALYSIS.md` - 真实数据分析
- `SEGMENTATION_VERIFICATION.md` - 分割验证
- `PURE_COLOR_IMAGE_FIX.md` - 纯色图像问题诊断

## 关键代码变更

### 1. 相机位置设置（多次迭代）

#### 初始版本
```python
# 简单固定位置
height = 10.0
distance = max_extent * 0.7
angle = 0.0
x = scene_center[0] + distance * np.cos(angle)
y = scene_center[1] + distance * np.sin(angle)
pitch = -45.0
yaw = np.arctan2(scene_center[1] - y, scene_center[0] - x)
```

#### 当前版本（generate_solar_farm_simple.py:233-243）
```python
# Oblique view: use proven working parameters
height = np.random.uniform(10, 12)  # Proven working range
distance = max_extent * 0.7  # Proven working distance
angle = np.random.uniform(0, 2 * np.pi) if args.num_cameras > 1 else 0.0
x = scene_center[0] + distance * np.cos(angle)
y = scene_center[1] + distance * np.sin(angle)
yaw = np.arctan2(scene_center[1] - y, scene_center[0] - x)
```

#### 尝试过的变体
1. **角度180°**（从对面看）
   - 结果：❌ 检测不到pile
   
2. **角度45°**（对角线）
   - 结果：❌ 检测不到pile
   
3. **更高高度（11-13m）**
   - 结果：❌ 检测不到pile
   
4. **更远距离（max_extent * 0.75）**
   - 结果：❌ 检测不到pile

### 2. Pile创建函数

#### 当前版本（generate_solar_farm_simple.py:21-45）
```python
def create_simple_pile(location: np.ndarray, radius: float = 0.4, height: float = 3.0):
    pile = bproc.object.create_primitive("CYLINDER", radius=radius, depth=height)
    pile.set_location([location[0], location[1], location[2] + height/2])
    pile.blender_obj.hide_set(False)
    pile.blender_obj.hide_render = False
    # 材质
    pile_material = pile.new_material("pile_material")
    pile_material.set_principled_shader_value("Base Color", [0.5, 0.5, 0.55, 1.0])
    pile_material.set_principled_shader_value("Metallic", 0.85)
    pile_material.set_principled_shader_value("Roughness", 0.25)
    return pile
```

#### 变更历史
- **初始**：radius=0.4, height=3.0, Base Color=[0.6, 0.6, 0.65]
- **优化**：Base Color改为[0.5, 0.5, 0.55]（更暗，对比度更好）
- **尝试**：radius=0.45（增大），但未持续使用

### 3. YOLO标注生成

#### 当前版本（generate_solar_farm_simple.py:48-124）
```python
def write_yolo_annotations(
    output_dir: str,
    instance_segmaps: List[np.ndarray],
    instance_attribute_maps: List[dict],
    class_id: int = 0,
    image_prefix: str = "image_",
):
    # 创建labels目录
    labels_dir = os.path.join(output_dir, "labels")
    os.makedirs(labels_dir, exist_ok=True)
    
    for frame_idx, (segmap, attr_map) in enumerate(zip(instance_segmaps, instance_attribute_maps)):
        # 解析属性映射
        inst_id_to_attrs = {}
        if isinstance(attr_map, list):
            for attr_dict in attr_map:
                if isinstance(attr_dict, dict) and "idx" in attr_dict:
                    inst_id_to_attrs[attr_dict["idx"]] = attr_dict
        
        # 遍历分割图中的实例
        unique_ids = np.unique(segmap)
        for inst_id in unique_ids:
            if inst_id == 0:  # 跳过背景
                continue
            # 检查category_id
            inst_info = inst_id_to_attrs.get(int(inst_id), {})
            category_id = inst_info.get("category_id", None)
            if category_id != class_id:
                continue
            # 计算边界框
            binary_mask = (segmap == inst_id).astype(np.uint8)
            coords = np.column_stack(np.where(binary_mask > 0))
            if len(coords) == 0:
                continue
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)
            # YOLO格式（归一化）
            center_x = (x_min + x_max) / 2.0 / width
            center_y = (y_min + y_max) / 2.0 / height
            bbox_width = (x_max - x_min) / width
            bbox_height = (y_max - y_min) / height
            # 跳过太小的bbox
            if bbox_width < 0.005 or bbox_height < 0.005:
                continue
            annotations.append(f"{class_id} {center_x:.6f} {center_y:.6f} {bbox_width:.6f} {bbox_height:.6f}")
```

#### 关键修复
- **修复1**：正确处理`instance_attribute_maps`（列表格式）
- **修复2**：过滤太小的bbox（< 0.005）
- **修复3**：正确解析category_id

### 4. 场景中心计算

#### 当前版本（generate_solar_farm_simple.py:197-205）
```python
if len(piles) > 0:
    pile_locations = np.array([pile.get_location() for pile in piles])
    scene_center = pile_locations.mean(axis=0)
    scene_size = pile_locations.max(axis=0) - pile_locations.min(axis=0)
    max_extent = max(scene_size[0], scene_size[1])
    print(f"Scene center: {scene_center}, max_extent: {max_extent:.1f}m")
else:
    scene_center = np.array([0, 0, 1.5])
    max_extent = 20.0
```

#### 问题
- Pile网格位置：`(i - num_piles_x/2) * spacing`，中心应该在(0, 0)
- 但由于随机jitter，实际中心可能偏移
- 相机基于这个中心计算，可能导致不对齐

### 5. 分割渲染设置

#### 当前版本（generate_solar_farm_simple.py:252-256）
```python
bproc.renderer.enable_segmentation_output(
    map_by=["category_id", "instance", "name"],
    default_values={"category_id": -1}
)
```

#### 验证
- ✅ 设置正确
- ✅ category_id=0用于pile，-1用于背景
- ✅ 已验证分割图能正确生成

## 未解决的问题

### 1. 相机位置问题
- **现象**：Pile在图像边缘（center_x=0.992）
- **原因**：相机yaw角度计算可能不正确
- **尝试**：多次调整角度，但都失败

### 2. 可见pile数量少
- **现象**：创建48个pile，只看到1个
- **原因**：可能是相机视野太小或距离太近
- **尝试**：增加高度和距离，但导致完全看不到

### 3. 纯色图像问题
- **现象**：某些配置下图像几乎纯色
- **原因**：相机看不到场景
- **解决**：使用-45°斜视角度可以避免

## 代码质量

### 优点
- ✅ 代码结构清晰，函数分离良好
- ✅ 有类型注解和文档字符串
- ✅ 错误处理完善
- ✅ 调试输出充分

### 需要改进
- ⚠️ 相机位置计算逻辑复杂，需要简化
- ⚠️ 缺少相机FOV设置
- ⚠️ 缺少正交相机选项
- ⚠️ 硬编码的参数较多

## 测试结果汇总

| 配置 | Pile数量 | 检测到 | 位置 | 状态 |
|------|---------|--------|------|------|
| simple_fixed | 8x6=48 | 1 | 右侧边缘(0.992) | ⚠️ 部分成功 |
| simple_centered_view | 8x6=48 | 0 | - | ❌ 失败 |
| simple_improved_view | 8x6=48 | 0 | - | ❌ 失败 |
| simple_more_piles | 10x8=80 | 0 | - | ❌ 失败 |
| simple_optimized | 8x6=48 | 0 | - | ❌ 失败 |

## 下一步代码修改建议

### 1. 添加相机FOV设置
```python
# 在相机设置中添加
bproc.camera.set_intrinsics_from_blender_params(
    lens=50.0,  # 或使用FOV
    image_width=args.render_width,
    image_height=args.render_height
)
```

### 2. 添加正交相机选项
```python
# 对于正摄视角，使用正交相机
if pitch < -75:
    bproc.camera.set_orthographic_camera(
        ortho_scale=...,
        ...
    )
```

### 3. 简化相机位置计算
```python
# 使用更直观的方法
# 直接指定相机看向场景中心
camera_location = scene_center + np.array([distance, 0, height])
look_at = scene_center
# 使用look_at函数而不是手动计算yaw
```

### 4. 添加调试可视化
```python
# 在场景中添加辅助对象显示相机位置
camera_marker = bproc.object.create_primitive("SPHERE", radius=0.5)
camera_marker.set_location([x, y, height])
```

## 版本历史

### v1.0 - 初始简化版本
- 基础场景创建
- 简单pile生成
- YOLO标注生成

### v1.1 - 相机位置优化
- 多次尝试调整相机位置
- 部分成功（simple_fixed）

### v1.2 - 当前版本
- 恢复到工作配置
- 继续调试相机位置问题





