"""
配置管理命令组
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from pathlib import Path
import sys
import os
import json

from epwn.core.config import config as config_instance

console = Console()

def display_config():
    """显示当前配置的辅助函数"""
    if not config_instance.config_file.exists():
        console.print("[yellow]No configuration found. Please run 'epwn config setup' first.[/yellow]")
        return
        
    try:
        config_instance.ensure_initialized()
    except Exception as e:
        console.print(f"[yellow]Failed to load configuration: {e}[/yellow]")
        console.print("[yellow]Please run 'epwn config setup' first.[/yellow]")
        return
    
    table = Table(title="Current Configuration")
    table.add_column("Section", style="cyan")
    table.add_column("Key", style="green")
    table.add_column("Value", style="yellow")
    
    try:
        # 显示路径配置
        for key in ["data_dir", "extract_dir"]:
            value = config_instance.get_path(key, ensure_init=False)
            table.add_row("paths", key, str(value))
            
        # 显示数据库配置
        value = config_instance.get_database("glibc_db", ensure_init=False)
        table.add_row("database", "glibc_db", str(value))
            
        # 显示下载配置
        download_keys = ["download_dir", "max_workers", "chunk_size", "max_retries", "timeout", "proxies"]
        for key in download_keys:
            value = config_instance.get_download(key, ensure_init=False)
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            table.add_row("download", key, value_str)
            
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error displaying configuration: {e}[/red]")
        raise

@click.group()
def config_cli():
    """配置管理命令组"""
    pass

@config_cli.command()
def setup():
    """初始化配置"""
    console.print("\n[cyan]欢迎使用epwn！让我们进行基本配置。[/cyan]\n")

    # 获取XDG基础目录
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.join(str(Path.home()), ".local", "share"))
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME", os.path.join(str(Path.home()), ".cache"))

    if Confirm.ask("是否要使用默认配置路径？", default=True):
        paths_config = {
            "base_dir": os.path.join(xdg_data_home, "epwn"),
            "data_dir": os.path.join(xdg_data_home, "epwn", "data"),
            "download_dir": os.path.join(xdg_cache_home, "epwn", "downloads"),
            "extract_dir": os.path.join(xdg_cache_home, "epwn", "extract"),
            "cache_dir": os.path.join(xdg_cache_home, "epwn"),
            "glibc_db": os.path.join(xdg_data_home, "epwn", "data", "glibc.db")
        }
        
        console.print("\n[green]将使用以下默认路径：[/green]")
        for key, value in paths_config.items():
            console.print(f"{key}: {value}")
    else:
        console.print("\n[yellow]请输入自定义路径：[/yellow]")
        paths_config = {
            "base_dir": Prompt.ask("基础目录", default=os.path.join(xdg_data_home, "epwn")),
            "data_dir": Prompt.ask("数据目录", default=os.path.join(xdg_data_home, "epwn", "data")),
            "download_dir": Prompt.ask("下载目录", default=os.path.join(xdg_cache_home, "epwn", "downloads")),
            "extract_dir": Prompt.ask("解压目录", default=os.path.join(xdg_cache_home, "epwn", "extract")),
            "cache_dir": Prompt.ask("缓存目录", default=os.path.join(xdg_cache_home, "epwn")),
            "glibc_db": Prompt.ask("数据库文件", default=os.path.join(xdg_data_home, "epwn", "data", "glibc.db"))
        }

    try:
        # 应用配置
        config_instance.apply_user_config(paths_config)
        console.print("\n[green]配置完成！所有必要的目录已创建。[/green]")
        
        # 显示当前配置
        console.print("\n当前配置：")
        display_config()
    except Exception as e:
        console.print(f"\n[red]配置失败：{str(e)}[/red]")
        sys.exit(1)

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

@config_cli.command()
def delete():
    """删除所有配置"""
    try:
        # 显示警告
        console.print("[red]WARNING: This will delete all configuration files and directories![/red]")
        console.print("[red]The following will be deleted:[/red]")
        
        # 显示当前配置
        display_config()
        
        # 确认删除
        if not Confirm.ask("[red]Are you sure you want to delete all configuration?[/red]"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return
            
        # 执行删除
        config_instance.delete_config()
        console.print("[green]All configuration files and directories have been deleted.[/green]")
        console.print("[yellow]Run 'epwn config setup' to create a new configuration.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)