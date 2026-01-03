# 快速开始指南

## 🚀 三步开始

### 1. 单张图像生成（测试）

```bash
blenderproc run generate_mountainous_solar_site.py output/test \
    --image_index 0 \
    --seed 1000 \
    --use_clusters \
    --use_advanced_features \
    --use_gpu
```

### 2. 批量生成（生产）

```bash
./run_parallel.sh 2 20 output/dataset 1000
```

### 3. 查看结果

```bash
ls output/dataset/images/  # 图像
ls output/dataset/labels/  # YOLO标注
```

## 📁 核心文件

| 文件 | 用途 |
|------|------|
| `generate_mountainous_solar_site.py` | 主程序 ⭐ |
| `run_parallel.sh` | 并行执行脚本 ⭐ |
| `pile_factory.py` | 桩基工厂模块 |
| `pile_layout_engine.py` | 排布算法模块 |
| `environmental_storytelling.py` | 环境细节模块 |

## 📚 重要文档

- `PROJECT_INDEX.md` - 完整文件索引
- `docs/solar_farm/architecture/PHOTOREALISM_REFACTOR.md` - 照片级真实感重构
- `docs/solar_farm/architecture/ARCHITECTURE_REFACTOR.md` - 架构说明
- `AGENTS.md` - AI代理指南

## ⚙️ 常用参数

```bash
--use_advanced_features    # 启用高级功能（默认开启）
--geological_preset loess  # 地质预设：loess（黄土）或 hills（丘陵）
--use_clusters            # 使用集群模式
--use_gpu                 # GPU加速（Metal on Apple Silicon）
--max_samples 50          # 渲染采样数（50=快速，100=高质量）
```

## 🔧 故障排查

1. **查看日志**：`output/dataset/logs/image_*.log`
2. **检查文档**：`PROJECT_INDEX.md` 中的问题排查部分
3. **验证安装**：`./install_blender_dependencies.sh`

