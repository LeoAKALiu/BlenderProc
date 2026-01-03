# GPU 加速和并行渲染使用指南

本文档说明如何在 MacBook Pro M3 Pro (Apple Silicon) 上使用 GPU 加速和并行渲染来加速 BlenderProc 数据集生成。

## 功能概述

### 1. GPU 加速（Metal）
- 自动检测并使用 Apple Silicon 的 Metal GPU
- 相比 CPU 渲染，速度提升 **5-10 倍**
- 通过 `--use_gpu` 参数启用（默认启用）

### 2. 渲染优化
- **采样数优化**：默认 100 采样（可通过 `--max_samples` 调整）
- **降噪**：启用 Intel 降噪器，在低采样数下保持质量
- **自适应采样**：噪声阈值 0.01（可通过 `--noise_threshold` 调整）

### 3. 并行渲染
- 支持多进程并行生成
- 每个进程使用不同的 seed，确保数据多样性
- 自动分配任务，等待所有进程完成

## 使用方法

### 方法 1：单进程 GPU 加速（推荐用于测试）

```bash
# 基本使用（启用 GPU，100 采样）
blenderproc run generate_mountainous_solar_site.py output/test \
  --num_images 10 \
  --use_clusters \
  --use_gpu \
  --seed 42

# 自定义采样数和噪声阈值
blenderproc run generate_mountainous_solar_site.py output/test \
  --num_images 10 \
  --use_clusters \
  --use_gpu \
  --max_samples 50 \
  --noise_threshold 0.02 \
  --seed 42
```

### 方法 2：并行渲染（推荐用于批量生成）

```bash
# 使用默认设置（4 个并行进程，100 张图片）
./run_parallel.sh

# 自定义并行进程数和图片总数
./run_parallel.sh 4 100 output/dataset

# 如果遇到内存问题，减少并行进程数
./run_parallel.sh 2 100 output/dataset
```

#### 并行脚本参数说明

```bash
./run_parallel.sh [num_parallel] [total_images] [output_base_dir]
```

- `num_parallel`: 并行进程数（默认：4，M3 Pro 推荐 4，内存不足时改为 2）
- `total_images`: 总图片数（默认：100）
- `output_base_dir`: 输出目录（默认：`output/parallel_dataset`）

#### 并行脚本输出结构

```
output/parallel_dataset/
├── batch_00/          # 进程 0 的输出
│   ├── image_0000/
│   ├── image_0001/
│   └── ...
├── batch_01/          # 进程 1 的输出
│   └── ...
├── batch_00.log       # 进程 0 的日志
└── batch_01.log       # 进程 1 的日志
```

## 性能对比

### CPU vs GPU（单张图片，5280x3956 分辨率）

| 配置 | 采样数 | 渲染时间 | 速度提升 |
|------|--------|----------|----------|
| CPU | 100 | ~5-8 分钟 | 基准 |
| GPU (Metal) | 100 | ~30-60 秒 | **5-10x** |
| GPU (Metal) | 50 | ~15-30 秒 | **10-20x** |

### 并行渲染加速

| 并行进程数 | 100 张图片总时间 | 加速比 |
|-----------|----------------|--------|
| 1 (串行) | ~50-100 分钟 | 1x |
| 2 | ~25-50 分钟 | 2x |
| 4 | ~12-25 分钟 | 4x |

**注意**：实际速度取决于场景复杂度、GPU 内存和系统负载。

## 参数说明

### GPU 和渲染参数

- `--use_gpu`: 启用 GPU 渲染（Metal，默认启用）
- `--max_samples`: 最大采样数（默认：100，范围：50-500）
  - 较低值（50-100）：快速生成，适合训练数据
  - 较高值（200-500）：高质量，适合最终渲染
- `--noise_threshold`: 噪声阈值（默认：0.01，范围：0.001-0.1）
  - 较低值：更少噪声，但需要更多采样
  - 较高值：更快渲染，但可能有更多噪声

### Seed 参数

- `--seed`: 随机种子（用于可重现性和并行执行）
  - 不同 seed 生成不同的随机场景
  - 并行脚本自动为每个进程分配不同的 seed

## 故障排除

### 1. GPU 未启用

**症状**：渲染仍然很慢，日志显示 "Using only the CPU for rendering"

**解决方案**：
```bash
# 检查 Blender 是否支持 Metal
# 在 Blender 中：Edit > Preferences > System > Cycles Render Devices
# 应该看到 "Apple M3 Pro (GPU)"

# 如果看不到，可能需要更新 Blender 版本
```

### 2. 内存不足

**症状**：进程崩溃或系统卡顿

**解决方案**：
```bash
# 减少并行进程数
./run_parallel.sh 2 100 output/dataset

# 或减少每批次的图片数
blenderproc run generate_mountainous_solar_site.py output/test \
  --num_images 5 \
  --use_gpu
```

### 3. 降噪器无法启用

**症状**：警告 "Could not enable Intel denoiser"

**解决方案**：
- 这是正常的，降噪器在某些 Blender 版本中可能不可用
- 渲染会继续，只是没有降噪（可能需要更多采样）

### 4. 并行进程输出混乱

**症状**：日志文件混乱或输出目录冲突

**解决方案**：
- 每个进程使用不同的输出目录（并行脚本已自动处理）
- 每个进程使用不同的 seed（并行脚本已自动处理）
- 检查日志文件：`tail -f output/parallel_dataset/batch_*.log`

## 最佳实践

1. **测试先行**：先用单进程生成少量图片测试 GPU 加速
2. **逐步增加**：从 2 个并行进程开始，逐步增加到 4 个
3. **监控资源**：使用 `Activity Monitor` 监控 GPU 和内存使用
4. **保存日志**：并行脚本会自动保存日志，便于调试
5. **质量平衡**：对于训练数据，50-100 采样通常足够

## 示例工作流

### 快速测试（10 张图片）
```bash
blenderproc run generate_mountainous_solar_site.py output/test \
  --num_images 10 \
  --use_clusters \
  --use_gpu \
  --max_samples 50
```

### 中等批量（100 张图片）
```bash
./run_parallel.sh 4 100 output/dataset
```

### 大规模生成（1000 张图片）
```bash
# 分批次运行，避免内存问题
./run_parallel.sh 4 250 output/dataset_batch1
./run_parallel.sh 4 250 output/dataset_batch2
./run_parallel.sh 4 250 output/dataset_batch3
./run_parallel.sh 4 250 output/dataset_batch4
```

## 技术细节

### GPU 设置实现

代码在 `bproc.init()` 之后自动配置：
```python
bproc.renderer.set_render_devices(
    use_only_cpu=False,
    desired_gpu_device_type="METAL"
)
```

### 渲染优化实现

```python
bproc.renderer.set_max_amount_of_samples(100)
bproc.renderer.set_noise_threshold(0.01)
bproc.renderer.set_denoiser("INTEL")
```

### Seed 管理

- 主进程通过 `--seed` 参数设置基础 seed
- 每张图片使用 `base_seed + image_index` 作为 seed
- 并行进程使用 `1000 + process_id` 作为 seed

## 参考

- [BlenderProc 文档](https://github.com/DLR-RM/BlenderProc)
- [Blender Cycles 渲染设置](https://docs.blender.org/manual/en/latest/render/cycles/index.html)
- [Metal GPU 加速](https://developer.apple.com/metal/)

