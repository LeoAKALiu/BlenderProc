# Blender 版本兼容性问题

## 问题

BlenderProc 2.8.0 是为 **Blender 4.2** 设计的，但你安装的是 **Blender 5.0.1**。

Blender 5.0 在 API 上有一些重大变化，导致兼容性问题。

## 解决方案

### 方案 1: 安装 Blender 4.2（推荐）

1. **下载 Blender 4.2.1**:
   ```bash
   # macOS ARM64
   curl -L -o ~/Downloads/blender-4.2.1-macos-arm64.dmg \
     "https://download.blender.org/release/Blender4.2/blender-4.2.1-macos-arm64.dmg"
   ```

2. **安装并运行**:
   ```bash
   # 打开 DMG 并安装
   open ~/Downloads/blender-4.2.1-macos-arm64.dmg
   
   # 使用 Blender 4.2 运行
   export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
   blenderproc run generate_solar_farm_dataset.py output/solar_farm \
     --custom-blender-path "/Applications/Blender.app/Contents/MacOS/Blender" \
     --num_cameras 5
   ```

### 方案 2: 修复 Blender 5.0 兼容性（需要修改代码）

需要修复多个地方的 `node_tree` 访问问题。主要问题：

1. `bpy.context.scene.node_tree` 在 Blender 5.0 中可能不存在
2. Background 节点需要手动创建

**已修复的位置**:
- `RendererUtility.set_world_background()` - ✅ 已修复
- `RendererUtility.disable_all_denoiser()` - ⚠️ 部分修复，仍有问题

**需要修复的其他位置**:
- `RendererUtility.set_denoiser()` (line 45)
- 其他使用 `bpy.context.scene.node_tree` 的地方

### 方案 3: 使用 BlenderProc 的自动下载（如果 SSL 问题解决）

如果 SSL 证书问题解决，可以让 BlenderProc 自动下载 Blender 4.2：

```bash
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
# 修复 SSL 后
blenderproc run generate_solar_farm_dataset.py output/solar_farm --num_cameras 5
```

## 当前状态

✅ **已完成**:
- BlenderProc 安装
- 所有 Python 依赖包安装到 Blender 环境
- 部分 Blender 5.0 兼容性修复

❌ **待解决**:
- Blender 5.0 API 兼容性问题（`node_tree` 访问）
- 建议使用 Blender 4.2 以获得最佳兼容性

## 快速开始（使用 Blender 4.2）

```bash
# 1. 下载 Blender 4.2.1
./download_blender.sh  # 或手动下载

# 2. 安装依赖（如果还没安装）
./install_blender_dependencies.sh

# 3. 运行脚本
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
blenderproc run generate_solar_farm_dataset.py output/solar_farm \
  --custom-blender-path "/Applications/Blender.app" \
  --num_cameras 5
```






