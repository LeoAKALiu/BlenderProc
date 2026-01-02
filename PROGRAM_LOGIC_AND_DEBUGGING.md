# 程序逻辑和调试文档

## 项目概述

这是一个使用 BlenderProc 生成太阳能农场建设工地合成数据集的 Python 脚本。主要功能是生成包含太阳能桩基（piles）的航拍图像，并生成 YOLO 格式的标注。

**主脚本**: `generate_mountainous_solar_site.py`

## 核心功能流程

### 1. 初始化阶段 (`main()`)

```python
bproc.init()  # 只调用一次，初始化 BlenderProc
```

**关键设置**:
- GPU 加速配置（Metal for Apple Silicon）
- 渲染参数优化（采样数、噪声阈值、降噪器）
- 曝光设置（-0.5 防止过曝）
- 纹理加载（一次性加载所有可用纹理）

### 2. 批量生成循环

```python
for img_idx in range(num_images):
    generate_single_image(...)
```

每次循环生成一张图像，包含完整的场景创建、渲染和保存流程。

### 3. 单张图像生成流程 (`generate_single_image()`)

#### 3.1 场景清理（第2张图片开始）

```python
if clean_scene:
    # 清除注册的输出（防止状态累积）
    GlobalStorage.set("output", [])
    bproc.utility.reset_keyframes()
    bproc.clean_up(clean_up_camera=True)
    gc.collect()
```

**问题**: 之前使用 `GlobalStorage.remove("output")` 但该 API 不存在，已修复为 `GlobalStorage.set("output", [])`

#### 3.2 场景创建

1. **地形创建** (`create_terraced_terrain`)
   - 创建大型网格平面
   - 添加位移修改器（terrace-like steps）
   - 应用混合纹理（草地、土壤、车辙等）

2. **桩基创建** (`create_pile_clusters` 或 `create_piles_in_curved_rows`)
   - 创建圆柱形桩基对象
   - 设置 `category_id=0`（用于分割）
   - 根据地形高度调整 Z 位置

3. **干扰物创建** (`create_material_bags`, `create_machinery_blocks`)
   - 白色材料袋
   - 黄色机械块
   - 设置 `category_id=0`（背景，不作为桩基标注）

4. **光照设置**
   - 随机太阳高度角（30-60°）
   - 随机方位角（0-360°）
   - 随机能量（1.0-2.0）

5. **相机设置**
   - 高度：100m
   - 视角：Nadir（垂直向下）
   - FOV：90°

#### 3.3 渲染前准备

```python
# 清除已注册的输出（防止重复注册）
GlobalStorage.set("output", [])

# 启用分割输出
bproc.renderer.enable_segmentation_output(
    map_by=["category_id", "instance", "name"],
    default_values={"category_id": -1}
)
```

**关键问题**: 
- 每次调用 `enable_segmentation_output` 都会注册新的输出
- 如果不清除，会导致 "duplicate keys and paths" 警告
- 状态累积可能导致渲染卡住

#### 3.4 渲染

```python
data = bproc.renderer.render()
```

**内部流程**（BlenderProc）:
1. 设置输出路径
2. 调用 `bpy.ops.render.render(animation=True, write_still=True)`
3. 加载渲染结果到内存

**已知问题**:
- 有时会卡在 `bpy.ops.render.render()` 调用
- 可能的原因：GPU 状态问题、内存泄漏、输出注册累积

#### 3.5 图像保存

```python
color_image = data['colors'][0]  # 第一帧
# 自动检测颜色范围（[0,1] 或 [0,255]）
if img_max > 1.0:
    color_uint8 = np.clip(color_image, 0, 255).astype(np.uint8)
else:
    color_uint8 = (color_bgr * 255).astype(np.uint8)
cv2.imwrite(image_path, color_uint8)
```

#### 3.6 YOLO 标注生成

```python
write_yolo_annotations(
    labels_dir,
    data['instance_segmaps'],
    data['instance_attribute_maps'],
    render_width,
    render_height,
    image_index
)
```

## 当前问题

### 问题 1: 渲染卡住

**症状**:
- 第2张图片开始，渲染时卡住
- 终端显示 "Rendering 2 frames"（应该是1帧）
- 进程 CPU 使用率接近 0%

**可能原因**:
1. **输出注册累积**: 每次 `enable_segmentation_output` 都注册新输出，导致状态累积
2. **GPU 状态问题**: Metal GPU 可能在多次渲染后进入异常状态
3. **内存泄漏**: 场景对象没有完全清理
4. **帧数设置错误**: 显示 "Rendering 2 frames" 说明 frame_end 可能被错误设置

**已尝试的修复**:
- ✅ 清除 `GlobalStorage["output"]`（修复了 API 调用错误）
- ✅ 添加 GC 清理
- ✅ 添加错误处理和重试
- ❌ 仍然卡住

### 问题 2: 重复注册输出警告

**症状**:
```
Warning! Detected output entries with duplicate keys and paths
```

**原因**:
- `enable_segmentation_output` 每次调用都会调用 `Utility.add_output_entry()`
- 如果之前注册的输出没有清除，就会重复注册

**已尝试的修复**:
- ✅ 在场景清理时清除输出
- ✅ 在渲染前清除输出
- ⚠️ 警告仍然出现（说明清除时机可能不对）

### 问题 3: 帧数错误

**症状**:
- 终端显示 "Rendering 2 frames" 但应该只有1帧
- 说明 `bpy.context.scene.frame_end - frame_start = 2`

