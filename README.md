# EPWN

EPWN是一个基于Python的PWN辅助工具，集成了自动化脚本生成、程序分析等功能。

## 特性

- 自动分析二进制程序并生成pwntools脚本
- 基于OpenAI API的智能分析
- 支持脚本模板和自定义提示
- 并行程序状态探索
- 交互式菜单分析
- 完整的CLI命令支持

## 安装

```bash
pip install epwn
```

## 配置

首次使用前需要配置OpenAI API相关参数：

```bash
epwn config set openai.api_key "your-api-key"
epwn config set openai.base_url "https://api.openai.com/v1"  # 可选，默认为OpenAI官方API
epwn config set openai.model "gpt-3.5-turbo"  # 可选，默认使用gpt-3.5-turbo
```

## 使用方法

### 自动生成PWN脚本

基本用法：
```bash
epwn script auto ./vuln exploit.py
```

使用模板：
```bash
epwn script auto ./vuln exploit.py -t template.py
```

提供额外提示：
```bash
epwn script auto ./vuln exploit.py -p "注意处理整数溢出"
```

### 分析程序菜单

```bash
# 将程序菜单输出保存到文件
./vuln > menu.txt
# 分析菜单
epwn script analyze-menu menu.txt
```

### 手动记录交互

添加成功的交互：
```bash
epwn script add-interaction "1" "Menu option 1 selected"
```

添加失败的交互：
```bash
epwn script add-interaction "invalid" "Error: Invalid input" --failure --error "Invalid menu option"
```

### 获取下一步建议

```bash
epwn script next-action
```

### 从记录生成脚本

```bash
epwn script generate vuln exploit.py
```

### 清除交互历史

```bash
epwn script clear
```

## 脚本模板

你可以创建自定义的脚本模板，在模板中使用 `# SCRIPT_CONTENT` 标记来指定生成内容的插入位置：

```python
from pwn import *

# 自定义设置
context.log_level = 'debug'
context.arch = 'amd64'

# SCRIPT_CONTENT

# 自定义辅助函数
def debug():
    gdb.attach(io)
    pause()
```

## 注意事项

1. 确保目标程序具有可执行权限
2. 建议在使用前备份重要文件
3. 生成的脚本可能需要根据具体情况进行调整

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License
