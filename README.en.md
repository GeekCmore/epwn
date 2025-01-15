# epwn

[中文](README.md) | English

epwn is a powerful GLIBC version management and ELF binary patching tool. It helps you download and manage different versions of GLIBC, and patch ELF binaries to use specific GLIBC versions.

## Features

- 🔍 Automatically crawl and download specific GLIBC packages
- 📦 Manage multiple GLIBC versions
- 🛠 Patch ELF binaries to use specific GLIBC versions
- 🧪 Comprehensive testing functionality
- 💻 Supports both CLI and Python API

## Installation

### Requirements

- Python >= 3.8
- Linux operating system

### Install via pip

```bash
pip install epwn
```

### Install from source

```bash
git clone https://github.com/GeekCmore/epwn.git
cd epwn
pip install -e .
```

## Command Line Usage

epwn provides two main command groups: `glibc` and `patch`, each containing multiple subcommands.

### GLIBC Management Commands

#### List Installed Versions
```bash
epwn glibc list
```

#### Install GLIBC
```bash
# Install a specific version
epwn glibc install --version 2.31-0ubuntu9

# Install a specific version with debug packages
epwn glibc install --version 2.31-0ubuntu9 -p libc6 -p libc6-dbg

# Install the latest 3 subversions of all versions
epwn glibc install --nums 3

# Complete options reference
epwn glibc install [OPTIONS]
  Options:
    --version TEXT    GLIBC version number
    --arch TEXT      System architecture (default: amd64)
    --force         Force reinstallation
    --nums INTEGER  Number of latest subversions to keep per version (default: 3)
    -p, --packages  Packages to download [libc6|libc6-dbg|glibc-source] (multiple allowed)
```

### ELF Patching Commands

#### Interactive GLIBC Version Selection
```bash
# Select a GLIBC version from installed versions to patch the binary
epwn patch choose your_binary
epwn patch choose your_binary --no-backup  # Don't create backup
```

#### Automatic GLIBC Version Matching
```bash
# Automatically select appropriate GLIBC version based on provided libc file
epwn patch auto your_binary path/to/libc.so.6

# Complete options reference
epwn patch auto [OPTIONS] ELF_FILE LIBC_FILE
  Options:
    --backup/--no-backup     Create backup or not (default: enabled)
    -p, --packages          Packages to download [libc6|libc6-dbg|glibc-source] (multiple allowed)
```

## Python API Usage

epwn can also be used as a Python library, providing a flexible API interface.

### GLIBC Download and Management

```python
from epwn.core.downloader import Downloader
from epwn.core.crawler import GlibcCrawler

# Get GLIBC download links
crawler = GlibcCrawler()
version_info = crawler.getOnePackageDownloadUrl(
    version="2.31-0ubuntu9",
    architectures=["amd64"],
    packages=["libc6", "libc6-dbg"]
)

# Download GLIBC packages
downloader = Downloader(save_dir="downloads")
results = downloader.download(version_info.get_urls())
```

### ELF Patching Operations

```python
from epwn.core.patcher import GlibcPatcher

# Create patcher instance
patcher = GlibcPatcher()

# Add GLIBC
version, interpreter = patcher.add_libc("path/to/libc.so.6")

# Patch binary
patcher.patch_binary("your_binary", interpreter)
```

## Project Structure

```
epwn/
├── cli/                # Command line interface
│   ├── commands/      # Command implementations
│   └── main.py        # CLI entry point
├── core/              # Core functionality
│   ├── crawler.py     # GLIBC package crawler
│   ├── downloader.py  # Package downloader
│   ├── extractor.py   # Package extractor
│   ├── patcher.py     # ELF patcher
│   └── version.py     # Version management
└── example/           # Usage examples
```

## Dependencies

- click >= 8.0.0
- rich >= 10.0.0
- requests >= 2.25.0
- beautifulsoup4 >= 4.9.0

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details 