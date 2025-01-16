#!/usr/bin/env python3
import click
from rich.console import Console

# 导入命令模块
from .commands.glibc import glibc
from .commands.patch import patch
from .commands.config import config_cli
from .commands.script import script

console = Console()

@click.group()
def cli():
    """GLIBC版本管理和ELF补丁工具"""
    pass

# 注册命令组
cli.add_command(glibc)
cli.add_command(patch)
cli.add_command(config_cli, name="config")
cli.add_command(script)

# 为了兼容性添加别名
main = cli

if __name__ == '__main__':
    cli()