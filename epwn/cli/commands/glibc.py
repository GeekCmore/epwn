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
import shutil
import tarfile

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
def show():
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
        table.add_column("Debug Path", style="magenta")
        table.add_column("Source Path", style="yellow")
        table.add_column("Added At", style="magenta")
        
        for version in installed_versions:
            table.add_row(
                version["version"],
                version["libc_path"],
                version.get("debug_path", ""),
                version.get("source_path", ""),
                version["created_at"]
            )
            
        console.print("\nInstalled GLIBC versions:")
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to list GLIBC versions: {str(e)}")
        sys.exit(1)

@glibc.command()
@click.argument('version')
def info(version: str):
    """查看指定GLIBC版本的详细信息"""
    try:
        version_manager = GlibcVersionManager()
        glibc_info = version_manager.get_glibc_info(version)
        
        if not glibc_info:
            console.print(f"[yellow]GLIBC version {version} not found.")
            return
            
        # 创建详细信息表格
        table = Table(show_header=True, title=f"GLIBC {version} Information")
        table.add_column("Property", style="cyan", justify="right")
        table.add_column("Value", style="green")
        
        table.add_row("Version", version)
        table.add_row("Libc Path", glibc_info["libc_path"])
        
        if "debug_path" in glibc_info:
            table.add_row("Debug Symbols Path", glibc_info["debug_path"])
        if "source_path" in glibc_info:
            table.add_row("Source Code Path", glibc_info["source_path"])
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to get GLIBC info: {str(e)}")
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
        if version_manager.get_glibc_info(version):
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
    
    # 按版本分组下载结果
    version_downloads = {}
    for result in successful_downloads:
        filename = os.path.basename(result.url)
        if 'libc6_' in filename:
            version = filename.split('libc6_')[1].split('_')[0]
            if version not in version_downloads:
                version_downloads[version] = {'libc6': None, 'libc6-dbg': None, 'glibc-source': None}
            version_downloads[version]['libc6'] = result
        elif 'libc6-dbg_' in filename:
            version = filename.split('libc6-dbg_')[1].split('_')[0]
            if version not in version_downloads:
                version_downloads[version] = {'libc6': None, 'libc6-dbg': None, 'glibc-source': None}
            version_downloads[version]['libc6-dbg'] = result
        elif 'glibc-source_' in filename:
            version = filename.split('glibc-source_')[1].split('_')[0]
            if version not in version_downloads:
                version_downloads[version] = {'libc6': None, 'libc6-dbg': None, 'glibc-source': None}
            version_downloads[version]['glibc-source'] = result
    
    # 按版本安装包
    for version, version_pkgs in version_downloads.items():
        # 一次性解压所有包
        extract_results = {}
        pkg_paths = []
        for pkg_type, pkg in version_pkgs.items():
            if pkg and pkg.file_path:
                pkg_paths.append(pkg.file_path)
        
        # 解压所有包
        if pkg_paths:
            results = extractor.extract(pkg_paths)
            # 如果是单个结果，转换为列表
            if not isinstance(results, list):
                results = [results]
                
            for result in results:
                if result.success:
                    # 根据包名判断类型
                    if 'libc6_' in result.package_name:
                        extract_results['libc6'] = result
                    elif 'libc6-dbg_' in result.package_name:
                        extract_results['libc6-dbg'] = result
                    elif 'glibc-source_' in result.package_name:
                        extract_results['glibc-source'] = result
        
        # 处理解压结果
        debug_path = None
        source_path = None
        libc_path = None
        
        # 处理调试符号包
        if 'libc6-dbg' in extract_results:
            try:
                extract_path = Path(extract_results['libc6-dbg'].extract_path)
                debug_files = list(extract_path.rglob('.build-id'))
                if debug_files:
                    debug_path = str(debug_files[0])
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to process debug symbols: {e}[/yellow]")
            
        # 处理源码包
        if 'glibc-source' in extract_results:
            try:
                source_path = extract_results['glibc-source'].extract_path
                extract_path = Path(source_path)
                tar_files = list(extract_path.rglob("glibc-*.tar.xz"))
                if tar_files:
                    tar_path = tar_files[0]
                    with tarfile.open(tar_path) as tar:
                        tar.extractall(path=tar_path.parent)
                    source_dirs = [p for p in tar_path.parent.glob("glibc-*") if p.is_dir()]
                    if source_dirs:
                        source_path = str(source_dirs[0])
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to process source package: {e}[/yellow]")
                
        # 处理libc6包
        if 'libc6' in extract_results:
            try:
                extract_path = Path(extract_results['libc6'].extract_path)
                libc_files = list(extract_path.rglob("libc.so.6"))
                if libc_files:
                    libc_path = str(libc_files[0].parent)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to process libc6 package: {e}[/yellow]")
            
        if not libc_path:
            continue
        
        # 添加到数据库
        try:
            version_manager.add_version(version, libc_path, debug_path, source_path)
            count = sum(1 for path in [libc_path, debug_path, source_path] if path is not None)
            installed_count += count
            # 打印安装的路径信息
            console.print(f"[green]Added GLIBC {version} with:")
            console.print(f"  Libc: {libc_path}")
            if debug_path:
                console.print(f"  Debug: {debug_path}")
            if source_path:
                console.print(f"  Source: {source_path}")
        except Exception as e:
            console.print(f"[red]Failed to add GLIBC: {e}")
                
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

@glibc.command()
@click.option('--force', is_flag=True, help='跳过确认直接删除')
def clean(force: bool):
    """删除所有已安装的GLIBC版本"""
    try:
        # 获取配置的数据目录
        data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "epwn", "data")
        glibc_dir = os.path.join(data_dir, "glibc")
        
        if not os.path.exists(glibc_dir):
            console.print("[yellow]No GLIBC files found.")
            return
            
        # 确认删除
        if not force:
            confirm = input("\nAre you sure you want to delete all GLIBC files? [y/N] ")
            if confirm.lower() != 'y':
                console.print("[yellow]Operation cancelled.")
                return
        
        # 删除glibc目录
        try:
            shutil.rmtree(glibc_dir)
            console.print("[green]Successfully deleted all GLIBC files.")
        except Exception as e:
            console.print(f"[red]Failed to delete GLIBC directory: {str(e)}")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Failed to clean GLIBC files: {str(e)}")
        sys.exit(1)
