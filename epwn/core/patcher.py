"""
ELF补丁模块
"""
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from .version import GlibcVersionManager

@dataclass
class PatchResult:
    """补丁结果"""
    success: bool
    error: Optional[str] = None

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
            glibc_info = self._version_manager.find_glibc(version)
            if not glibc_info:
                return PatchResult(False, f"GLIBC version {version} not found")
            
            # 设置ELF文件路径
            self._elf_path = elf_path
            
            # 应用补丁
            self._patch_interpreter(glibc_info["interpreter"])
            self._patch_rpath(str(Path(glibc_info["interpreter"]).parent))
            
            return PatchResult(True)
            
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
