# 对象可见性修复总结

## 已完成的修复

### 1. ✅ 代码结构修复
- 修复了 `instance_attribute_maps` 数据结构处理（列表的列表）
- 修复了 YOLO 标注写入函数
- 添加了详细的调试信息

### 2. ✅ 对象设置修复
- 确保对象可见性：`hide_set(False)`, `hide_render = False`
- 正确设置 `category_id = 0` 给 pile 对象
- 增大 pile 半径从 0.15 到 0.2 以提高可见性
- 添加对象位置的小偏移以避免 z-fighting

### 3. ✅ 相机设置优化
- 降低相机高度：从 10-20m 调整到 8-12m
- 减小相机距离：从 80-150% 场景范围调整到 60-130%
- 调整相机角度：从 -70°到-50° 调整到 -65°到-55°
- 确保相机指向场景中心

### 4. ✅ 调试信息增强
- 添加了对象位置、category_id、pass_index 的调试输出
- 添加了相机位置和角度的调试信息
- 添加了分割图检测结果的详细输出

## 当前状态

### ✅ 成功的部分
1. **脚本运行**: 无错误，成功执行
2. **对象创建**: Pile 对象正确创建，category_id=0 正确设置
3. **对象注册**: 对象有正确的 pass_index (2, 3, 5 等)
4. **分割图生成**: 分割图成功生成
5. **文件输出**: 所有文件正确生成

### ⚠️ 仍需解决的问题
1. **对象可见性**: Pile 对象在分割图中不可见
   - 虽然对象在场景中（有正确的 pass_index）
   - 但分割图中只检测到地面和部分 distractor
   - 可能原因：
     - 对象太小，在远距离视角下不可见
     - 相机角度导致对象不在视野内
     - 对象被其他对象遮挡

## 建议的进一步修复

### 方案 1: 进一步增大对象尺寸
```python
radius=0.3  # 从 0.2 增加到 0.3
height=3.0  # 从 1.8-2.2 增加到 2.5-3.5
```

### 方案 2: 使用更近的相机
```python
height = 5-8m  # 进一步降低
distance = max_extent * 0.4  # 更近的距离
pitch = -50° to -60°  # 更平的角度
```

### 方案 3: 检查对象是否在相机视野内
- 使用 BlenderProc 的 `visible_objects` 函数验证
- 调整相机位置确保对象在视野内

### 方案 4: 简化测试场景
- 先创建一个简单的测试：单个 pile，固定相机位置
- 验证对象能被检测到后，再扩展到完整场景

## 测试命令

```bash
# 测试当前修复
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
blenderproc run generate_solar_farm_dataset.py output/test \
  --custom-blender-path "/Applications/Blender.app" \
  --num_cameras 1 \
  --num_piles_x 2 \
  --num_piles_y 2 \
  --pile_spacing 3.0

# 检查输出
cat output/test/labels/image_000000.txt
python3 -c "import h5py; f = h5py.File('output/test/0.hdf5', 'r'); import ast; attr = ast.literal_eval(f['instance_attribute_maps'][()].decode('utf-8')); print([e for e in attr if e.get('category_id') == 0])"
```

## 下一步

1. 尝试进一步增大对象尺寸
2. 使用更近的相机位置
3. 创建简化测试场景验证基本功能
4. 如果仍不可见，检查 Blender 场景视图确认对象位置






