# BlenderProc 安装指南

## 是的，BlenderProc 需要安装/部署

BlenderProc 必须在 Blender 的 Python 环境中运行，因此需要特殊安装。

## 安装方法

### 方法 1: 通过 pip 安装（推荐）

这是最简单的方式：

```bash
pip install blenderproc
```

安装后，你可以使用 `blenderproc` 命令运行脚本。

### 方法 2: 从源码安装（当前目录）

由于你已经在 BlenderProc 源码目录中，可以进行本地安装：

```bash
# 确保在 BlenderProc 根目录
cd /Users/leo/code/pileSim/BlenderProc

# 进行可编辑安装（开发模式）
pip install -e .
```

这样安装后，`blenderproc` 命令可以在系统任何地方使用。

## 验证安装

安装完成后，测试是否成功：

```bash
# 检查 blenderproc 命令是否可用
blenderproc --help

# 运行快速测试
blenderproc quickstart
```

## 运行你的脚本

安装完成后，使用以下命令运行生成脚本：

```bash
# 基本用法
blenderproc run generate_solar_farm_dataset.py output/solar_farm

# 带参数
blenderproc run generate_solar_farm_dataset.py output/solar_farm \
    --num_piles_x 10 \
    --num_piles_y 8 \
    --num_cameras 20
```

## 重要说明

1. **不能直接用 Python 运行**: BlenderProc 脚本不能直接用 `python script.py` 运行
2. **必须使用 blenderproc 命令**: 必须使用 `blenderproc run script.py` 来运行
3. **需要 Blender**: BlenderProc 依赖 Blender，安装时会自动处理

## 依赖项

安装时会自动安装以下依赖：
- setuptools
- pyyaml
- requests
- matplotlib
- numpy
- Pillow
- h5py
- progressbar

## 故障排除

### SSL 证书问题

如果遇到 SSL 证书错误（如 `SSLError`），使用以下命令：

```bash
python3 -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -e .
```

### PATH 问题

如果安装后 `blenderproc` 命令找不到，需要将 Python bin 目录添加到 PATH：

```bash
# 临时添加（当前终端会话）
export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"

# 永久添加（添加到 ~/.zshrc 或 ~/.bash_profile）
echo 'export PATH="/Users/leo/Library/Python/3.12/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

或者直接使用完整路径：
```bash
/Users/leo/Library/Python/3.12/bin/blenderproc --help
```

### 其他问题

1. **检查 Python 版本**: 需要 Python 3.7+
   ```bash
   python3 --version
   ```

2. **检查 pip**: 确保 pip 是最新的
   ```bash
   python3 -m pip install --upgrade pip
   ```

3. **重新安装**: 如果安装失败，尝试：
   ```bash
   python3 -m pip uninstall blenderproc
   python3 -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -e .
   ```

## 下一步

安装完成后，查看 `README_solar_farm.md` 了解如何使用生成脚本。

