from pathlib import Path
import yaml
import os
from typing import Any, Dict, Optional, List
import re
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()

class Config:
    """全局配置管理类"""
    
    def __init__(self):
        """初始化配置管理器"""
        # XDG目录
        self.xdg_dirs = self._get_xdg_dirs()
        
        # 配置文件搜索路径
        self.config_search_paths = [
            # 1. 系统级配置
            Path("/etc/epwn/epwn.yaml"),
            # 2. 用户级默认配置
            Path(self.xdg_dirs["XDG_CONFIG_HOME"]) / "epwn" / "epwn.yaml",
            # 3. 项目级配置(用于开发)
            Path(__file__).parent.parent.parent / "epwn.yaml"
        ]
        
        # 用户配置文件路径
        self.config_dir = Path(self.xdg_dirs["XDG_CONFIG_HOME"]) / "epwn"
        self.config_file = self.config_dir / "config.yaml"
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 检查是否需要运行首次配置向导
        if self._is_first_run():
            self._run_setup_wizard()
        
        # 加载配置
        self.config = self._load_config()
        
        # 确保所有必要的目录存在
        self._ensure_directories()
        
    def _get_xdg_dirs(self) -> Dict[str, str]:
        """
        获取XDG基础目录
        
        Returns:
            Dict[str, str]: XDG目录字典
        """
        home = str(Path.home())
        return {
            "HOME": home,
            "XDG_CONFIG_HOME": os.environ.get("XDG_CONFIG_HOME", f"{home}/.config"),
            "XDG_DATA_HOME": os.environ.get("XDG_DATA_HOME", f"{home}/.local/share"),
            "XDG_CACHE_HOME": os.environ.get("XDG_CACHE_HOME", f"{home}/.cache")
        }
        
    def _expand_path(self, path: str) -> str:
        """
        展开路径中的变量
        
        Args:
            path: 包含变量的路径字符串
            
        Returns:
            str: 展开后的路径
        """
        # 替换所有${VAR}形式的变量
        def replace_var(match):
            var_name = match.group(1)
            return self.xdg_dirs.get(var_name, match.group(0))
            
        return re.sub(r'\${(\w+)}', replace_var, path)
        
    def _ensure_directories(self) -> None:
        """确保所有必要的目录都存在"""
        paths = self.config.get("paths", {})
        for key, path in paths.items():
            if isinstance(path, str) and key.endswith("_dir"):
                expanded_path = self._expand_path(path)
                os.makedirs(expanded_path, exist_ok=True)
        
    def _find_default_config(self) -> Optional[Path]:
        """
        按优先级查找默认配置文件
        
        Returns:
            Optional[Path]: 找到的配置文件路径，如果都不存在则返回None
        """
        for path in self.config_search_paths:
            if path.exists():
                return path
        return None
        
    def _load_default_config(self) -> Dict[str, Any]:
        """
        加载默认配置
        
        Returns:
            Dict[str, Any]: 默认配置字典
        """
        # 查找默认配置文件
        default_config_file = self._find_default_config()
        
        if default_config_file:
            try:
                with open(default_config_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load default config file {default_config_file}: {e}")
            
        # 如果找不到配置文件或加载失败，返回基础配置
        return {
            "paths": {
                "base_dir": f"${{HOME}}/.epwn",
                "data_dir": f"${{HOME}}/.epwn/data",
                "download_dir": f"${{HOME}}/.epwn/downloads",
                "cache_dir": f"${{HOME}}/.epwn/cache"
            },
            "database": {
                "glibc_db": f"${{HOME}}/.epwn/data/glibc.db"
            },
            "download": {
                "save_dir": f"${{HOME}}/.epwn/downloads",
                "max_workers": 5,
                "chunk_size": 8192,
                "max_retries": 3,
                "timeout": 30,
                "proxies": None
            }
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """
        从文件加载配置，如果文件不存在则创建默认配置
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        if not self.config_file.exists():
            # 加载默认配置并创建用户配置文件
            default_config = self._load_default_config()
            self.save_config(default_config)
            return default_config
            
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                # 确保所有默认配置项都存在
                return self._merge_with_defaults(config or {})
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")
            return self._load_default_config()
            
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        将用户配置与默认配置合并，确保所有必要的配置项都存在
        
        Args:
            config: 用户配置字典
            
        Returns:
            Dict[str, Any]: 合并后的配置字典
        """
        default_config = self._load_default_config()
        result = default_config.copy()
        
        for section, values in config.items():
            if section in result and isinstance(values, dict):
                result[section].update(values)
            else:
                result[section] = values
                
        return result
        
    def save_config(self, config: Dict[str, Any]) -> None:
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置字典
        """
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
            self.config = config
            # 确保所有目录存在
            self._ensure_directories()
        except Exception as e:
            print(f"Error: Failed to save config file: {e}")
            
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            section: 配置分区名
            key: 配置项名称
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        value = self.config.get(section, {}).get(key, default)
        # 如果是路径，展开变量
        if isinstance(value, str) and ("${" in value):
            return self._expand_path(value)
        return value
        
    def set(self, section: str, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            section: 配置分区名
            key: 配置项名称
            value: 配置值
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config(self.config)
        
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            Dict[str, Any]: 完整的配置字典
        """
        return self.config.copy()
        
    def _is_first_run(self) -> bool:
        """
        检查是否是首次运行
        
        Returns:
            bool: 如果只有项目级配置存在则返回True
        """
        # 检查系统级和用户级配置是否存在
        system_config = self.config_search_paths[0]
        user_config = self.config_search_paths[1]
        project_config = self.config_search_paths[2]
        
        # 如果系统级或用户级配置已存在，不是首次运行
        if system_config.exists() or user_config.exists():
            return False
            
        # 如果项目级配置存在，且是唯一存在的配置，则是首次运行
        return project_config.exists()
        
    def _run_setup_wizard(self) -> None:
        """运行首次配置向导"""
        console.print("\n[bold cyan]欢迎使用EPWN![/bold cyan]")
        console.print("看起来这是你第一次运行EPWN。让我们一起完成配置设置。\n")
        
        # 询问配置文件位置
        console.print("[bold]配置文件位置[/bold]")
        console.print("EPWN的配置文件可以存储在以下位置:")
        console.print("1. 系统级 (/etc/epwn/epwn.yaml) - 所有用户共享")
        console.print("2. 用户级 (~/.config/epwn/epwn.yaml) - 仅当前用户\n")
        
        try:
            use_system = Confirm.ask("是否要安装系统级配置文件？")
        except Exception:
            # 如果在非交互环境下，默认使用用户级配置
            use_system = False
        
        source_config = self.config_search_paths[2]  # 项目级配置
        if use_system:
            target_config = self.config_search_paths[0]  # 系统级配置
            try:
                # 创建系统配置目录
                os.makedirs(target_config.parent, exist_ok=True)
                # 复制配置文件
                import shutil
                shutil.copy2(source_config, target_config)
                console.print(f"\n[green]已创建系统级配置文件: {target_config}[/green]")
            except PermissionError:
                console.print("\n[yellow]警告: 没有权限创建系统级配置文件。[/yellow]")
                console.print("[yellow]请使用sudo运行或选择用户级配置。[/yellow]")
                console.print("[yellow]将使用用户级配置作为备选...[/yellow]\n")
                use_system = False
                
        if not use_system:
            target_config = self.config_search_paths[1]  # 用户级配置
            # 创建用户配置目录
            os.makedirs(target_config.parent, exist_ok=True)
            # 复制配置文件
            import shutil
            shutil.copy2(source_config, target_config)
            console.print(f"\n[green]已创建用户级配置文件: {target_config}[/green]")
            
        # 创建数据目录
        base_dir = Path.home() / ".epwn"
        for dir_name in ["data", "downloads", "cache"]:
            os.makedirs(base_dir / dir_name, exist_ok=True)
            
        console.print("\n[green]配置完成！[/green]")
        console.print("你可以随时使用以下命令查看或修改配置：")
        console.print("  epwn config show  - 显示当前配置")
        console.print("  epwn config set   - 修改配置项")
        console.print("  epwn config reset - 重置为默认配置\n")

# 全局配置实例
config = Config() 