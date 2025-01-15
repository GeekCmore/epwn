#!/usr/bin/env python3
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.patcher import GlibcPatcher
from core.downloader import Downloader
from core.extractor import PackageExtractor
from core.crawler import GlibcCrawler
from rich.console import Console
import os
import tempfile
import shutil
import subprocess
from typing import Dict, List, Tuple, Optional

def cleanup_files():
    """
    清理所有生成的文件和目录
    """
    console = Console()
    console.print("\n[yellow]Cleaning up files...")
    
    # 清理数据库文件
    if os.path.exists(".glibc.db"):
        os.remove(".glibc.db")
        console.print("[green]✓ Removed .glibc.db")
        
    # 清理JSON文件
    if os.path.exists("glibc_packages.json"):
        os.remove("glibc_packages.json")
        console.print("[green]✓ Removed glibc_packages.json")
        
    # 清理下载目录
    if os.path.exists("downloads"):
        shutil.rmtree("downloads")
        console.print("[green]✓ Removed downloads directory")
        
    # 清理解压目录
    if os.path.exists("extracted"):
        shutil.rmtree("extracted")
        console.print("[green]✓ Removed extracted directory")

def download_glibc_packages(version: str, arch: str = "amd64") -> List[str]:
    """
    下载指定版本的GLIBC包
    
    Args:
        version: GLIBC版本号
        arch: 系统架构，默认amd64
        
    Returns:
        List[str]: 下载的文件路径列表
    """
    console = Console()
    console.print(f"\n[yellow]Downloading GLIBC {version} packages...")
    
    # 创建爬虫实例获取下载链接
    crawler = GlibcCrawler()
    version_info = crawler.getOnePackageDownloadUrl(
        version,
        [arch],
        ["libc6", "libc6-dbg"],
        save=False
    )
    
    if not version_info:
        raise RuntimeError(f"Failed to get download URLs for GLIBC {version}")
    
    # 准备下载
    fetcher = Downloader(save_dir="downloads")
    urls = {}
    
    # 获取包的下载链接
    arch_info = version_info.architectures.get(arch)
    if not arch_info:
        raise RuntimeError(f"No packages found for architecture {arch}")
        
    for pkg_name, pkg_info in arch_info.packages.items():
        if pkg_info.url:
            urls[pkg_info.url] = None  # 使用默认保存路径
    
    # 执行下载
    results = fetcher.download(urls)
    
    # 收集成功下载的文件路径
    downloaded_files = []
    for result in results:
        if result.success:
            downloaded_files.append(result.file_path)
        else:
            console.print(f"[red]Failed to download {result.url}: {result.error}")
    
    return downloaded_files

def extract_packages(package_files: List[str]) -> str:
    """
    解压下载的包文件
    
    Args:
        package_files: 包文件路径列表
        
    Returns:
        str: 解压目录路径
    """
    console = Console()
    console.print("\n[yellow]Extracting packages...")
    
    extractor = PackageExtractor(extract_dir="extracted")
    results = []
    
    for pkg_file in package_files:
        result = extractor.extract_package(pkg_file)
        results.append(result)
        
    # 返回第一个成功解压的目录
    for result in results:
        if result.success:
            return result.extract_path
            
    raise RuntimeError("No packages were successfully extracted")

def find_libc_in_extracted(extract_path: str) -> str:
    """
    在解压目录中查找libc.so.6文件
    
    Args:
        extract_path: 解压目录路径
        
    Returns:
        str: libc.so.6文件的完整路径
    """
    for root, _, files in os.walk(extract_path):
        for file in files:
            if file == "libc.so.6":
                return os.path.join(root, file)
    raise FileNotFoundError("Could not find libc.so.6 in extracted files")

def create_test_program() -> Tuple[str, str]:
    """
    创建一个依赖GLIBC的测试程序
    
    Returns:
        Tuple[str, str]: (临时目录路径, 二进制文件路径)
    """
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    # 测试程序源码 - 使用一些GLIBC函数
    test_code = """
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    
    int main() {
        char *str = strdup("Hello from GLIBC!");
        printf("%s\\n", str);
        free(str);
        
        printf("GLIBC version: %s\\n", gnu_get_libc_version());
        return 0;
    }
    """
    
    try:
        # 保存源代码
        src_path = os.path.join(temp_dir, "test.c")
        with open(src_path, "w") as f:
            f.write(test_code)
        
        # 编译程序
        binary_path = os.path.join(temp_dir, "test")
        subprocess.run(
            ["gcc", "-o", binary_path, src_path],
            check=True,
            capture_output=True,
            text=True
        )
        
        return temp_dir, binary_path
        
    except Exception as e:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        raise RuntimeError(f"Failed to create test program: {e}")

