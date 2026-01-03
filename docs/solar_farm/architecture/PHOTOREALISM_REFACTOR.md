# 照片级真实感重构总结

## 概述

根据《光伏板桩特征调研报告》，已完成对 BlenderProc 生成脚本的深度重构，实现照片级真实感（Photorealism）。重构包含三个核心模块，严格遵循 GB 50797-2012 规范。

## 模块一：高保真桩基资产库 (`pile_factory.py`)

### 功能

实现了三种桩基类型的程序化生成，完全基于报告中的物理参数：

#### 1. PHC 管桩 (PHC Pipe Pile)
- **几何参数**：
  - 外径：300mm / 400mm / 500mm（三档标准规格）
  - 壁厚：70mm（空心圆柱）
  - 露出高度：300-500mm（可配置）
- **细节特征**：
  - 抱箍结构（金属材质环绕桩顶）
  - 破碎切口（不规则的粗糙顶面，可选）
- **材质变体**：
  - 新桩：灰白色(200, 200, 200)，光滑，模板印痕
  - 陈旧桩：深灰(120, 120, 120)，粗糙，有裂纹

#### 2. 螺旋钢桩 (Spiral Steel Pile)
- **几何参数**：
  - 钢管直径：76mm / 89mm / 114mm / 159mm（四档规格）
  - 壁厚：3-5mm（默认4mm）
  - 螺旋叶片：外径为管径的3-7倍
  - 顶部法兰盘：直径220mm，厚10mm
- **材质特征**：
  - 热镀锌钢，高光泽
  - 支持锈蚀程度调节：
    - `new`：银灰金属光泽(180, 180, 180)
    - `light`：浅灰(160, 160, 160)，轻微氧化
    - `medium`：锈蚀初期(139, 90, 43)，局部锈斑
    - `heavy`：深锈色(100, 60, 30)，镀锌层失效

#### 3. 灌注桩 (Cast-in-place Pile)
- **几何参数**：
  - 直径：300mm（标准）或微孔185-250mm
  - 表面：螺旋状模具痕迹（纸筒模具特征）
- **缺陷特征**：
  - 漏浆结块（底部不规则扩径，可选）
  - 混凝土强度：C30

### 使用示例

```python
from pile_factory import create_pile_variant

# 创建PHC管桩
pile, hoop = create_pile_variant(
    pile_type="PHC",
    location=np.array([10.0, 20.0]),
    terrain_z=0.5,
    diameter=400,
    exposed_height=0.4,
    age_state="new",
    has_hoop_clamp=True,
    has_cracked_top=False,
    asset_path="../assets"
)

# 创建螺旋钢桩
pipe, flange = create_pile_variant(
    pile_type="spiral_steel",
    location=np.array([15.0, 25.0]),
    terrain_z=0.5,
    pipe_diameter=89,
    total_length=2.0,
    exposed_height=0.3,
    rust_level="light",
    asset_path="../assets"
)
```

## 模块二：基于规范的智能排布算法 (`pile_layout_engine.py`)

### 功能

严格遵循 **GB 50797-2012《光伏发电站设计规范》**，实现约束驱动的排布逻辑。

#### 1. 随坡与阶梯逻辑

- **动态排间距计算**：
  - 根据地形坡度动态计算排间距（防遮挡逻辑）
  - 北坡间距大，南坡间距小
  - 公式：`spacing = base_spacing × direction_factor × slope_factor`
  - 参考报告 2.1 节：标准配置 2×5（10根桩），东西向柱距 3.6m

- **阶梯状桩组（Table）**：
  - 同一组内（约10根桩）的桩顶必须在同一平面上
  - 允许通过调节桩的露出高度（300mm-1000mm）来补偿地形起伏
  - 同组桩顶标高差：≤40mm（参考报告）

#### 2. 工程容差注入

- **行内约束**：
  - 同一排桩的圆心偏差极小（<10mm），模拟打桩放线的高精度
- **垂直度偏差**：
  - 每根桩添加微小的随机倾斜（<0.5%），模拟施工误差
- **列间抖动**：
  - 排与排之间的对齐相对宽松（±20cm）

### 使用示例

```python
from pile_layout_engine import layout_piles_with_constraints

# 基于规范的智能排布
pile_info_list = layout_piles_with_constraints(
    terrain=terrain,
    area_size=200.0,
    num_groups=20,
    piles_per_group=10,
    road_width=8.0,
    asset_path="../assets"
)

# pile_info_list 包含每个桩的位置、类型、参数等信息
for pile_info in pile_info_list:
    pos = pile_info['position']
    terrain_z = pile_info['terrain_z']
    tilt = pile_info['tilt']
    pile_type = pile_info['pile_type']
    pile_params = pile_info['pile_params']
```

## 模块三：环境叙事与痕迹生成 (`environmental_storytelling.py`)

