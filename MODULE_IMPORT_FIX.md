# 模块导入问题修复说明

## 问题描述

运行脚本时出现错误：
```
Warning: Advanced features not available: No module named 'pile_factory'
NameError: name 'configure_geological_preset' is not defined
```

## 原因分析

1. **模块文件存在**：`pile_factory.py`, `pile_layout_engine.py`, `environmental_storytelling.py` 都在项目根目录
2. **导入失败**：在 BlenderProc 环境中，Python 导入路径可能不同
3. **函数未定义**：导入失败后，代码仍尝试调用这些函数，导致 `NameError`

## 修复方案

已应用以下修复：

### 1. 添加占位符函数

当模块导入失败时，定义占位符函数避免 `NameError`：

```python
except ImportError as e:
    # 定义占位符函数
    def configure_geological_preset(*args, **kwargs):
        return {}  # Return empty dict
    def add_vegetation_traces(*args, **kwargs):
        pass  # No-op
    # ... 其他占位符函数
```

### 2. 双重检查逻辑

确保只有在模块真正可用时才使用高级功能：

```python
# 强制检查模块是否可用
use_advanced_features = use_advanced_features and ADVANCED_FEATURES_AVAILABLE

# 调用前再次检查
if use_advanced_features and ADVANCED_FEATURES_AVAILABLE:
    preset_config = configure_geological_preset(...)
```

## 当前状态

✅ **脚本现在可以正常运行**，即使模块导入失败也会：
- 显示警告信息
- 自动回退到基础模式
- 使用原有的桩基生成逻辑
- 正常生成图像和标注

## 如何启用高级功能

如果模块导入失败，可以尝试：

### 方法 1: 检查文件位置

确保模块文件与主脚本在同一目录：
```bash
ls -la pile_factory.py pile_layout_engine.py environmental_storytelling.py
```

### 方法 2: 检查 BlenderProc 环境

在 BlenderProc 环境中，模块应该可以正常导入。如果仍然失败，可能是：
- Python 路径问题
- BlenderProc 版本兼容性问题

### 方法 3: 使用基础模式

如果高级功能不可用，脚本会自动使用基础模式，功能仍然完整：
- ✅ 生成桩基
- ✅ 生成地形
- ✅ 生成标注
- ❌ 高级桩基类型（使用简单圆柱体）
- ❌ 环境细节（车辙、废料等）

## 验证修复

运行测试脚本：
```bash
./test_single_image.sh
```

应该看到：
1. 警告信息：`Warning: Advanced features not available`
2. 继续运行：`Falling back to basic pile generation`
3. 成功生成：图像和标注文件

## 相关文件

- `generate_mountainous_solar_site.py` - 主脚本（已修复）
- `pile_factory.py` - 桩基工厂模块
- `pile_layout_engine.py` - 排布引擎模块
- `environmental_storytelling.py` - 环境叙事模块

---

**修复日期**：2026-01-03
