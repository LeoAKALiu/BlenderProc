# 架构重构总结 - 单进程单图模式

## 重构目标

解决 M3 Pro 上的内存泄漏和 Metal 上下文重用问题，采用"单进程单图"模式，确保每次渲染都拥有干净的内存和 GPU 状态。

## 主要改动

### 1. Python 脚本重构 (`generate_mountainous_solar_site.py`)

#### ✅ 移除的功能
- **批量循环**: 移除了 `for img_idx in range(num_images):` 循环
- **`--num_images` 参数**: 不再需要批量生成参数
- **场景清理代码**: 
  - 移除了 `clean_scene` 参数和相关逻辑
  - 移除了 `gc.collect()` 调用
  - 移除了 `GlobalStorage.set("output", [])` 清理
  - 移除了 `bproc.clean_up()` 调用
- **`seed_offset` 参数**: 不再需要，每个进程独立设置种子
- **渲染错误处理和重试**: 简化渲染代码，移除复杂的错误处理

#### ✅ 新增的功能
- **`--image_index` 参数**: 指定图片索引（用于文件名，如 `000000.png`）
- **独立的随机种子**: 基于 `--seed` 和 `--image_index` 计算唯一种子

#### ✅ 修改的逻辑
- **`main()` 函数**: 
  - 不再包含循环
  - 直接调用一次 `generate_single_image()`
  - 根据 `--image_index` 和 `--seed` 设置随机种子
- **`generate_single_image()` 函数**:
  - 移除了 `clean_scene` 参数
  - 移除了 `seed_offset` 参数
  - 移除了所有清理代码
  - 简化了渲染代码

### 2. 并行脚本重构 (`run_parallel.sh`)

#### ✅ 新的并发控制机制
- **并发限制**: 使用 `PARALLEL_JOBS` 变量（默认 2，适合 M3 Pro）
- **任务队列**: 使用 `wait_for_slot()` 函数确保同时只有指定数量的进程运行
- **进程管理**: 使用 Bash 数组跟踪运行中的进程和对应的图片索引

#### ✅ 新的调用方式
```bash
blenderproc run generate_mountainous_solar_site.py output/dataset \
    --image_index 0 \
    --seed 1000 \
    --use_clusters \
    --use_gpu
```

每次调用生成一张图片，进程完全独立。

## 架构对比

### 重构前（批量模式）
```
main()
  ├─ bproc.init() (一次)
  ├─ for img_idx in range(num_images):
  │   ├─ clean_scene (清理状态)
  │   ├─ gc.collect() (内存清理)
  │   ├─ GlobalStorage 清理
  │   ├─ generate_single_image()
  │   └─ (状态累积，可能导致卡死)
  └─ 完成
```

**问题**:
- 状态在进程内累积
- 内存泄漏累积
- Metal GPU 上下文重用问题
- 渲染卡死

### 重构后（单进程单图模式）
```
run_parallel.sh
  ├─ for image_index in 0..total_images:
  │   └─ blenderproc run script.py --image_index N --seed M
  │       └─ main()
  │           ├─ bproc.init() (全新进程)
  │           ├─ generate_single_image() (一次)
  │           └─ 退出（干净状态）
  └─ 完成
```

**优势**:
- ✅ 每次都是全新进程，无状态累积
- ✅ 每次都是干净的内存空间，无内存泄漏
- ✅ 每次都是新的 Metal 上下文，无上下文重用问题
- ✅ 进程独立，一个失败不影响其他

## 使用方式

### 单张图片测试
```bash
blenderproc run generate_mountainous_solar_site.py output/test \
    --image_index 0 \
    --seed 1000 \
    --use_clusters \
    --use_gpu \
    --max_samples 50
```

### 并行批量生成
```bash
# 2 个并行进程，生成 20 张图片
./run_parallel.sh 2 20 output/dataset 1000

# 参数说明:
#   1. 并行进程数 (2 - 适合 M3 Pro)
#   2. 总图片数 (20)
#   3. 输出目录 (output/dataset)
#   4. 基础种子 (1000 - 每张图片的种子 = 1000 + image_index)
```

### 自定义参数
```bash
# 生成单张图片，自定义参数
blenderproc run generate_mountainous_solar_site.py output/test \
    --image_index 5 \
    --seed 2000 \
    --use_clusters \
    --num_clusters 3 \
    --terrain_size 200.0 \
    --use_gpu \
    --max_samples 100
```

## 输出结构

所有图片和标注都保存在同一个目录下：

```
output/dataset/
├── images/
│   ├── 000000.png
│   ├── 000001.png
│   ├── 000002.png
│   └── ...
├── labels/
│   ├── 000000.txt
│   ├── 000001.txt
│   ├── 000002.txt
│   └── ...
└── image_*.log  (每张图片的日志)
```

## 性能优化

### 并发数建议
- **M3 Pro (16GB)**: 2 个并行进程（避免内存不足）
- **M3 Max (32GB+)**: 可以尝试 3-4 个并行进程

### 渲染参数
- **快速测试**: `--max_samples 30 --noise_threshold 0.02`
- **训练数据**: `--max_samples 50 --noise_threshold 0.01` (默认)
- **高质量**: `--max_samples 100 --noise_threshold 0.005`

## 优势总结

1. **解决卡死问题**: 每次都是全新进程，无状态累积
2. **解决内存泄漏**: 进程退出时自动释放所有内存
3. **解决 GPU 上下文问题**: 每次都是新的 Metal 上下文
4. **更好的错误隔离**: 一个进程失败不影响其他
5. **更灵活的并行控制**: 可以动态调整并发数
6. **更简单的代码**: 移除了大量清理和错误处理代码

## 注意事项

1. **进程启动开销**: 每个进程都需要启动 Blender，有少量开销
2. **并发数限制**: 不要设置过高的并发数，避免内存不足
3. **日志文件**: 每张图片都有独立的日志文件，便于调试
4. **种子管理**: 确保每张图片使用不同的种子（通过 `base_seed + image_index`）

## 故障排除

### 如果仍然卡住
1. 检查日志文件: `cat output/dataset/image_000000.log`
2. 降低并发数: `./run_parallel.sh 1 10 output/test 1000`
3. 尝试单进程: 直接运行单张图片测试
4. 检查内存: `top` 或 `Activity Monitor`

### 如果内存不足
1. 减少并发数: `PARALLEL_JOBS=1`
2. 降低采样数: `--max_samples 30`
3. 减少场景复杂度: 减少桩基数量

## 迁移指南

### 从旧版本迁移
1. 不再使用 `--num_images` 参数
2. 使用 `--image_index` 指定图片索引
3. 使用 `run_parallel.sh` 进行批量生成
4. 所有图片保存在同一个 `images/` 和 `labels/` 目录

### 示例对比

**旧方式**:
```bash
blenderproc run script.py output/dataset --num_images 100
```

**新方式**:
```bash
./run_parallel.sh 2 100 output/dataset 1000
```