**可能原因**:
- `bproc.camera.add_camera_pose()` 可能被调用了多次
- 或者 frame_end 在某个地方被错误地增加了

## 代码关键位置

### 输出注册机制

**文件**: `blenderproc/python/utility/Utility.py`

```python
def add_output_entry(output: Dict[str, Any]):
    if not GlobalStorage.is_in_storage("output"):
        GlobalStorage.set("output", [])
    
    registered_outputs = GlobalStorage.get("output")
    if Utility.output_already_registered(output, registered_outputs):
        print("Warning! Detected output entries with duplicate keys and paths")
        return True
    
    registered_outputs.append(output)
    GlobalStorage.set("output", registered_outputs)
```

**关键点**:
- 输出存储在 `GlobalStorage["output"]` 中，是一个列表
- 每次 `enable_segmentation_output` 都会添加新条目
- 清除方法：`GlobalStorage.set("output", [])`

### 渲染流程

**文件**: `blenderproc/python/renderer/RendererUtility.py`

```python
def render(...):
    # 设置输出路径
    bpy.context.scene.render.filepath = os.path.join(output_dir, file_prefix)
    
    # 计算帧数
    total_frames = bpy.context.scene.frame_end - bpy.context.scene.frame_start
    
    # 渲染
    bpy.ops.render.render(animation=True, write_still=True)
    
    # 加载结果
    return _WriterUtility.load_registered_outputs(load_keys)
```

**关键点**:
- `frame_end` 和 `frame_start` 决定渲染帧数
- 每个相机位姿对应一帧
- 如果显示 "2 frames"，说明有2个相机位姿或 frame_end 设置错误

### 场景清理

**文件**: `blenderproc/python/utility/Initializer.py`

```python
def clean_up(clean_up_camera: bool = False):
    _Initializer.remove_all_data(clean_up_camera)
    _Initializer.remove_custom_properties()
    # 创建新世界和相机
```

**关键点**:
- `clean_up` 会删除所有对象
- 但不会清除 `GlobalStorage` 中的数据
- 需要手动清除 `GlobalStorage["output"]`

## 调试建议

### 1. 检查帧数设置

在渲染前添加调试信息：

```python
print(f"  Frame range: {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
print(f"  Total frames: {bpy.context.scene.frame_end - bpy.context.scene.frame_start}")
```

### 2. 检查输出注册

在 `enable_segmentation_output` 前后检查：

```python
before = len(Utility.get_registered_outputs())
bproc.renderer.enable_segmentation_output(...)
after = len(Utility.get_registered_outputs())
print(f"  Outputs: {before} -> {after}")
```

### 3. 检查 GPU 状态

在渲染前检查 GPU 设备状态：

```python
import bpy
prefs = bpy.context.preferences.addons['cycles'].preferences
for device in prefs.devices:
    print(f"  Device: {device.name}, type: {device.type}, use: {device.use}")
```

### 4. 尝试禁用 GPU

如果 GPU 有问题，可以尝试只用 CPU：

```bash
blenderproc run generate_mountainous_solar_site.py output/test \
  --num_images 2 \
  # 不传 --use_gpu
```

### 5. 检查内存使用

在每次渲染前后检查内存：

```python
import psutil
process = psutil.Process()
mem_before = process.memory_info().rss / 1024 / 1024  # MB
# ... render ...
mem_after = process.memory_info().rss / 1024 / 1024
print(f"  Memory: {mem_before:.1f}MB -> {mem_after:.1f}MB (+{mem_after-mem_before:.1f}MB)")
```

## 可能的解决方案

### 方案 1: 每次重新初始化（不推荐，太慢）

```python
for img_idx in range(num_images):
    bproc.init()  # 每次都重新初始化
    generate_single_image(clean_scene=False, ...)
```

### 方案 2: 手动管理输出注册

不依赖 `enable_segmentation_output` 的自动注册，手动管理：

```python
# 清除所有输出
GlobalStorage.set("output", [])

# 手动注册分割输出
# ... 需要查看 enable_segmentation_output 的实现
```

### 方案 3: 检查 frame_end 设置

确保每次渲染前 frame_end 正确：

```python
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = 1  # 确保只有1帧
```

### 方案 4: 使用单进程模式

如果并行导致问题，使用单进程：

```bash
# 不使用 run_parallel.sh
blenderproc run generate_mountainous_solar_site.py output/dataset \
  --num_images 10 \
  --use_clusters \
  --use_gpu
```

## 环境信息

- **Blender**: 4.2.0
- **BlenderProc**: 2.8.0
- **系统**: macOS (darwin 25.2.0)
- **GPU**: Apple M3 Pro (Metal)
- **Python**: 3.12

## 相关文件

- `generate_mountainous_solar_site.py` - 主脚本
- `blenderproc/python/renderer/RendererUtility.py` - 渲染工具
- `blenderproc/python/utility/Utility.py` - 工具函数（输出注册）
- `blenderproc/python/utility/GlobalStorage.py` - 全局存储
- `blenderproc/python/utility/Initializer.py` - 初始化工具

## 下一步调试方向

1. **检查 frame_end 设置**: 为什么显示 "2 frames"？
2. **检查输出清除时机**: 是否在正确的时机清除？
3. **检查 GPU 状态**: Metal GPU 是否在多次渲染后进入异常状态？
4. **尝试简化场景**: 减少对象数量，看是否仍然卡住
5. **检查 BlenderProc 版本兼容性**: 2.8.0 与 Blender 4.2.0 是否有已知问题

