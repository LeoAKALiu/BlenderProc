# 查看输出文件指南

## 📸 图像文件

### 位置
```
output/solar_farm_final_opt/images/image_000000.jpg
```

### 信息
- **尺寸**: 1920x1080 像素
- **格式**: JPEG
- **大小**: 111 KB
- **状态**: ✅ 完整可用

### 查看方法

#### 方法1: 使用系统默认程序
```bash
open output/solar_farm_final_opt/images/image_000000.jpg
```

#### 方法2: 使用Python/OpenCV
```python
import cv2
img = cv2.imread('output/solar_farm_final_opt/images/image_000000.jpg')
cv2.imshow('Solar Farm Scene', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

#### 方法3: 使用Python/PIL
```python
from PIL import Image
img = Image.open('output/solar_farm_final_opt/images/image_000000.jpg')
img.show()
```

## 💾 HDF5数据文件

### 位置
```
output/solar_farm_final_opt/0.hdf5
```

### 包含的数据
- `colors`: RGB图像数据 (1080, 1920, 3)
- `instance_segmaps`: 实例分割图 (1080, 1920)
- `category_id_segmaps`: 类别分割图 (1080, 1920)
- `instance_attribute_maps`: 实例属性映射
- `blender_proc_version`: BlenderProc版本信息

### 查看方法

```python
import h5py
import numpy as np
import ast

# 打开HDF5文件
f = h5py.File('output/solar_farm_final_opt/0.hdf5', 'r')

# 查看所有键
print("Keys:", list(f.keys()))

# 查看RGB图像
colors = f['colors'][:]
print(f"Colors shape: {colors.shape}")

# 查看分割图
segmap = f['instance_segmaps'][:]
unique_ids = np.unique(segmap)
print(f"Unique instance IDs: {unique_ids}")

# 查看属性映射
attr_str = f['instance_attribute_maps'][()].decode('utf-8')
attr_list = ast.literal_eval(attr_str)
print(f"Detected objects: {len(attr_list)}")
for entry in attr_list:
    print(f"  ID {entry['idx']}: {entry['name']} (category_id={entry['category_id']})")

f.close()
```

## 📝 标签文件

### 位置
```
output/solar_farm_final_opt/labels/image_000000.txt
```

### 状态
⚠️ **空文件** (0字节)

### 原因
- 没有检测到 `category_id=0` 的pile对象
- 分割图中只检测到：
  - 地面 (Plane, category_id=-1): 98.47% 像素
  - Distractor对象 (Cube, category_id=-1): 1.53% 像素

### 预期格式（如果对象被检测到）
```
<class_id> <x_center> <y_center> <width> <height>
```
所有值都是归一化的 (0-1)，例如：
```
0 0.5 0.5 0.1 0.2
0 0.3 0.7 0.08 0.15
```

## 🔍 当前检测状态

### 检测到的对象
1. **地面 (Plane)**
   - ID: 1
   - category_id: -1
   - 像素占比: 98.47%

2. **Distractor对象 (Cube)**
   - ID: 19, 20
   - category_id: -1
   - 像素占比: 1.53%

### 未检测到的对象
- **Pile对象 (Cylinder)**
  - 虽然对象在场景中创建（有正确的pass_index和category_id=0）
  - 但在分割图中不可见
  - 可能原因：相机角度、对象遮挡或尺寸问题

## 📊 数据统计

### 分割图统计
- **总像素数**: 2,073,600 (1920 × 1080)
- **背景像素**: 0 (ID 0)
- **地面像素**: 2,041,886 (98.47%)
- **对象像素**: 31,714 (1.53%)

### 对象检测统计
- **总对象数**: 3
- **Pile对象**: 0
- **Distractor对象**: 2
- **地面**: 1

## 🎯 下一步

要生成有效的标签文件，需要解决pile对象的可见性问题：
1. 调整相机角度（使用更平的角度）
2. 进一步增大对象尺寸
3. 简化地面（移除displacement modifier）
4. 使用更近的相机位置

## 📁 所有输出目录

```bash
# 列出所有输出目录
ls -lht output/

# 查看特定目录的内容
ls -lh output/solar_farm_final_opt/
```

## 💡 提示

- 图像文件可以直接用任何图像查看器打开
- HDF5文件可以用Python的h5py库读取
- 可以使用Blender打开.blend文件（如果保存了）来查看3D场景
- 分割图可以可视化来查看哪些区域被检测到






