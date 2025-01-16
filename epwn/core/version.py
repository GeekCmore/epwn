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

class GlibcVersionManager:
    """GLIBC版本管理器"""
    def __init__(self, db_path: str = ".glibc.db"):
        """
        初始化GLIBC版本管理器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.console = Console()
        self._conn = None
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        # 如果已经有连接，直接使用
        if self._conn is not None:
            return
            
        self._conn = sqlite3.connect(self.db_path)
        
        # 检查表是否存在
        cursor = self._conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='glibc_versions'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # 如果表不存在，创建新表
            self._conn.execute("""
                CREATE TABLE glibc_versions (
                    version TEXT PRIMARY KEY,
                    libc_path TEXT NOT NULL,
                    interpreter_path TEXT,
                    debug_path TEXT,
                    source_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # 如果表存在，检查是否需要添加新列
            cursor = self._conn.execute("PRAGMA table_info(glibc_versions)")
            columns = {row[1] for row in cursor.fetchall()}
            
            # 添加缺失的列
            if "debug_path" not in columns:
                self._conn.execute("ALTER TABLE glibc_versions ADD COLUMN debug_path TEXT")
            if "source_path" not in columns:
                self._conn.execute("ALTER TABLE glibc_versions ADD COLUMN source_path TEXT")
                
        self._conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        if self._conn is not None:
            self._conn.close()
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
    
    def _validate_version(self, version: str) -> bool:
        """
        验证GLIBC版本号格式是否正确
        
        Args:
            version: 版本号字符串
            
        Returns:
            bool: 版本号格式是否正确
        """
        # 匹配格式: 2.XX-YubuntuZ[.W]
        pattern = r"^2\.\d{2}-\d+ubuntu\d+(\.\d+)?$"
        return bool(re.match(pattern, version))
    
    def _parse_version(self, version: str) -> Tuple[int, int, int, int]:
        """
        解析GLIBC版本号
        
        Args:
            version: 版本号字符串 (例如: 2.31-0ubuntu9.5)
            
        Returns:
            Tuple[int, int, int, int]: (主版本号, 次版本号, ubuntu主版本号, ubuntu次版本号)
        """
        if not self._validate_version(version):
            raise ValueError(f"Invalid GLIBC version format: {version}")
        
        # 分解版本号
        main_ver, ubuntu_ver = version.split("-", 1)
        major, minor = map(int, main_ver.split("."))
        
        # 处理ubuntu版本号
        ubuntu_parts = ubuntu_ver.split("ubuntu")
        ubuntu_major = int(ubuntu_parts[0])
        
        # 处理可能的次版本号
        ubuntu_minor_parts = ubuntu_parts[1].split(".")
        ubuntu_minor = int(ubuntu_minor_parts[0])
        ubuntu_patch = int(ubuntu_minor_parts[1]) if len(ubuntu_minor_parts) > 1 else 0
        
        return (major, minor, ubuntu_minor, ubuntu_patch)
    
    def add_glibc(self, version: str, libc_path: str, debug_path: Optional[str] = None, source_path: Optional[str] = None) -> Tuple[str, str]:
        """
        添加新的glibc文件
        
        Args:
            version: GLIBC版本号
            libc_path: libc文件路径
            debug_path: 调试符号文件路径
            source_path: 源码路径
            
        Returns:
            Tuple[str, str, str]: (版本号, 解释器路径, 调试符号路径)
            
        Raises:
            RuntimeError: 添加失败时抛出
            ValueError: 版本号格式无效时抛出
        """
        try:
            libc_path = os.path.abspath(libc_path)
            if not os.path.exists(libc_path):
                raise FileNotFoundError(f"File not found: {libc_path}")
            
            # 获取GLIBC版本
            version = self.get_glibc_version(libc_path)
            # 验证版本号格式
            if not self._validate_version(version):
                raise ValueError(f"Invalid GLIBC version format: {version}")
            
            # 查找对应的解释器
            lib_dir = Path(libc_path).parent
            interpreter_path = None
            for path in lib_dir.rglob("ld-linux-x86-64.so.*"):
                interpreter_path = str(path)
                break
            
            if not interpreter_path:
                raise RuntimeError(f"Could not find matching interpreter for GLIBC {version}")
            
            # 保存到数据库
            self._conn.execute("""
                INSERT OR REPLACE INTO glibc_versions 
                (version, libc_path, interpreter_path, debug_path, source_path, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (version, libc_path, interpreter_path, debug_path, source_path))
            self._conn.commit()
            
            self.console.print(f"[green]Added GLIBC {version} from {libc_path}")
            return version, interpreter_path
            
        except FileNotFoundError:
            raise  # 直接重新抛出FileNotFoundError
        except Exception as e:
            raise RuntimeError(f"Failed to add glibc: {e}")
    
    def find_glibc(self, version: str) -> Optional[Dict[str, str]]:
        """
        查找指定版本的GLIBC文件
        
        Args:
            version: GLIBC版本号
            
        Returns:
            Dict[str, str]: 包含libc、interpreter、debug和source路径的字典，未找到则返回None
        """
        cursor = self._conn.execute("""
            SELECT libc_path, interpreter_path, debug_path, source_path
            FROM glibc_versions 
            WHERE version = ?
        """, (version,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        libc_path, interpreter_path, debug_path, source_path = row
        
        # 验证文件是否仍然存在
        if not os.path.exists(libc_path) or not os.path.exists(interpreter_path):
            # 如果文件不存在，从数据库中删除
            self._conn.execute("DELETE FROM glibc_versions WHERE version = ?", (version,))
            self._conn.commit()
            return None
        
        result = {
            "libc": libc_path,
            "interpreter": interpreter_path
        }
        
        # 添加可选的调试符号和源码路径
        if debug_path and os.path.exists(debug_path):
            result["debug"] = debug_path
        if source_path and os.path.exists(source_path):
            result["source"] = source_path
            
        return result
    
    def list_versions(self) -> List[Dict[str, str]]:
        """
        列出所有可用的GLIBC版本
        
        Returns:
            List[Dict[str, str]]: 版本信息列表
        """
        cursor = self._conn.execute("""
            SELECT version, libc_path, interpreter_path, debug_path, source_path, created_at 
            FROM glibc_versions 
            ORDER BY version
        """)
        
        versions = []
        for row in cursor.fetchall():
            version, libc_path, interpreter_path, debug_path, source_path, created_at = row
            if os.path.exists(libc_path) and os.path.exists(interpreter_path):
                version_info = {
                    "version": version,
                    "libc_path": libc_path,
                    "interpreter_path": interpreter_path,
                    "created_at": created_at
                }
                
                # 添加可选的调试符号和源码路径
                if debug_path and os.path.exists(debug_path):
                    version_info["debug_path"] = debug_path
                if source_path and os.path.exists(source_path):
                    version_info["source_path"] = source_path
                    
                versions.append(version_info)
        
        return versions
    
    def remove_version(self, version: str) -> bool:
        """
        从数据库中删除指定版本
        
        Args:
            version: GLIBC版本号
            
        Returns:
            bool: 是否成功删除
        """
        cursor = self._conn.execute(
            "DELETE FROM glibc_versions WHERE version = ?",
            (version,)
        )
        self._conn.commit()
        return cursor.rowcount > 0
    
    def print_versions(self):
        """打印所有可用的GLIBC版本信息"""
        versions = self.list_versions()
        
        if not versions:
            self.console.print("[yellow]No GLIBC versions available")
            return
        
        table = Table(title="Available GLIBC Versions")
        table.add_column("Version", style="cyan")
        table.add_column("Libc Path", style="green")
        table.add_column("Interpreter Path", style="blue")
        table.add_column("Added At", style="magenta")
        
        for v in versions:
            table.add_row(
                v["version"],
                v["libc_path"],
                v["interpreter_path"],
                v["created_at"]
            )
        
        self.console.print(table) 