def run_test(glibc_version: str = "2.31-0ubuntu9", arch: str = "amd64"):
    """
    运行完整的测试流程
    
    Args:
        glibc_version: 目标GLIBC版本
        arch: 系统架构
    """
    console = Console()
    temp_dir = None
    downloaded_files = []
    
    try:
        # 1. 下载GLIBC包
        console.print(f"\n[bold cyan]Test Step 1: Downloading GLIBC {glibc_version}[/bold cyan]")
        try:
            downloaded_files = download_glibc_packages(glibc_version, arch)
            if not downloaded_files:
                raise RuntimeError("No packages were downloaded")
            console.print("[green]✓ Download successful")
        except Exception as e:
            raise RuntimeError(f"Download failed: {e}")
            
        # 2. 解压包
        console.print("\n[bold cyan]Test Step 2: Extracting packages[/bold cyan]")
        try:
            extract_path = extract_packages(downloaded_files)
            console.print(f"[green]✓ Extraction successful: {extract_path}")
        except Exception as e:
            raise RuntimeError(f"Extraction failed: {e}")
            
        # 3. 查找解压后的libc文件
        console.print("\n[bold cyan]Test Step 3: Locating libc.so.6[/bold cyan]")
        try:
            libc_path = find_libc_in_extracted(extract_path)
            console.print(f"[green]✓ Found libc: {libc_path}")
        except FileNotFoundError as e:
            raise RuntimeError(f"Failed to find libc: {e}")
            
        # 4. 创建测试程序
        console.print("\n[bold cyan]Test Step 4: Creating test program[/bold cyan]")
        try:
            temp_dir, binary_path = create_test_program()
            console.print(f"[green]✓ Created test program: {binary_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to create test program: {e}")
        
        # 5. 创建patcher实例并添加libc
        console.print("\n[bold cyan]Test Step 5: Adding GLIBC to patcher[/bold cyan]")
        try:
            patcher = GlibcPatcher()
            version, interpreter = patcher.add_libc(libc_path)
            console.print(f"[green]✓ Added GLIBC {version}")
            console.print(f"  Interpreter: {interpreter}")
        except Exception as e:
            raise RuntimeError(f"Failed to add libc: {e}")
        
        # 6. 显示原始程序输出
        console.print("\n[bold cyan]Test Step 6: Original program output[/bold cyan]")
        try:
            result = subprocess.run(
                [binary_path],
                capture_output=True,
                text=True
            )
            console.print(f"[yellow]Output:[/yellow]\n{result.stdout}")
        except Exception as e:
            raise RuntimeError(f"Failed to run original program: {e}")
        
        # 7. 执行patch操作
        console.print(f"\n[bold cyan]Test Step 7: Patching binary to GLIBC {version}[/bold cyan]")
        result = patcher.patch(binary_path, version)
        
        if result.success:
            console.print("[green]✓ Successfully patched binary")
            
            # 8. 运行修改后的程序
            console.print("\n[bold cyan]Test Step 8: Patched program output[/bold cyan]")
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = os.path.dirname(libc_path)
            try:
                result = subprocess.run(
                    [binary_path],
                    env=env,
                    capture_output=True,
                    text=True
                )
                console.print(f"[yellow]Output:[/yellow]\n{result.stdout}")
                console.print("[green]✓ Test completed successfully")
            except Exception as e:
                raise RuntimeError(f"Failed to run patched program: {e}")
        else:
            raise RuntimeError(f"Failed to patch binary: {result.error}")
            
    except Exception as e:
        console.print(f"[red]Test failed: {e}")
        raise
        
    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            console.print("\n[green]Cleaned up temporary files")
            
        # 清理下载的文件
        for file in downloaded_files:
            if os.path.exists(file):
                os.remove(file)
        console.print("[green]Cleaned up downloaded files")
        
        # 清理其他生成的文件
        cleanup_files()

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)