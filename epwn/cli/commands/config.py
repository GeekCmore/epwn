"""
配置管理命令组
"""
import click
from rich.console import Console
from rich.table import Table
import sys
from typing import Any
import json

from epwn.core.config import config as config_instance

console = Console()

def display_config():
    """显示当前配置的辅助函数"""
    table = Table(title="Current Configuration")
    table.add_column("Section", style="cyan")
    table.add_column("Key", style="green")
    table.add_column("Value", style="yellow")
    
    # 显示路径配置
    for key, value in config_instance.config.paths.__dict__.items():
        if not key.startswith("_"):
            table.add_row("paths", key, str(value))
            
    # 显示数据库配置
    for key, value in config_instance.config.database.__dict__.items():
        if not key.startswith("_"):
            table.add_row("database", key, str(value))
            
    # 显示下载配置
    for key, value in config_instance.config.download.__dict__.items():
        if not key.startswith("_"):
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            table.add_row("download", key, value_str)
            
    console.print(table)

@click.group()
def config_cli():
    """配置管理命令组"""
    pass

@config_cli.command()
def show():
    """显示当前配置"""
    try:
        display_config()
    except Exception as e:
        console.print(f"[red]Failed to show configuration: {str(e)}")
        sys.exit(1)

@config_cli.command()
@click.argument("section", type=click.Choice(["paths", "database", "download"]))
@click.argument("key")
@click.argument("value")
def set(section: str, key: str, value: str):
    """设置配置项

    参数说明:
    \b
    SECTION: 配置段落，可选值: paths, database, download
    KEY: 配置项名称
    VALUE: 要设置的值
    
    示例:
    \b
    # 路径配置
    epwn config set paths base_dir ~/.epwn
    epwn config set paths data_dir ~/.epwn/data
    epwn config set paths download_dir ~/.epwn/downloads
    epwn config set paths extract_dir ~/.epwn/extract
    epwn config set paths cache_dir ~/.epwn/cache
    
    # 数据库配置
    epwn config set database glibc_db ~/.epwn/data/glibc.db
    
    # 下载配置
    epwn config set download save_dir ~/downloads
    epwn config set download max_workers 10
    epwn config set download chunk_size 8192
    epwn config set download max_retries 3
    epwn config set download timeout 30
    epwn config set download proxies '{"http":"http://127.0.0.1:7890"}'
    """
    try:
        # 尝试解析值
        try:
            # 如果是JSON字符串，解析为Python对象
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            # 不是JSON，尝试转换为适当的类型
            if value.lower() == "true":
                parsed_value = True
            elif value.lower() == "false":
                parsed_value = False
            elif value.lower() == "none":
                parsed_value = None
            else:
                try:
                    # 尝试转换为数字
                    parsed_value = int(value)
                except ValueError:
                    try:
                        parsed_value = float(value)
                    except ValueError:
                        # 保持为字符串
                        parsed_value = value
                        
        # 根据配置段落设置值
        if section == "paths":
            config_instance.set_path(key, parsed_value)
        elif section == "database":
            config_instance.set_database(key, parsed_value)
        elif section == "download":
            config_instance.set_download(key, parsed_value)
            
        console.print(f"[green]Successfully set {section}.{key} = {parsed_value}")
        
    except Exception as e:
        console.print(f"[red]Failed to set configuration: {str(e)}")
        sys.exit(1)
        
@config_cli.command()
def reset():
    """重置为默认配置"""
    try:
        # 重置配置
        config_instance.reset()
        console.print("[green]Configuration has been reset to defaults")
        
        # 显示新的配置
        console.print("\nNew configuration:")
        display_config()
        
    except Exception as e:
        console.print(f"[red]Failed to reset configuration: {str(e)}")
        sys.exit(1) 