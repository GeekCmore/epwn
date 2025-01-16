# EPwn

[English](README.en.md) | 简体中文

EPwn 是一个强大的 GLIBC 版本管理和 ELF 文件补丁工具，专为 CTF 选手和二进制安全研究人员设计。

## 功能特点

- **GLIBC 版本管理**
  - 自动下载和安装不同版本的 GLIBC
  - 支持 libc6、libc6-dbg 和 glibc-source 包
  - 管理多个 GLIBC 版本，便于切换和测试
  - 支持查看已安装版本的详细信息

- **ELF 文件补丁**
  - 自动修复 ELF 文件的依赖关系
  - 支持自定义补丁规则
  - 智能处理文件路径和版本兼容性

- **配置管理**
  - 灵活的配置系统
  - 支持自定义设置和偏好
  - 便捷的命令行配置接口

- **脚本功能**
  - 支持自动化操作脚本
  - 提供丰富的脚本接口
  - 简化重复性工作

## 系统要求

- Python >= 3.7
- Linux 操作系统
- 依赖包：
  - click >= 8.0.0
  - rich >= 10.0.0

## 安装
```bash
pip install epwn
```

## 详细使用说明

### 1. 配置管理 (config)

配置管理命令用于管理 EPwn 的各项设置，包括路径配置、下载设置和 OpenAI API 配置等。

#### 初始化配置

```bash
epwn config setup
```

这个命令会引导你完成基本配置，包括：
- 数据目录设置
- 下载目录设置
- OpenAI API 配置
- 其他基本设置

#### 查看当前配置

```bash
epwn config show
```

显示所有当前配置项，包括：
- 路径配置
- 数据库设置
- 下载配置
- OpenAI 设置

#### 修改配置

```bash
# 设置路径
epwn config set paths data_dir ~/.epwn/data
epwn config set paths download_dir ~/.epwn/downloads

# 设置下载参数
epwn config set download max_workers 10
epwn config set download timeout 30

# 设置 OpenAI
epwn config set openai api_key your-api-key
epwn config set openai model gpt-4
```

#### 重置和删除配置

```bash
# 重置为默认配置
epwn config reset

# 删除所有配置
epwn config delete
```

### 2. GLIBC 版本管理 (glibc)

GLIBC 版本管理是 EPwn 的核心功能之一，用于管理不同版本的 GLIBC。

#### 查看已安装版本

```bash
epwn glibc show
```

显示所有已安装的 GLIBC 版本，包括：
- 版本号
- libc 路径
- 调试符号路径
- 源码路径
- 安装时间

#### 查看特定版本详情

```bash
epwn glibc info 2.27
```

#### 安装 GLIBC

```bash
# 安装特定版本
epwn glibc install --version 2.27

# 安装带调试符号
epwn glibc install --version 2.27 -p libc6 -p libc6-dbg

# 安装源码
epwn glibc install --version 2.27 -p glibc-source

# 强制重新安装
epwn glibc install --version 2.27 --force

# 安装多个版本
epwn glibc install --nums 3  # 每个主版本保留3个最新子版本
```

#### 清理 GLIBC

```bash
# 清理所有版本
epwn glibc clean

# 强制清理
epwn glibc clean --force
```

### 3. ELF 补丁功能 (patch)

ELF 补丁功能用于修复 ELF 文件的 GLIBC 依赖问题。

#### 手动选择版本

```bash
# 创建备份并打补丁
epwn patch choose your_binary

# 不创建备份
epwn patch choose your_binary --no-backup
```

#### 自动修复

```bash
# 根据提供的 libc 文件自动修复
epwn patch auto your_binary path/to/libc.so.6

# 同时下载调试符号
epwn patch auto your_binary path/to/libc.so.6 -p libc6 -p libc6-dbg
```

### 4. PWN 脚本生成 (script)

PWN 脚本生成功能帮助自动化生成漏洞利用脚本。

#### 自动生成脚本

```bash
# 基本用法
epwn script auto ./vuln exploit.py

# 使用模板
epwn script auto ./vuln exploit.py -t template.py

# 提供额外提示
epwn script auto ./vuln exploit.py -p "注意处理整数溢出"
```

#### 交互式记录

```bash
# 记录交互并生成脚本
epwn script record ./vuln exploit.py

# 使用模板记录
epwn script record ./vuln exploit.py -t template.py
```

## 最佳实践

### GLIBC 管理最佳实践

1. 建议为每个主要版本保留多个子版本
2. 重要的 CTF 环境建议同时安装调试符号
3. 需要深入分析时可以安装源码包

### ELF 补丁最佳实践

1. 始终使用 --backup 选项创建备份
2. 优先使用 auto 模式，让工具自动选择合适的版本
3. 对于特殊情况可以使用 choose 模式手动选择

### 脚本生成最佳实践

1. 使用模板来保持脚本风格统一
2. 通过 prompt 提供额外的漏洞信息
3. 对于复杂程序，建议使用 record 模式手动探索

## 常见问题

1. 配置文件位置
   - 默认位置：`~/.local/share/epwn/`
   - 可通过 `config set` 修改

2. GLIBC 版本兼容性
   - 向下兼容：高版本 GLIBC 通常可以运行低版本编译的程序
   - 不向上兼容：低版本 GLIBC 可能无法运行高版本编译的程序

3. 补丁失败处理
   - 检查 GLIBC 版本是否正确
   - 确认 ELF 文件架构是否匹配
   - 使用备份文件恢复

## 贡献指南

欢迎提交 Pull Request 和 Issue！在提交之前，请确保：

1. 代码符合 PEP 8 规范
2. 添加了必要的测试用例
3. 更新了相关文档

## 问题反馈

如果你在使用过程中遇到任何问题，可以通过以下方式反馈：

- GitHub Issues: https://github.com/GeekCmore/epwn/issues
- 项目主页: https://github.com/GeekCmore/epwn

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 致谢

感谢所有为本项目做出贡献的开发者！

## 开发状态

当前版本：0.1.0 (Beta)

本项目仍在积极开发中，欢迎提供反馈和建议。
