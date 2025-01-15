"""
ELF补丁命令组
"""
import click
from rich.console import Console
from rich.table import Table
from pathlib import Path
import shutil
import sys
from typing import Optional, List

from epwn.core.patcher import ElfPatcher
from epwn.core.version import GlibcVersionManager
from epwn.cli.commands.glibc import _install_glibc

console = Console()

@click.group()
def patch():
    """ELF补丁命令组"""
    pass

@patch.command()
@click.argument('elf_file')
@click.option('--backup/--no-backup', default=True, help='是否创建备份')
def choose(elf_file: str, backup: bool):
    """从已安装的GLIBC版本中选择一个打补丁"""
    try:
        # 获取已安装的版本列表
        version_manager = GlibcVersionManager()
        available_versions = version_manager.list_versions()
        
        if not available_versions:
            console.print("[red]No GLIBC versions available")
            return
            
        # 显示可用版本
        table = Table(show_header=True)
        table.add_column("Index", style="cyan")
        table.add_column("Version", style="cyan")
        
        for i, version in enumerate(available_versions):
            table.add_row(
                str(i+1),
                version["version"]
            )
            
        console.print("\nAvailable GLIBC versions:")
        console.print(table)
        
        # 让用户选择版本
        choice = click.prompt("Please select a version (enter index)", type=int)
        if choice < 1 or choice > len(available_versions):
            console.print("[red]Invalid selection")
            return
            
        selected_version = available_versions[choice-1]["version"]
        console.print(f"[green]Selected GLIBC version: {selected_version}")
        
        # 创建备份
        if backup:
            backup_file = f"{elf_file}.bak"
            shutil.copy2(elf_file, backup_file)
            console.print(f"[green]Created backup: {backup_file}")
            
        # 执行补丁
        patcher = ElfPatcher()
        result = patcher.patch(elf_file, selected_version)
        
        if result.success:
            console.print(f"[green]Successfully patched {elf_file} to use GLIBC {selected_version}")
        else:
            console.print(f"[red]Patch failed: {result.error}")
            if backup:
                shutil.move(backup_file, elf_file)
                console.print("[yellow]Restored from backup")
                
    except Exception as e:
        console.print(f"[red]Patch failed: {str(e)}")
        sys.exit(1)

@patch.command()
@click.argument('elf_file')
@click.argument('libc')
@click.option('--backup/--no-backup', default=True, help='是否创建备份')
@click.option('--packages', '-p', multiple=True, type=click.Choice(['libc6', 'libc6-dbg', 'glibc-source']), 
              default=['libc6'], help='需要下载的包，可指定多个')
def auto(elf_file: str, libc: str, backup: bool, packages: List[str]):
    """自动选择合适的GLIBC版本打补丁"""
    try:
        version_manager = GlibcVersionManager()
        available_versions = version_manager.list_versions()
        
        # 获取libc版本
        libc_version = version_manager.get_glibc_version(libc)
        if not libc_version:
            console.print("[red]Failed to get GLIBC version from provided libc file")
            return
            
        # 检查是否已有该版本
        target_version = None
        for version in available_versions:
            if version["version"] == libc_version:
                target_version = libc_version
                console.print(f"[green]Found matching GLIBC version: {libc_version}")
                break
                
        # 如果没有该版本，尝试下载
        if not target_version:
            console.print(f"[yellow]GLIBC version {libc_version} not found locally, trying to download...")
            # 获取ELF文件的架构
            patcher = ElfPatcher(elf_file)
            arch = patcher.get_arch()
            if not arch:
                console.print("[red]Failed to determine ELF architecture")
                return
            console.print(f"[cyan]Installing GLIBC {libc_version} for {arch}...")
            
            # 调用install函数
            _install_glibc(
                version=libc_version,  # 版本号
                arch=arch,            # 架构
                force=True,          # 强制安装
                nums=1,              # 保留版本数
                packages=packages    # 包列表
            )
            target_version = libc_version
        
        # 创建备份
        if backup:
            backup_file = f"{elf_file}.bak"
            shutil.copy2(elf_file, backup_file)
            console.print(f"[green]Created backup: {backup_file}")
        
        # 执行补丁
        patcher = ElfPatcher()
        result = patcher.patch(elf_file, target_version)
        
        if result.success:
            console.print(f"[green]Successfully patched {elf_file} to use GLIBC {target_version}")
        else:
            console.print(f"[red]Patch failed: {result.error}")
            if backup:
                shutil.move(backup_file, elf_file)
                console.print("[yellow]Restored from backup")
            
    except Exception as e:
        console.print(f"[red]Patch failed: {str(e)}")
        sys.exit(1)
