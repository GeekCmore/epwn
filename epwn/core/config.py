from pathlib import Path
import yaml
import os
from typing import Any, Dict, Optional, List, Union
import re
from rich.console import Console
from rich.prompt import Confirm, Prompt
from dataclasses import dataclass, field, asdict
from typing_extensions import Literal

console = Console()

@dataclass
class PathsConfig:
    """路径配置模型"""
    data_dir: str = "${XDG_DATA_HOME}/epwn/data"
    extract_dir: str = "${XDG_DATA_HOME}/epwn/extract"

@dataclass
class DatabaseConfig:
    """数据库配置模型"""
    glibc_db: str = "${XDG_DATA_HOME}/epwn/data/glibc.db"

@dataclass
class DownloadConfig:
    """下载配置模型"""
    download_dir: str = "${XDG_CACHE_HOME}/epwn/downloads"
    max_workers: int = 5
    chunk_size: int = 8192
    max_retries: int = 3
    timeout: int = 30
    proxies: Optional[Dict[str, str]] = None

@dataclass
class ConfigModel:
    """配置模型"""
    paths: PathsConfig = field(default_factory=PathsConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "paths": asdict(self.paths),
            "database": asdict(self.database),
            "download": asdict(self.download)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigModel':
        """从字典创建配置模型"""
        paths = PathsConfig(**data.get("paths", {}))
        database = DatabaseConfig(**data.get("database", {}))
        download = DownloadConfig(**data.get("download", {}))
        return cls(paths=paths, database=database, download=download)

class PathManager:
    """路径管理器"""
    def __init__(self):
        self.xdg_dirs = self._get_xdg_dirs()

    def _get_xdg_dirs(self) -> Dict[str, str]:
        """获取XDG基础目录"""
        home = str(Path.home())
        return {
            "HOME": home,
            "XDG_CONFIG_HOME": os.environ.get("XDG_CONFIG_HOME", f"{home}/.config"),
            "XDG_DATA_HOME": os.environ.get("XDG_DATA_HOME", f"{home}/.local/share"),
            "XDG_CACHE_HOME": os.environ.get("XDG_CACHE_HOME", f"{home}/.cache")
        }

    def expand_path(self, path: str) -> str:
        """展开路径中的变量和特殊字符"""
        if not path:
            return path

        # 直接替换 ${HOME}
        home = self.xdg_dirs["HOME"]
        path = path.replace("${HOME}", home)
        
        # 处理其他环境变量
        for var_name, value in self.xdg_dirs.items():
            if var_name != "HOME":
                path = path.replace(f"${{{var_name}}}", value)
        
        return os.path.abspath(path)

    def validate_path(self, path: str) -> bool:
        """验证路径是否合法"""
        try:
            Path(path)
            return True
        except Exception:
            return False

    def normalize_path(self, path: str) -> str:
        """规范化路径格式"""
        if not path:
            return path
        path = path.replace("\\", "/")
        path = re.sub(r'/+', '/', path)
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path

class Config:
    """配置管理器"""
    def __init__(self):
        self.path_manager = PathManager()
        self.config_paths = self._get_config_paths()
        self.config_file = self._get_user_config_path()
        self.config = None
        self._initialized = False

    def ensure_initialized(self):
        """确保配置已初始化"""
        if not self._initialized:
            self._init_config()
            self._initialized = True

    def _init_config(self):
        """初始化配置"""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError("Config file not found")
                
            # 加载已有配置
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self.config = ConfigModel.from_dict(data)
        except Exception as e:
            console.print(f"[yellow]No configuration found. Please run 'epwn config setup' first.[/yellow]")
            raise

    def is_first_run(self) -> bool:
        """检查是否是首次运行"""
        return not self.config_file.exists()

    def get_path(self, key: str, default: Optional[str] = None, ensure_init: bool = True) -> str:
        """获取路径配置"""
        if ensure_init:
            self.ensure_initialized()
            
        if self.config is None:
            raise RuntimeError("Configuration not initialized. Please run 'epwn config setup' first.")
            
        value = getattr(self.config.paths, key, default)
        if value is None:
            return default
        expanded = self.path_manager.expand_path(value)
        if self.path_manager.validate_path(expanded):
            return self.path_manager.normalize_path(expanded)
        console.print(f"[yellow]Warning: Invalid path format: {value}[/yellow]")
        return value

    def get_database(self, key: str, default: Any = None, ensure_init: bool = True) -> Any:
        """获取数据库配置"""
        if ensure_init:
            self.ensure_initialized()
            
        if self.config is None:
            raise RuntimeError("Configuration not initialized. Please run 'epwn config setup' first.")
            
        value = getattr(self.config.database, key, default)
        if value is None:
            return default
            
        # 如果是路径类型的配置，进行路径展开
        if key == "glibc_db":
            expanded = self.path_manager.expand_path(value)
            if self.path_manager.validate_path(expanded):
                return self.path_manager.normalize_path(expanded)
            console.print(f"[yellow]Warning: Invalid path format: {value}[/yellow]")
            
        return value

    def get_download(self, key: str, default: Any = None, ensure_init: bool = True) -> Any:
        """获取下载配置"""
        if ensure_init:
            self.ensure_initialized()
            
        if self.config is None:
            raise RuntimeError("Configuration not initialized. Please run 'epwn config setup' first.")
            
        value = getattr(self.config.download, key, default)
        if value is None:
            return default
            
        # 如果是路径类型的配置，进行路径展开
        if key == "download_dir":
            expanded = self.path_manager.expand_path(value)
            if self.path_manager.validate_path(expanded):
                return self.path_manager.normalize_path(expanded)
            console.print(f"[yellow]Warning: Invalid path format: {value}[/yellow]")
            
        return value

    def apply_user_config(self, paths_config: Dict[str, str]) -> None:
        """应用用户配置"""
        self.config = ConfigModel()  # 创建新的默认配置
            
        # 设置路径配置
        for key, value in paths_config.items():
            if hasattr(self.config.paths, key):
                setattr(self.config.paths, key, value)
            elif hasattr(self.config.database, key):
                setattr(self.config.database, key, value)
            elif key == "download_dir":  # 特殊处理download_dir
                setattr(self.config.download, key, value)
                
        # 保存配置并确保目录存在
        self.save_config(self.config)
        self._initialized = True

    def _save_config_file(self, config: ConfigModel) -> None:
        """保存配置文件"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            console.print(f"[red]Error: Failed to save config file: {e}[/red]")

    def save_config(self, config: ConfigModel) -> None:
        """保存配置"""
        self._save_config_file(config)
        self._ensure_directories(config)
        self.config = config

    def _ensure_directories(self, config: ConfigModel) -> None:
        """确保所有必要的目录都存在"""
        paths = [
            config.paths.data_dir,
            config.paths.extract_dir,
            config.download.download_dir
        ]

        for path in paths:
            try:
                expanded_path = self.path_manager.expand_path(path)
                if not self.path_manager.validate_path(expanded_path):
                    console.print(f"[yellow]Warning: Invalid path format: {path}[/yellow]")
                    continue

                normalized_path = self.path_manager.normalize_path(expanded_path)
                os.makedirs(normalized_path, exist_ok=True)

                if not os.access(normalized_path, os.W_OK):
                    console.print(f"[yellow]Warning: No write permission: {normalized_path}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to create directory {path}: {e}[/yellow]")

        # 确保数据库目录存在
        db_path = self.get_database("glibc_db")
        if db_path:
            db_dir = os.path.dirname(self.path_manager.expand_path(db_path))
            os.makedirs(db_dir, exist_ok=True)

    def _get_config_paths(self) -> List[Path]:
        """获取配置文件搜索路径"""
        return [
            Path("/etc/epwn/epwn.yaml"),
            Path(self.path_manager.xdg_dirs["XDG_CONFIG_HOME"]) / "epwn" / "epwn.yaml",
            Path(__file__).parent.parent.parent / "epwn.yaml"
        ]

    def _get_user_config_path(self) -> Path:
        """获取用户配置文件路径"""
        config_dir = Path(self.path_manager.xdg_dirs["XDG_CONFIG_HOME"]) / "epwn"
        os.makedirs(config_dir, exist_ok=True)
        return config_dir / "config.yaml"

    def set_path(self, key: str, value: str) -> None:
        """设置路径配置"""
        if hasattr(self.config.paths, key):
            setattr(self.config.paths, key, value)
            self.save_config(self.config)

    def set_database(self, key: str, value: Any) -> None:
        """设置数据库配置"""
        if hasattr(self.config.database, key):
            setattr(self.config.database, key, value)
            self.save_config(self.config)

    def set_download(self, key: str, value: Any) -> None:
        """设置下载配置"""
        if hasattr(self.config.download, key):
            setattr(self.config.download, key, value)
            self.save_config(self.config)

    def delete_all(self) -> None:
        """删除所有配置和相关目录"""
        try:
            # 获取所有可能存在的目录
            paths = []
            if self.config is not None:
                # 添加路径配置的目录
                for key in ["data_dir", "extract_dir"]:
                    try:
                        path = self.get_path(key, ensure_init=False)
                        if path:
                            paths.append(path)
                    except:
                        pass
                
                # 添加下载目录
                try:
                    path = self.get_download("download_dir", ensure_init=False)
                    if path:
                        paths.append(path)
                except:
                    pass
                    
                # 添加数据库目录
                try:
                    path = self.get_database("glibc_db", ensure_init=False)
                    if path:
                        db_dir = os.path.dirname(path)
                        paths.append(db_dir)
                except:
                    pass
            
            # 添加基础目录
            base_paths = [
                os.path.join(self.path_manager.xdg_dirs["XDG_DATA_HOME"], "epwn"),
                os.path.join(self.path_manager.xdg_dirs["XDG_CACHE_HOME"], "epwn"),
                os.path.dirname(str(self.config_file))
            ]
            paths.extend(base_paths)
            
            # 删除所有目录
            for path in paths:
                if os.path.exists(path):
                    if os.path.isfile(path):
                        os.remove(path)
                    else:
                        import shutil
                        shutil.rmtree(path)
                        
            # 重置配置
            self.config = None
            self._initialized = False
            
        except Exception as e:
            console.print(f"[red]Error deleting configuration: {e}[/red]")
            raise

# 全局配置实例
config = Config() 