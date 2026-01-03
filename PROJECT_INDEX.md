# 项目文件索引

本文档整理了当前目录中的脚本、主程序和文档，方便快速查找和使用。

## 📁 目录结构

```
BlenderProc/
├── 📜 主程序脚本
├── 🔧 工具脚本
├── 📚 文档
└── 🧪 测试与示例
```

---

## 📜 主程序脚本

### 核心生成脚本

#### 1. `generate_mountainous_solar_site.py` ⭐ **主要脚本**
- **功能**：生成山地光伏建设工地的合成数据集
- **特性**：
  - 高保真桩基资产（PHC、螺旋钢桩、灌注桩）
  - 基于GB 50797-2012规范的智能排布
  - 环境叙事（车辙、废料、地质特征）
  - 支持批量生成和并行渲染
- **使用**：
  ```bash
  blenderproc run generate_mountainous_solar_site.py output/dataset \
      --image_index 0 \
      --seed 1000 \
      --use_clusters \
      --use_advanced_features \
      --geological_preset loess \
      --use_gpu
  ```
- **相关文档**：`docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md`

#### 2. `generate_solar_farm_dataset.py`
- **功能**：基础版本的光伏农场数据集生成器
- **特点**：简单场景，用于测试和验证
- **状态**：已过时，建议使用 `generate_mountainous_solar_site.py`

#### 3. `generate_solar_farm_simple.py`
- **功能**：最简化的测试版本
- **特点**：最小化场景，用于调试
- **状态**：仅用于开发测试

---

## 🔧 工具脚本

### 并行执行脚本

#### `run_parallel.sh` ⭐ **推荐使用**
- **功能**：并行执行多个图像生成任务（单进程单图模式）
- **特点**：
  - 避免内存泄漏和GPU上下文重用问题
  - 自动管理并发进程
  - 生成日志文件
- **使用**：
  ```bash
  ./run_parallel.sh [num_parallel] [total_images] [output_dir] [base_seed]
  # 示例：
  ./run_parallel.sh 2 20 output/dataset 1000
  ```
- **相关文档**：`docs/solar_farm/architecture/ARCHITECTURE_REFACTOR.md`

### 安装与配置脚本

#### `install_blender_dependencies.sh`
- **功能**：安装Blender的Python依赖包
- **使用**：`./install_blender_dependencies.sh`

#### `download_blender.sh`
- **功能**：下载Blender（macOS）
- **使用**：`./download_blender.sh`

---

## 🧩 模块化组件

### 高保真桩基资产库

#### `pile_factory.py`
- **功能**：生成三种类型的桩基（PHC、螺旋钢桩、灌注桩）
- **接口**：`create_pile_variant(pile_type, location, terrain_z, **kwargs)`
- **参考**：`docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` 模块一

#### `pile_layout_engine.py`
- **功能**：基于GB 50797-2012规范的智能排布算法
- **特性**：
  - 随坡与阶梯逻辑
  - 工程容差注入
  - 动态排间距计算
- **参考**：`docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` 模块二

#### `environmental_storytelling.py`
- **功能**：环境叙事与痕迹生成
- **特性**：
  - 机械车辙
  - 施工废料
  - 地质特征匹配
- **参考**：`docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` 模块三

---

## 📚 文档

### 核心文档

#### `README.md`
- **内容**：项目主README（BlenderProc官方文档）

#### `README_solar_farm.md`
- **内容**：光伏农场数据集生成项目说明

#### `AGENTS.md` ⭐
- **内容**：AI代理工作指南，包含项目概述、开发环境、常见问题
- **用途**：为AI助手提供项目上下文

### 架构与设计文档

#### `docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` ⭐ **重要**
- **内容**：照片级真实感重构总结
- **包含**：
  - 三个核心模块的详细说明
  - 使用示例
  - 技术细节
  - 参考标准

#### `docs/solar_farm/architecture/ARCHITECTURE_REFACTOR.md`
- **内容**：单进程单图架构重构说明
- **包含**：
  - 重构原因
  - 架构变更
  - 使用方法

#### `docs/solar_farm/analysis/PROGRAM_LOGIC_AND_DEBUGGING.md`
- **内容**：程序逻辑和调试指南
- **用途**：帮助理解代码流程和排查问题

### 问题修复文档

#### `FIXES_APPLIED.md`
- **内容**：已应用的修复总结

#### `docs/solar_farm/changelog/CODE_CHANGES_SUMMARY.md`
- **内容**：代码变更摘要

#### `DEBUG_SESSION_SUMMARY.md`
- **内容**：调试会话总结

### 功能特定文档

#### `docs/solar_farm/guides/GPU_ACCELERATION_README.md`
- **内容**：GPU加速配置说明（Metal for Apple Silicon）

#### `docs/solar_farm/analysis/REAL_DATA_ANALYSIS.md`
- **内容**：真实数据分析（分辨率、对象大小等）

#### `docs/solar_farm/guides/TEXTURE_RECOMMENDATIONS.md`
- **内容**：纹理推荐和使用指南

### 问题诊断文档

#### `PURE_COLOR_IMAGE_FIX.md`
- **内容**：纯色图片问题修复

#### `CAMERA_POSITION_DEBUG.md`
- **内容**：相机位置调试记录

#### `CAMERA_LOOKAT_FIX.md`
- **内容**：相机look-at功能修复

