# Solar Farm场景改进指南

## 当前状态

✅ **功能正常**:
- Pile对象可以检测到
- 标签文件已生成
- 图像已渲染

⚠️ **需要改进**:
- 场景看起来不像solar farm（太阳能农场）
- 只有部分pile对象可见
- 地面材质需要更像工地

## 改进建议

### 1. 增加Pile数量形成明显网格

当前问题：只有部分pile可见，没有形成明显的网格布局。

**解决方案**：
```bash
# 使用更多pile形成明显的网格
blenderproc run generate_solar_farm_dataset.py output/dataset \
  --num_piles_x 10 \
  --num_piles_y 8 \
  --pile_spacing 4.0
```

### 2. 改善地面材质

当前问题：地面颜色可能不够像工地/construction site。

**已实施的改进**：
- 地面颜色改为 earthy brown: `[0.35, 0.28, 0.22]`
- 粗糙度设为 0.95（像泥土）

**进一步改进**：
- 可以添加真实的muddy ground纹理
- 可以添加tire tracks（轮胎痕迹）
- 可以添加random noise patches（随机干土斑块）

### 3. 调整相机参数以获得更好的网格视图

**当前参数**（已验证可工作）：
- 高度: 5-8m
- 角度: -45°到-35°
- 距离: 40%场景范围

**建议**：
- 对于更大的网格，可以适当增加高度和距离
- 保持角度在-45°到-35°之间以确保对象可见

### 4. 改善光照

**已实施的改进**：
- 太阳光强度: 8.0
- 太阳角度: -20°（低角度，长阴影）
- 环境光: 0.5强度，蓝灰色天空

**效果**：
- 更亮的场景
- 更长的阴影（更像工地场景）

### 5. 添加更多场景元素（可选）

可以添加：
- 更多distractor对象（模拟工地杂物）
- 车辆/设备（如果需要）
- 围栏/标记（如果需要）

## 快速测试命令

```bash
# 生成一个明显的solar farm场景
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
blenderproc run generate_solar_farm_dataset.py output/solar_farm_test \
  --custom-blender-path "/Applications/Blender.app" \
  --num_cameras 1 \
  --num_piles_x 8 \
  --num_piles_y 6 \
  --pile_spacing 4.0

# 查看结果
open output/solar_farm_test/images/image_000000.jpg
cat output/solar_farm_test/labels/image_000000.txt
```

## 参数说明

### 关键参数

- `--num_piles_x`: X方向的pile数量（建议8-12）
- `--num_piles_y`: Y方向的pile数量（建议6-10）
- `--pile_spacing`: Pile之间的间距（建议3.5-4.5米）
- `--num_cameras`: 相机数量（建议10-50用于数据集）

### 当前工作参数

- **对象尺寸**: radius=0.4m, height=3-4m
- **相机高度**: 5-8m
- **相机角度**: -45°到-35°
- **相机距离**: 40%场景范围

## 下一步

1. **增加pile数量**：使用 `--num_piles_x 10 --num_piles_y 8` 形成明显网格
2. **添加真实纹理**：提供muddy ground纹理路径
3. **调整间距**：根据实际solar farm调整 `--pile_spacing`
4. **生成更多样本**：使用 `--num_cameras 50` 生成数据集

## 当前输出位置

- **最新成功输出**: `output/solar_farm_final/`
- **改进版本**: `output/solar_farm_improved/`
- **最佳版本**: `output/solar_farm_better/`






