"""
GLIBC版本管理命令组
"""
import click
from rich.console import Console
from rich.table import Table
import sys
from typing import Optional, List, Tuple
import os
from pathlib import Path

from epwn.core.version import GlibcVersionManager
from epwn.core.crawler import GlibcCrawler
from epwn.core.downloader import Downloader
from epwn.core.extractor import PackageExtractor

console = Console()

@click.group()
def glibc():
    """GLIBC版本管理命令组"""
    pass

@glibc.command()
def list():
    """列出已安装的GLIBC版本"""
    try:
        version_manager = GlibcVersionManager()
        installed_versions = version_manager.list_versions()
        
        if not installed_versions:
            console.print("[yellow]No GLIBC versions installed.")
            return
            
        table = Table(show_header=True)
        table.add_column("Version", style="cyan")
        table.add_column("Libc Path", style="green")
        table.add_column("Interpreter Path", style="blue")
        table.add_column("Added At", style="magenta")
        
        for version in installed_versions:
            table.add_row(
                version["version"],
                version["libc_path"],
                version["interpreter_path"],
                version["created_at"]
            )
            
        console.print("\nInstalled GLIBC versions:")
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to list GLIBC versions: {str(e)}")
        sys.exit(1)

def _install_glibc(version: Optional[str], arch: str, force: bool, nums: int, packages: List[str]):
    """安装GLIBC的核心逻辑
    
    Args:
        version: 指定版本号,为None时安装所有版本
        arch: 系统架构
        force: 是否强制重新安装
        nums: 每个版本保留的最新子版本数量
        packages: 需要下载的包列表
        
    Returns:
        Tuple[int, int, int]: (找到的包总数, 下载成功数, 安装成功数)
    """
    version_manager = GlibcVersionManager()
    crawler = GlibcCrawler()
    
    # 检查是否已安装
    if version and not force:
        if version_manager.find_glibc(version):
            console.print(f"[yellow]GLIBC {version} 已安装。使用--force强制重新安装。")
            return (0, 0, 0)

    # 获取包下载URL
    if version:
        package_urls = crawler.getOnePackageDownloadUrl(version, [arch], packages)
        if not package_urls:
            console.print(f"[red]Version {version} not found")
            return (0, 0, 0)
        filtered_urls = {version: package_urls}
    else:
        package_urls = crawler.getPackageDownloadUrl([arch], packages)
        if not package_urls:
            console.print("[red]No packages found to download")
            return (0, 0, 0)
            
        # 按主版本号分组并只保留最新的nums个子版本
        version_groups = {}
        for ver in package_urls:
            major_ver = '.'.join(ver.split('-')[0].split('.')[:2])
            if major_ver not in version_groups:
                version_groups[major_ver] = []
            version_groups[major_ver].append(ver)
        
        filtered_urls = {}
        for vers in version_groups.values():
            vers.sort(reverse=True)
            for ver in vers[:nums]:
                filtered_urls[ver] = package_urls[ver]
    
    # 显示将要安装的版本
    table = Table(show_header=True)
    table.add_column("Version", style="cyan")
    table.add_column("Architecture", style="cyan")
    for pkg in packages:
        table.add_column(pkg, style="green")
    
    download_files = []
    for ver, info in filtered_urls.items():
        row = [ver, arch]
        for pkg in packages:
            pkg_info = info.architectures.get(arch, {}).packages.get(pkg)
            if pkg_info and pkg_info.url:
                download_files.append((pkg_info.url, pkg_info.size))
                row.append("✓")
            else:
                row.append("✗")
        table.add_row(*row)
    
    console.print("\nPackages to install:")
    console.print(table)
    
    if not download_files:
        console.print("[red]No packages found to download")
        return (0, 0, 0)
    
    # 下载包
    downloader = Downloader()
    download_results = downloader.download(download_files)
    
    # 解压安装
    extractor = PackageExtractor()
    installed_count = 0
    successful_downloads = [r for r in download_results if r.success and r.file_path]
    
    for result in successful_downloads:
        extract_result = extractor.extract_package(result.file_path)
        if extract_result.success:
            # 查找并添加libc路径
            extract_path = Path(extract_result.extract_path)
            for libc_path in extract_path.rglob("libc.so.6"):
                version_manager.add_libc_path(str(libc_path))
                installed_count += 1
                break
                
    return (len(download_files), len(successful_downloads), installed_count)

@glibc.command()
@click.option('--version', help='GLIBC版本号')
@click.option('--arch', default='amd64', help='系统架构')
@click.option('--force', is_flag=True, help='强制重新安装')
@click.option('--nums', default=3, help='每个版本保留的最新子版本数量')
@click.option('--packages', '-p', multiple=True, type=click.Choice(['libc6', 'libc6-dbg', 'glibc-source']), 
              default=['libc6'], help='需要下载的包，可指定多个')
def install(version: Optional[str], arch: str, force: bool, nums: int, packages: List[str]):
    """安装指定版本或所有版本的GLIBC"""
    try:
        total_pkgs, downloaded, installed = _install_glibc(version, arch, force, nums, packages)
        
        # 显示安装结果
        result_table = Table(show_header=True)
        result_table.add_column("Status", style="cyan")
        result_table.add_column("Count", style="green")
        
        result_table.add_row(
            "Total packages found",
            str(total_pkgs)
        )
        result_table.add_row(
            "Successfully downloaded",
            str(downloaded)
        )
        result_table.add_row(
            "Successfully installed",
            str(installed)
        )
        
        console.print("\nInstallation Summary:")
        console.print(result_table)
        
    except Exception as e:
        print(e)
        sys.exit(1)
