# 纯色图像问题修复方案

## 问题描述
生成的图像是纯色的（只有10个唯一值，范围54-73），看不到纹理和目标对象。

## 可能的原因

### 1. 相机没有看到场景
- 相机位置可能不对
- 相机角度可能有问题
- 相机视野范围可能不包含场景

### 2. 场景对象没有正确创建
- 地面可能没有正确创建
- Pile对象可能没有正确创建
- 对象可能被隐藏或不可见

### 3. 材质/纹理问题
- 地面材质可能有问题
- 对象材质可能有问题
- 纹理可能没有正确加载

## 诊断步骤

### 步骤1: 检查场景对象
在代码中添加调试输出，确认对象真的在场景中：
```python
import bpy
all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
print(f"场景中的网格对象: {len(all_objects)}")
for obj in all_objects[:10]:
    print(f"  - {obj.name}: loc={obj.location}, visible={not obj.hide_render}")
```

### 步骤2: 检查相机位置
确认相机位置和场景中心的关系：
```python
print(f"场景中心: {scene_center}")
print(f"相机位置: ({x}, {y}, {height})")
print(f"相机角度: pitch={pitch}°, yaw={yaw}°")
```

### 步骤3: 使用已知工作的参数
使用之前成功检测到对象的相机参数（倾斜视角）：
```python
# 使用之前成功的参数
height = np.random.uniform(6, 10)  # 较低高度
pitch = np.random.uniform(-50, -40)  # 倾斜视角
distance = max(max_extent * 0.5, 6.0)
x = scene_center[0] + distance * np.cos(angle)
y = scene_center[1] + distance * np.sin(angle)
```

## 建议的修复方案

### 方案1: 使用倾斜视角（先确保能看到场景）
```python
# 使用之前成功的倾斜视角参数
height = np.random.uniform(8, 12)
distance = max(max_extent * 0.6, 8.0)
angle = np.random.uniform(0, 2 * np.pi)
x = scene_center[0] + distance * np.cos(angle)
y = scene_center[1] + distance * np.sin(angle)
pitch = np.random.uniform(-55, -45)  # 倾斜视角
yaw = np.arctan2(scene_center[1] - y, scene_center[0] - x)
```

### 方案2: 检查并修复地面材质
确保地面有可见的纹理：
```python
# 在create_ground函数中
ground_material.set_principled_shader_value("Base Color", [0.4, 0.3, 0.2, 1.0])  # 明显的棕色
ground_material.set_principled_shader_value("Roughness", 0.9)
```

### 方案3: 添加调试渲染
在渲染前检查场景：
```python
# 在渲染前
import bpy
print(f"场景对象数: {len(bpy.context.scene.objects)}")
print(f"相机: {bpy.context.scene.camera}")
print(f"相机位置: {bpy.context.scene.camera.location}")
```

## 快速测试

运行一个简单的测试，使用已知工作的参数：
```bash
blenderproc run generate_solar_farm_dataset.py output/test_visible \
  --num_cameras 1 \
  --num_piles_x 5 \
  --num_piles_y 4 \
  --pile_spacing 4.0 \
  --render_width 1920 \
  --render_height 1080
```

然后检查生成的图像是否有内容。

## 下一步

1. 先使用倾斜视角确保能看到场景
2. 确认场景对象正确创建
3. 然后逐步调整为正摄视角