### 功能

为了消除"CG感"，增加真实的环境细节。

#### 1. 机械车辙 (Track Marks)

- **特征**：
  - 在每一排桩的间隙（行进通道）生成平行的履带车辙印
  - 车辙宽度：700mm
  - 履带间距：1.8m
- **实现**：
  - 使用 Blender 的置换修改器使车辙处地面轻微下陷（5cm）
  - 改变车辙处的粗糙度和颜色（变深，模拟翻出的湿土）
  - 使用程序化纹理（条纹+噪声）模拟履带印

#### 2. 施工废料 (Construction Debris)

- **类型**（按概率生成，30%概率）：
  - **截断的混凝土饼**：不规则形状，深灰色，粗糙材质
  - **锈蚀的短钢筋头**：圆柱体，锈色金属材质
  - **白色石灰粉线**：平面，高亮度，轻微发光
- **位置**：桩基周围1米范围内

#### 3. 地质特征匹配

- **Config_Loess（黄土高原）**：
  - 推荐桩型：螺旋钢桩（70%概率）
  - 地形颜色：干燥黄土色
  - 特征：风积沙、低植被密度（10%）
  
- **Config_Hills（南方丘陵）**：
  - 推荐桩型：PHC桩（60%概率）
  - 地形颜色：红粘土色
  - 特征：植被痕迹、中等植被密度（50%）

### 使用示例

```python
from environmental_storytelling import (
    create_track_marks,
    create_construction_debris,
    configure_geological_preset,
    add_vegetation_traces
)

# 配置地质预设
preset_config = configure_geological_preset(terrain, "loess", asset_path)
add_vegetation_traces(terrain, preset_config, asset_path)

# 创建车辙
create_track_marks(terrain, pile_positions)

# 创建施工废料
debris_objects = create_construction_debris(
    terrain,
    pile_positions,
    debris_probability=0.3
)
```

## 主脚本集成

### 新增命令行参数

```bash
# 启用高级功能（默认启用）
--use_advanced_features

# 选择地质预设
--geological_preset {loess,hills}  # 可选，不设置则随机选择
```

### 使用示例

```bash
# 使用高级功能生成图像（黄土高原预设）
blenderproc run generate_mountainous_solar_site.py output/dataset \
    --image_index 0 \
    --seed 1000 \
    --use_clusters \
    --use_advanced_features \
    --geological_preset loess \
    --use_gpu \
    --max_samples 50

# 使用高级功能生成图像（南方丘陵预设）
blenderproc run generate_mountainous_solar_site.py output/dataset \
    --image_index 1 \
    --seed 1001 \
    --use_clusters \
    --use_advanced_features \
    --geological_preset hills \
    --use_gpu \
    --max_samples 50
```

## 技术细节

### 材质系统

- 充分利用 Blender 的节点系统混合纹理
- 支持 PBR 纹理（Base Color, Normal, Roughness, Displacement, AO）
- 混凝土纹理缓存机制，避免重复加载

### 几何建模

- PHC 管桩：使用布尔修改器创建空心圆柱
- 螺旋钢桩：使用环形几何体模拟螺旋叶片
- 灌注桩：使用噪声纹理模拟螺旋模具痕迹

### 性能优化

- 全局纹理缓存（`_CONCRETE_TEXTURE_CACHE`）
- 可选的高级功能（向后兼容，可回退到基础模式）

## 向后兼容性

- 如果新模块导入失败，自动回退到原有的简单桩基生成逻辑
- 通过 `--use_advanced_features` 参数控制是否使用高级功能
- 默认启用高级功能，但可通过参数禁用

## 参考标准

- **GB 50797-2012**《光伏发电站设计规范》
- 《光伏板桩特征调研报告》表 5.1 和 表 3-1
- 报告 2.1 节：桩间距（东西向跨距）
- 报告 5.2 节：随坡与阶梯逻辑

## 文件结构

```
BlenderProc/
├── pile_factory.py                    # 模块一：高保真桩基资产库
├── pile_layout_engine.py              # 模块二：智能排布算法
├── environmental_storytelling.py       # 模块三：环境叙事
├── generate_mountainous_solar_site.py # 主脚本（已集成）
└── PHOTOREALISM_REFACTOR.md          # 本文档
```

## 下一步

1. **测试验证**：使用实际数据验证生成图像的质量
2. **参数调优**：根据真实图像调整材质参数、光照参数等
3. **性能优化**：优化渲染速度，特别是高级功能的性能
4. **扩展功能**：根据需求添加更多桩基变体和环境细节

## 注意事项

- 新模块需要在 `blenderproc run` 环境中运行
- 确保资产路径正确（用于加载混凝土纹理等）
- 高级功能会增加渲染时间，但显著提升真实感
- 如果遇到问题，可以禁用高级功能回退到基础模式

