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
    base_dir: str = "${HOME}/.epwn"
    data_dir: str = "${HOME}/.epwn/data"
    download_dir: str = "${HOME}/.epwn/downloads"
    extract_dir: str = "${HOME}/.epwn/extract"
    cache_dir: str = "${HOME}/.epwn/cache"

@dataclass
class DatabaseConfig:
    """数据库配置模型"""
    glibc_db: str = "${HOME}/.epwn/data/glibc.db"

@dataclass
class DownloadConfig:
    """下载配置模型"""
    save_dir: str = "${HOME}/.epwn/downloads"
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

        # 展开 ${VAR} 变量
        def replace_var(match):
            var_name = match.group(1)
            # 优先使用 xdg_dirs 中的值
            if var_name in self.xdg_dirs:
                return self.xdg_dirs[var_name]
            # 然后尝试环境变量
            return os.environ.get(var_name, match.group(0))

        # 先处理 ${HOME} 和其他变量
        path = re.sub(r'\${(\w+)}', replace_var, path)
        # 然后处理 ~ 展开
        path = os.path.expanduser(path)
        # 最后处理其他环境变量
        path = os.path.expandvars(path)
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
        self.config = self._load_config()

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

    def _load_config(self) -> ConfigModel:
        """加载配置"""
        if not self.config_file.exists():
            return self._create_default_config()

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return ConfigModel.from_dict(data)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load config file: {e}[/yellow]")
            return self._create_default_config()

    def _create_default_config(self) -> ConfigModel:
        """创建默认配置"""
        config = ConfigModel()
        self.save_config(config)
        return config

    def save_config(self, config: ConfigModel) -> None:
        """保存配置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
            self._ensure_directories(config)
        except Exception as e:
            console.print(f"[red]Error: Failed to save config file: {e}[/red]")

    def _ensure_directories(self, config: ConfigModel) -> None:
        """确保所有必要的目录都存在"""
        paths = [
            config.paths.base_dir,
            config.paths.data_dir,
            config.paths.download_dir,
            config.paths.extract_dir,
            config.paths.cache_dir
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

    def get_path(self, key: str, default: Optional[str] = None) -> str:
        """获取路径配置"""
        value = getattr(self.config.paths, key, default)
        if value is None:
            return default
        expanded = self.path_manager.expand_path(value)
        if self.path_manager.validate_path(expanded):
            return self.path_manager.normalize_path(expanded)
        console.print(f"[yellow]Warning: Invalid path format: {value}[/yellow]")
        return value

    def get_database(self, key: str, default: Any = None) -> Any:
        """获取数据库配置"""
        return getattr(self.config.database, key, default)

    def get_download(self, key: str, default: Any = None) -> Any:
        """获取下载配置"""
        return getattr(self.config.download, key, default)

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

    def reset(self) -> None:
        """重置为默认配置"""
        self.config = self._create_default_config()

# 全局配置实例
config = Config() 