#### `SCALE_FIX_SUMMARY.md`
- **内容**：比例修复总结

#### `SEGMENTATION_VERIFICATION.md`
- **内容**：分割验证说明

#### `OUTPUT_VALIDATION.md`
- **内容**：输出验证指南

### 安装与配置文档

#### `docs/solar_farm/guides/INSTALLATION_CN.md`
- **内容**：中文安装指南

#### `docs/solar_farm/guides/FIX_SSL_AND_BLENDER.md`
- **内容**：SSL证书和Blender安装问题修复

#### `docs/solar_farm/guides/BLENDER_VERSION_COMPATIBILITY.md`
- **内容**：Blender版本兼容性说明

### 归档文档（已过时，仅供参考）

以下文档已移动到 `docs/archive/`，保留作为历史参考：

- `FIX_SUMMARY.md`, `FIXES_APPLIED.md` - 修复总结
- `PURE_COLOR_IMAGE_FIX.md`, `CAMERA_POSITION_DEBUG.md` - 问题修复
- `OPTIMIZATION_RESULTS.md`, `NEW_APPROACH.md` - 优化记录
- 其他过时文档请查看 `docs/archive/README.md`

### 其他文档

#### `docs/solar_farm/changelog/PROJECT_SUMMARY.md`
- **内容**：项目总结

#### `docs/solar_farm/changelog/SUCCESS_REPORT.md`
- **内容**：成功报告

#### `OPTIMIZATION_RESULTS.md`
- **内容**：优化结果

#### `docs/solar_farm/guides/SCENE_IMPROVEMENT_GUIDE.md`
- **内容**：场景改进指南

#### `NEW_APPROACH.md`
- **内容**：新方法说明

#### `VIEW_OUTPUT.md`
- **内容**：查看输出指南

---

## 🚀 快速开始

### 1. 单张图像生成

```bash
blenderproc run generate_mountainous_solar_site.py output/test \
    --image_index 0 \
    --seed 1000 \
    --use_clusters \
    --use_advanced_features \
    --use_gpu
```

### 2. 批量生成（推荐）

```bash
./run_parallel.sh 2 20 output/dataset 1000
```

### 3. 查看文档

- **新用户**：阅读 `README_solar_farm.md` 和 `AGENTS.md`
- **开发者**：阅读 `docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` 和 `docs/solar_farm/architecture/ARCHITECTURE_REFACTOR.md`
- **问题排查**：查看相应的 `*_FIX.md` 或 `*_DEBUG.md` 文档

---

## 📋 文件分类

### 按用途分类

| 类别 | 文件 |
|------|------|
| **主程序** | `generate_mountainous_solar_site.py` |
| **工具脚本** | `run_parallel.sh`, `install_blender_dependencies.sh`, `download_blender.sh` |
| **模块组件** | `pile_factory.py`, `pile_layout_engine.py`, `environmental_storytelling.py` |
| **核心文档** | `README_solar_farm.md`, `AGENTS.md`, `docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` |
| **问题修复** | `FIXES_APPLIED.md`, `docs/solar_farm/changelog/CODE_CHANGES_SUMMARY.md`, `*_FIX.md` |
| **调试指南** | `docs/solar_farm/analysis/PROGRAM_LOGIC_AND_DEBUGGING.md`, `*_DEBUG.md` |

### 按重要性分类

#### ⭐ 必读文档
1. `AGENTS.md` - AI代理工作指南
2. `docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` - 照片级真实感重构
3. `docs/solar_farm/architecture/ARCHITECTURE_REFACTOR.md` - 架构重构说明
4. `README_solar_farm.md` - 项目说明

#### 📖 参考文档
- `docs/solar_farm/analysis/PROGRAM_LOGIC_AND_DEBUGGING.md` - 程序逻辑
- `docs/solar_farm/guides/GPU_ACCELERATION_README.md` - GPU加速
- `docs/solar_farm/analysis/REAL_DATA_ANALYSIS.md` - 真实数据分析

#### 🔍 问题排查
- `*_FIX.md` - 各种问题修复
- `*_DEBUG.md` - 调试记录
- `*_SUMMARY.md` - 修复总结

---

## 🔄 文件状态

### 当前推荐使用
- ✅ `generate_mountainous_solar_site.py` - 主程序
- ✅ `run_parallel.sh` - 并行执行
- ✅ `pile_factory.py` - 桩基工厂
- ✅ `pile_layout_engine.py` - 排布引擎
- ✅ `environmental_storytelling.py` - 环境叙事

### 已过时（保留用于参考）
- ⚠️ `generate_solar_farm_dataset.py` - 基础版本
- ⚠️ `generate_solar_farm_simple.py` - 简化版本

### 文档维护状态
- ✅ 核心文档：已更新
- ✅ 架构文档：已更新
- ⚠️ 部分修复文档：可能已过时，需验证

---

## 📝 更新日志

- **2026-01-02**：创建项目索引文档
- **2026-01-02**：完成照片级真实感重构
- **2026-01-02**：实现单进程单图架构

---

## 💡 提示

1. **首次使用**：先阅读 `README_solar_farm.md` 和 `AGENTS.md`
2. **遇到问题**：查看相应的 `*_FIX.md` 或 `*_DEBUG.md` 文档
3. **开发新功能**：参考 `docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` 的模块化设计
4. **批量生成**：使用 `run_parallel.sh` 而不是在Python中循环

---

**最后更新**：2026-01-02

