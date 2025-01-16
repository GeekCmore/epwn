# epwn

中文 | [English](README.en.md)

epwn 是一个强大的 GLIBC 版本管理和 ELF 二进制补丁工具。它可以帮助你下载、管理不同版本的 GLIBC，并为 ELF 二进制文件打补丁以使用特定版本的 GLIBC。

## 功能特点

- 🔍 自动爬取和下载指定版本的 GLIBC 包
- 📦 管理多个 GLIBC 版本
- 🛠 为 ELF 二进制文件打补丁，使其使用指定版本的 GLIBC
- 🧪 提供完整的测试功能
- 💻 同时支持命令行界面和 Python API

## 安装

### 系统要求

- Python >= 3.8
- Linux 操作系统

### 通过 pip 安装

```bash
pip install epwn
```

### 从源码安装

```bash
git clone https://github.com/GeekCmore/epwn.git
cd epwn
pip install -e .
```

## 命令行使用

epwn 提供了两个主要命令组：`glibc` 和 `patch`，每个命令组都包含多个子命令。

### GLIBC 管理命令

#### 查看已安装版本
```bash
epwn glibc list
```

#### 安装 GLIBC
```bash
# 安装指定版本
epwn glibc install --version 2.31-0ubuntu9

# 安装指定版本并下载调试包
epwn glibc install --version 2.31-0ubuntu9 -p libc6 -p libc6-dbg

# 安装所有版本的最新3个子版本
epwn glibc install --nums 3

# 完整选项说明
epwn glibc install [选项]
  选项:
    --version TEXT    指定GLIBC版本号
    --arch TEXT      系统架构 (默认: amd64)
    --force         强制重新安装
    --nums INTEGER  每个版本保留的最新子版本数量 (默认: 3)
    -p, --packages  需要下载的包 [libc6|libc6-dbg|glibc-source] (可多选)
```

#### 清理所有文件
```bash
# 清理所有epwn相关的文件和目录（会提示确认）
epwn glibc clean

# 强制清理，跳过确认
epwn glibc clean --force

# 清理时保留配置文件
epwn glibc clean --keep-config

# 预览将要删除的文件（不实际删除）
epwn glibc clean --dry-run

# 清理时跳过版本管理文件
epwn glibc clean --skip-versions

# 完整选项说明
epwn glibc clean [选项]
  选项:
    --force         跳过确认直接删除
    --keep-config   保留配置文件
    --dry-run      只显示将要删除的文件，不实际删除
    --skip-versions 不删除版本管理相关文件
```

### ELF 补丁命令

#### 交互式选择 GLIBC 版本
```bash
# 从已安装的GLIBC版本中选择一个为二进制文件打补丁
epwn patch choose your_binary
epwn patch choose your_binary --no-backup  # 不创建备份
```

#### 自动匹配 GLIBC 版本
```bash
# 根据提供的libc文件自动选择合适的GLIBC版本
epwn patch auto your_binary path/to/libc.so.6

# 完整选项说明
epwn patch auto [选项] ELF文件 LIBC文件
  选项:
    --backup/--no-backup     是否创建备份 (默认: 启用)
    -p, --packages          需要下载的包 [libc6|libc6-dbg|glibc-source] (可多选)
```

## Python API 使用

epwn 也可以作为 Python 库使用，提供了灵活的 API 接口。

### GLIBC 下载和管理

```python
from epwn.core.downloader import Downloader
from epwn.core.crawler import GlibcCrawler

# 获取 GLIBC 下载链接
crawler = GlibcCrawler()
version_info = crawler.getOnePackageDownloadUrl(
    version="2.31-0ubuntu9",
    architectures=["amd64"],
    packages=["libc6", "libc6-dbg"]
)

# 下载 GLIBC 包
downloader = Downloader(save_dir="downloads")
results = downloader.download(version_info.get_urls())
```

### ELF 补丁操作

```python
from epwn.core.patcher import GlibcPatcher

# 创建 patcher 实例
patcher = GlibcPatcher()

# 添加 GLIBC
version, interpreter = patcher.add_libc("path/to/libc.so.6")

# 为二进制文件打补丁
patcher.patch_binary("your_binary", interpreter)
```

## 项目结构

```
epwn/
├── cli/                # 命令行接口
│   ├── commands/      # 命令实现
│   └── main.py        # CLI 入口
├── core/              # 核心功能
│   ├── crawler.py     # GLIBC 包爬取
│   ├── downloader.py  # 包下载
│   ├── extractor.py   # 包解压
│   ├── patcher.py     # ELF 补丁
│   └── version.py     # 版本管理
└── example/           # 使用示例
```

## 依赖

- click >= 8.0.0
- rich >= 10.0.0
- requests >= 2.25.0
- beautifulsoup4 >= 4.9.0

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件
