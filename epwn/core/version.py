"""
GLIBC版本管理模块
"""
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.table import Table
from epwn.core.config import config

class GlibcVersionManager:
    """GLIBC版本管理器"""
    def __init__(self):
        self.console = Console()
        self._conn = None
        self.db_path = None
        
        # 从配置获取数据库路径
        try:
            config.ensure_initialized()
            self.db_path = config.get_database("glibc_db")
            
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            # 初始化数据库连接
            self._init_db()
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Failed to load database configuration: {e}[/yellow]")
            self.console.print("[yellow]Using default values[/yellow]")
            
            # 使用默认值
            self.db_path = os.path.join(os.path.expanduser("~"), ".local", "share", "epwn", "data", "glibc.db")
            
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            # 初始化数据库连接
            self._init_db()

    def _init_db(self):
        """初始化数据库"""
        try:
            if self._conn is not None:
                return
                
            if self.db_path is None:
                raise RuntimeError("Database path is not set")
                
            # 连接数据库
            self._conn = sqlite3.connect(self.db_path)
            
            # 创建表
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS glibc_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL UNIQUE,
                    libc_path TEXT NOT NULL,
                    debug_path TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self._conn.commit()
            
        except Exception as e:
            self.console.print(f"[red]Error initializing database: {e}[/red]")
            if self._conn is not None:
                self._conn.close()
                self._conn = None
            raise

    def _ensure_connection(self):
        """确保数据库连接可用"""
        if self._conn is None:
            self._init_db()
        return self._conn

    def close(self):
        """关闭数据库连接"""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as e:
                self.console.print(f"[yellow]Warning: Error closing database connection: {e}[/yellow]")
            finally:
                self._conn = None

    def get_glibc_version(self, libc_path: str) -> str:
        """
        获取libc文件的GLIBC版本
        
        Args:
            libc_path: libc文件路径
            
        Returns:
            str: GLIBC版本号，例如 2.39-0ubuntu8.3
            
        Raises:
            RuntimeError: 无法获取版本号时抛出
        """
        try:
            # 使用strings命令获取所有字符串
            result = subprocess.run(
                ["strings", libc_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # 查找包含"GNU C Library (Ubuntu GLIBC"的行
            for line in result.stdout.splitlines():
                if "GNU C Library (Ubuntu GLIBC" in line:
                    # 提取版本号，格式如: GNU C Library (Ubuntu GLIBC 2.39-0ubuntu8.3)
                    match = re.search(r'GNU C Library \(Ubuntu GLIBC (2\.\d{2}-\d+ubuntu\d+(?:\.\d+)?)\)', line)
                    if match:
                        return match.group(1)
                        
            raise ValueError("No Ubuntu GLIBC version found")
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to read strings from file: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to get GLIBC version: {e}")

    def add_version(self, version: str, libc_path: str, debug_path: Optional[str] = None, source_path: Optional[str] = None) -> None:
        """
        添加GLIBC版本记录
        
        Args:
            version: GLIBC版本号
            libc_path: libc目录路径
            debug_path: 调试符号路径，可选
            source_path: 源码路径，可选
        """
        try:
            # 验证libc路径
            if not os.path.exists(libc_path):
                raise ValueError(f"Libc path does not exist: {libc_path}")
                
            # 验证调试符号路径
            if debug_path and not os.path.exists(debug_path):
                raise ValueError(f"Debug path does not exist: {debug_path}")
                
            # 验证源码路径
            if source_path and not os.path.exists(source_path):
                raise ValueError(f"Source path does not exist: {source_path}")
            
            conn = self._ensure_connection()
            conn.execute(
                "INSERT OR REPLACE INTO glibc_versions (version, libc_path, debug_path, source_path) VALUES (?, ?, ?, ?)",
                (version, libc_path, debug_path or "", source_path or "")
            )
            conn.commit()
        except Exception as e:
            self.console.print(f"[red]Error adding version: {e}[/red]")
            raise

    def remove_version(self, version: str) -> None:
        """
        删除GLIBC版本记录
        
        Args:
            version: GLIBC版本号
        """
        try:
            conn = self._ensure_connection()
            conn.execute(
                "DELETE FROM glibc_versions WHERE version = ?",
                (version,)
            )
            conn.commit()
        except Exception as e:
            self.console.print(f"[red]Error removing version: {e}[/red]")
            raise

    def get_versions(self) -> List[Dict[str, str]]:
        """
        获取所有GLIBC版本记录
        
        Returns:
            List[Dict[str, str]]: 版本记录列表
        """
        try:
            conn = self._ensure_connection()
            cursor = conn.execute(
                "SELECT version, libc_path, debug_path, source_path FROM glibc_versions ORDER BY version"
            )
            return [
                {
                    "version": row[0],
                    "libc_path": row[1],
                    "debug_path": row[2],
                    "source_path": row[3]
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            self.console.print(f"[red]Error getting versions: {e}[/red]")
            raise

    def get_version_info(self, version: str) -> Optional[Dict[str, str]]:
        """
        获取指定版本的记录
        
        Args:
            version: GLIBC版本号
            
        Returns:
            Optional[Dict[str, str]]: 版本记录，如果不存在则返回None
        """
        try:
            conn = self._ensure_connection()
            cursor = conn.execute(
                "SELECT version, libc_path, debug_path, source_path FROM glibc_versions WHERE version = ?",
                (version,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "version": row[0],
                    "libc_path": row[1],
                    "debug_path": row[2],
                    "source_path": row[3]
                }
            return None
        except Exception as e:
            self.console.print(f"[red]Error getting version info: {e}[/red]")
            raise

    def version_exists(self, version: str) -> bool:
        """
        检查版本是否存在
        
        Args:
            version: GLIBC版本号
            
        Returns:
            bool: 是否存在
        """
        try:
            conn = self._ensure_connection()
            cursor = conn.execute(
                "SELECT COUNT(*) FROM glibc_versions WHERE version = ?",
                (version,)
            )
            return cursor.fetchone()[0] > 0
        except Exception as e:
            self.console.print(f"[red]Error checking version existence: {e}[/red]")
            raise

    def print_versions(self):
        """打印所有可用的GLIBC版本信息"""
        try:
            versions = self.get_versions()
            
            if not versions:
                self.console.print("[yellow]No GLIBC versions available")
                return
                
            table = Table(title="Available GLIBC Versions")
            table.add_column("Version", style="cyan")
            table.add_column("Libc Path", style="green")
            table.add_column("Debug Path", style="blue")
            table.add_column("Source Path", style="magenta")
            
            for version in versions:
                table.add_row(
                    version["version"],
                    version["libc_path"],
                    version["debug_path"],
                    version["source_path"]
                )
                
            self.console.print(table)
            
        except Exception as e:
            self.console.print(f"[red]Error printing versions: {e}[/red]")
            raise 

    def list_versions(self) -> List[Dict[str, str]]:
        """
        获取所有GLIBC版本记录，包含完整信息
        
        Returns:
            List[Dict[str, str]]: 版本记录列表
        """
        try:
            conn = self._ensure_connection()
            cursor = conn.execute(
                "SELECT version, libc_path, debug_path, source_path, created_at FROM glibc_versions ORDER BY version"
            )
            return [
                {
                    "version": row[0],
                    "libc_path": row[1],
                    "debug_path": row[2],
                    "source_path": row[3],
                    "created_at": row[4]
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            self.console.print(f"[red]Error listing versions: {e}[/red]")
            raise

    def get_glibc_info(self, version: str) -> Optional[Dict[str, str]]:
        """
        获取指定版本的完整信息
        
        Args:
            version: GLIBC版本号
            
        Returns:
            Optional[Dict[str, str]]: 版本信息，如果不存在则返回None
        """
        try:
            conn = self._ensure_connection()
            cursor = conn.execute(
                "SELECT version, libc_path, debug_path, source_path, created_at FROM glibc_versions WHERE version = ?",
                (version,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "version": row[0],
                    "libc_path": row[1],
                    "debug_path": row[2],
                    "source_path": row[3],
                    "created_at": row[4]
                }
            return None
        except Exception as e:
            self.console.print(f"[red]Error getting GLIBC info: {e}[/red]")
            raise 