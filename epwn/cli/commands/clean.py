"""
全局清理命令
"""
import click
from rich.console import Console
from rich.table import Table
import sys
import os
import shutil
from pathlib import Path

from epwn.core.config import config
from epwn.core.version import GlibcVersionManager

console = Console()

@click.command()
@click.option('--force', is_flag=True, help='跳过确认直接删除')
@click.option('--keep-config', is_flag=True, help='保留配置文件')
def clean(force: bool, keep_config: bool):
    """删除所有epwn相关的文件和目录"""
    try:
        # 收集所有需要删除的路径
        paths_to_delete = []
        
        # 添加基础目录
        base_dir = config.get_path("base_dir")
        if os.path.exists(base_dir):
            paths_to_delete.append(("Base Directory", base_dir))
            
        # 添加数据目录
        data_dir = config.get_path("data_dir")
        if os.path.exists(data_dir):
            paths_to_delete.append(("Data Directory", data_dir))
            
        # 添加下载目录
        download_dir = config.get_path("download_dir")
        if os.path.exists(download_dir):
            paths_to_delete.append(("Download Directory", download_dir))
            
        # 添加解压目录
        extract_dir = config.get_path("extract_dir")
        if os.path.exists(extract_dir):
            paths_to_delete.append(("Extract Directory", extract_dir))
            
        # 添加缓存目录
        cache_dir = config.get_path("cache_dir")
        if os.path.exists(cache_dir):
            paths_to_delete.append(("Cache Directory", cache_dir))
            
        # 添加配置文件
        if not keep_config:
            config_dir = Path(config.config_file).parent
            if os.path.exists(config_dir):
                paths_to_delete.append(("Config Directory", str(config_dir)))
        
        if not paths_to_delete:
            console.print("[yellow]No epwn files found to delete.")
            return
            
        # 显示将要删除的路径
        table = Table(show_header=True)
        table.add_column("Type", style="cyan")
        table.add_column("Path", style="green")
        
        for path_type, path in paths_to_delete:
            table.add_row(path_type, path)
            
        console.print("\nFiles and directories to be deleted:")
        console.print(table)
        
        # 确认删除
        if not force:
            confirm = input("\nAre you sure you want to delete all epwn files? [y/N] ")
            if confirm.lower() != 'y':
                console.print("[yellow]Operation cancelled.")
                return
        
        deleted_count = 0
        
        # 删除文件和目录
        for path_type, path in paths_to_delete:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    deleted_count += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    deleted_count += 1
                console.print(f"[green]Deleted {path_type}: {path}")
            except Exception as e:
                console.print(f"[red]Failed to delete {path}: {e}")
        
        # 显示删除结果
        result_table = Table(show_header=True)
        result_table.add_column("Status", style="cyan")
        result_table.add_column("Count", style="green")
        
        result_table.add_row(
            "Items deleted",
            str(deleted_count)
        )
        
        console.print("\nCleanup Summary:")
        console.print(result_table)
        
    except Exception as e:
        console.print(f"[red]Failed to clean epwn files: {str(e)}")
        sys.exit(1) 