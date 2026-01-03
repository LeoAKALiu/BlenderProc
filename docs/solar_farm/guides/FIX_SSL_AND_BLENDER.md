# 解决 SSL 证书和 Blender 下载问题

## 问题描述

运行 `blenderproc run` 时遇到 SSL 证书验证失败，无法自动下载 Blender。

## 解决方案

### 方案 1: 手动下载并安装 Blender（推荐）

1. **手动下载 Blender 4.2.1**:
   - 访问: https://www.blender.org/download/
   - 或直接下载 macOS ARM64 版本:
   ```bash
   # 下载 Blender 4.2.1 for macOS ARM64
   curl -L -o ~/Downloads/blender-4.2.1-macos-arm64.dmg \
     "https://download.blender.org/release/Blender4.2/blender-4.2.1-macos-arm64.dmg"
   ```

2. **安装 Blender**:
   - 打开下载的 `.dmg` 文件
   - 将 Blender.app 拖到 Applications 文件夹

3. **使用自定义 Blender 路径运行**:
   ```bash
   export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
   blenderproc run generate_solar_farm_dataset.py output/solar_farm \
     --custom-blender-path "/Applications/Blender.app" \
     --num_cameras 5
   ```
   
   **重要**: `--custom-blender-path` 必须指向 `Blender.app` 的路径，**不是**可执行文件的路径！
   - ✅ 正确: `/Applications/Blender.app`
   - ❌ 错误: `/Applications/Blender.app/Contents/MacOS/Blender`

### 方案 2: 修复 SSL 证书（macOS）

macOS 上 Python 的 SSL 证书问题通常需要安装证书：

```bash
# 安装 Python 证书
/Applications/Python\ 3.12/Install\ Certificates.command

# 或者使用 pip 安装 certifi
python3 -m pip install --upgrade certifi
```

如果上述命令不存在，尝试：

```bash
# 找到 Python 安装目录
python3 -c "import sys; print(sys.executable)"

# 然后运行（如果存在）
/Applications/Python\ 3.12/Install\ Certificates.command
```

### 方案 3: 临时禁用 SSL 验证（不推荐，仅用于测试）

**警告**: 这会降低安全性，仅用于测试环境。

设置环境变量：

```bash
export PYTHONHTTPSVERIFY=0
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
blenderproc run generate_solar_farm_dataset.py output/solar_farm --num_cameras 5
```

### 方案 4: 使用 Homebrew 安装 Blender

如果你使用 Homebrew：

```bash
# 安装 Blender
brew install --cask blender

# 然后使用自定义路径
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
blenderproc run generate_solar_farm_dataset.py output/solar_farm \
  --custom-blender-path "/opt/homebrew/bin/blender" \
  --num_cameras 5
```

## 验证 Blender 安装

检查 Blender 是否已安装：

```bash
# 查找 Blender
find /Applications -name "Blender.app" 2>/dev/null
find /opt/homebrew -name "blender" 2>/dev/null

# 如果找到，获取可执行文件路径
# macOS App Bundle:
/Applications/Blender.app/Contents/MacOS/Blender --version

# Homebrew:
/opt/homebrew/bin/blender --version
```

## 推荐步骤

1. **首先尝试方案 1**（手动下载 Blender）- 最可靠
2. 如果已安装 Blender，使用 `--custom-blender-path` 参数
3. 如果需要自动下载，尝试方案 2（修复 SSL 证书）

## 快速命令

如果 Blender 已安装在 Applications：

```bash
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"
blenderproc run generate_solar_farm_dataset.py output/solar_farm \
  --custom-blender-path "/Applications/Blender.app" \
  --num_cameras 5
```

**注意**: 
- 第一次运行时会自动安装依赖包到 Blender 的 Python 环境，这可能需要几分钟
- 确保使用 `Blender.app` 路径，而不是可执行文件路径

