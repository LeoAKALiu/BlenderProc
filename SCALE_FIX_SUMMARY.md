# 尺度与坐标系修复总结

## 问题诊断

根据深度分析，发现了**"Scale & Coordinate Mismatch" (尺度与坐标系不匹配)** 问题：

### 核心问题

1. **坐标系原点漂移**
   - 相机位置计算复杂，导致"看哪里"和场景"在哪里"脱节
   - Pile在图像边缘（center_x=0.992），说明相机没有正对场景中心

2. **尺度完全错误**
   - 真实数据：无人机30-60m高度，看300+个桩
   - 之前仿真：相机10-12m高度，看48个桩
   - **相机太低了！** 只能看到脚底下的一小块

3. **正摄视角误解**
   - 之前尝试：Pitch -45°（斜视）
   - 真实需求：Pitch -90°（正摄）
   - 正摄视角下，阴影是主要视觉特征

## 修复方案

### 1. 场景生成（固定原点）

```python
# 网格居中在 (0, 0, 0)
x = (i - (num_piles_x - 1) / 2) * spacing
y = (j - (num_piles_y - 1) / 2) * spacing
location = np.array([x, y, 0])

# 地面足够大，居中
ground_size = max(num_piles_x, num_piles_y) * spacing * 2 + 50.0
ground.set_location([0, 0, 0])
```

### 2. 相机设置（固定位置策略）

```python
# 固定位置：直接在场景中心上方
camera_height = 50.0  # 匹配真实无人机30-60m
camera_location = np.array([0.0, 0.0, camera_height])

# 旋转：-90° pitch（正摄）
pitch = -90.0
cam2world = bproc.math.build_transformation_mat(
    camera_location,
    [np.radians(pitch), 0, 0]  # pitch, roll, yaw
)
```

### 3. 关键参数

- **相机高度**：50m（真实无人机范围）
- **FOV**：80°（广角，匹配无人机）
- **Clipping**：0.1-500m（足够大）
- **太阳角度**：35°（产生阴影，正摄视角的关键）
- **Pile数量**：20x15 = 300个（匹配真实数据）

## 代码变更

### 主要修改

1. **Pile网格生成**（generate_solar_farm_simple.py:168-195）
   - 改为居中在(0,0,0)
   - 添加场景边界计算和验证

2. **地面创建**（generate_solar_farm_simple.py:163-167）
   - 地面大小动态计算
   - 明确居中在(0,0,0)

3. **光照设置**（generate_solar_farm_simple.py:187-193）
   - 太阳角度：35°（不是垂直）
   - 产生阴影（正摄视角的关键）

4. **相机设置**（generate_solar_farm_simple.py:195-280）
   - 固定位置：(0, 0, 50)
   - 固定角度：-90° pitch
   - FOV：80°（使用radians）
   - Clipping：0.1-500m

## 测试结果

### 当前状态
- ✅ 图像有内容（唯一值52）
- ✅ 分割图有对象（ID: [0, 1]）
- ⚠️  Pile对象：1个（应该更多）
- ⚠️  YOLO标注：0个（需要修复）

### 可能的问题

1. **FOV设置**：需要验证80°是否正确设置
2. **相机旋转**：-90° pitch可能不是正确的正摄角度
3. **Pile大小**：在50m高度，pile可能太小（< 1像素）

## 下一步

1. **验证FOV**：检查实际FOV是否为80°
2. **检查相机旋转**：可能需要调整pitch角度
3. **调整pile大小**：如果太小，增大radius或降低高度
4. **验证分割图**：检查为什么只有1个pile对象

## 关键发现

1. **不再使用复杂的三角函数计算相机位置**
2. **固定位置策略更可靠**
3. **阴影是正摄视角的关键视觉特征**
4. **尺度匹配真实数据很重要**

## 参考文档

- `CAMERA_POSITION_DEBUG.md` - 之前的调试记录
- `REAL_DATA_ANALYSIS.md` - 真实数据分析
- `DEBUG_SESSION_SUMMARY.md` - 调试会话总结





