"""
GLIBC版本管理和ELF补丁工具的核心功能模块
"""
from .version import GlibcVersionManager
from .patcher import ElfPatcher, PatchResult
from .crawler import (
    GlibcCrawler,
    PackageInfo,
    ArchitectureInfo,
    VersionInfo
)
from .downloader import Downloader, DownloadResult
from .extractor import PackageExtractor, ExtractionResult

__all__ = [
    # 版本管理
    'GlibcVersionManager',
    
    # 补丁工具
    'ElfPatcher',
    'PatchResult',
    
    # 包管理
    'GlibcCrawler',
    'PackageInfo',
    'ArchitectureInfo',
    'VersionInfo',
    'Downloader',
    'DownloadResult',
    'PackageExtractor',
    'ExtractionResult',
] 