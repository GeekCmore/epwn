"""
ELF补丁模块
"""
import os
import re
import glob
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path
from rich.console import Console

from .version import GlibcVersionManager

@dataclass
class PatchResult:
    """补丁结果"""
    success: bool
    error: Optional[str] = None
    ldd_info: Optional[str] = None

class ElfPatcher:
    """ELF文件补丁工具"""
    def __init__(self, elf_path: Optional[str] = None):
        """
        初始化ELF补丁工具
        
        Args:
            elf_path: ELF文件路径
        """
        self._elf_path = elf_path
        self._version_manager = GlibcVersionManager()
        self.console = Console()
        
        if elf_path and not os.path.exists(elf_path):
            raise FileNotFoundError(f"File not found: {elf_path}")
    
    def patch(self, elf_path: str, version: str) -> PatchResult:
        """
        为ELF文件打补丁，使其使用指定版本的GLIBC
        
        Args:
            elf_path: ELF文件路径
            version: 目标GLIBC版本
            
        Returns:
            PatchResult: 补丁结果
        """
        try:
            # 查找指定版本的GLIBC
            glibc_info = self._version_manager.get_glibc_info(version)
            if not glibc_info:
                return PatchResult(False, f"GLIBC version {version} not found")
            
            # 设置ELF文件路径
            self._elf_path = elf_path
            
            # 获取架构
            arch = self.get_arch()
            
            # 查找链接器和libc路径
            interpreter_path, libc_path = self._find_glibc_files(glibc_info["libc_path"], arch)
            if not interpreter_path or not libc_path:
                return PatchResult(False, "Failed to find required GLIBC files")
            
            # 应用补丁
            self._patch_interpreter(interpreter_path)
            self._patch_rpath(str(Path(libc_path).parent))
            
            # 获取ldd信息
            ldd_info = self._get_ldd_info()
            
            # 打印ldd信息
            self.console.print("\n[cyan]Current library dependencies:[/cyan]")
            self.console.print(ldd_info)
            
            return PatchResult(True, ldd_info=ldd_info)
            
        except Exception as e:
            return PatchResult(False, str(e))
    
    def get_arch(self) -> str:
        """
        获取ELF文件的架构
        
        Returns:
            str: 架构名称，如 'x86_64', 'i386', 'aarch64' 等
            
        Raises:
            RuntimeError: 无法获取架构信息时抛出
        """
        if not self._elf_path:
            raise RuntimeError("ELF path not set")
            
        try:
            result = subprocess.run(
                ["file", self._elf_path],
                check=True,
                capture_output=True,
                text=True
            )
            
            # 解析file命令输出获取架构信息
            output = result.stdout.lower()
            if "x86-64" in output:
                return "amd64"
            elif "80386" in output:
                return "i386" 
            elif "aarch64" in output:
                return "aarch64"
            elif "arm" in output:
                return "arm"
            else:
                raise RuntimeError(f"Unknown architecture in file output: {output}")
                
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get architecture: {e}")
            
    def _find_glibc_files(self, base_path: str, arch: str) -> Tuple[Optional[str], Optional[str]]:
        """
        查找指定架构的链接器和libc文件
        
        Args:
            base_path: GLIBC基础路径
            arch: 目标架构
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (链接器路径, libc路径)
        """
        try:
            # 查找链接器
            ld_paths = glob.glob(os.path.join(base_path, "ld*"))
            interpreter_path = ld_paths[0] if ld_paths else None
            
            # 查找libc
            libc_paths = glob.glob(os.path.join(base_path, "libc.so.6"))
            libc_path = libc_paths[0] if libc_paths else None
            
            return interpreter_path, libc_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to find GLIBC files: {e}")
    
    def _patch_interpreter(self, interpreter_path: str):
        """
        修改ELF文件的解释器
        
        Args:
            interpreter_path: 新的解释器路径
        """
        if not self._elf_path:
            raise RuntimeError("ELF path not set")
            
        try:
            subprocess.run(
                ["patchelf", "--set-interpreter", interpreter_path, self._elf_path],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to patch interpreter: {e.stderr.decode()}")
    
    def _patch_rpath(self, rpath: str):
        """
        修改ELF文件的RPATH
        
        Args:
            rpath: 新的RPATH路径
        """
        if not self._elf_path:
            raise RuntimeError("ELF path not set")
            
        try:
            subprocess.run(
                ["patchelf", "--set-rpath", rpath, self._elf_path],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to patch RPATH: {e.stderr.decode()}")
            
    def _get_ldd_info(self) -> str:
        """
        获取ELF文件的ldd信息
        
        Returns:
            str: ldd命令输出
            
        Raises:
            RuntimeError: 执行ldd命令失败时抛出
        """
        if not self._elf_path:
            raise RuntimeError("ELF path not set")
            
        try:
            result = subprocess.run(
                ["ldd", self._elf_path],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get ldd info: {e}")
