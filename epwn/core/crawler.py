from bs4 import BeautifulSoup
import requests
import re
import json
from rich.progress import Progress
from rich.console import Console
from rich.table import Table
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

@dataclass
class PackageInfo:
    """包信息数据结构"""
    url: str
    size: Optional[int] = 0
    error: Optional[str] = None

@dataclass
class ArchitectureInfo:
    """架构信息数据结构"""
    build_url: str
    packages: Dict[str, PackageInfo]

@dataclass
class VersionInfo:
    """版本信息数据结构"""
    version: str
    source_url: str
    architectures: Dict[str, ArchitectureInfo]

class GlibcCrawler:
    """GLIBC包下载链接爬取器"""
    
    def __init__(self):
        self.baseUrl = "https://launchpad.net/"
        self._version_list = []
        self._version_count = 0
        self._console = Console()
        self._results: Dict[str, VersionInfo] = {}

    def _get_package_download_url_by_build(self, buildUrl: str, packageList: list) -> Dict[str, PackageInfo]:
        """从构建URL获取包下载链接"""
        package_info = {}
        try:
            response = requests.get(buildUrl)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            file_links = soup.select('#files > ul > li > a')
            if not file_links:
                # 记录所有请求的包都未找到的错误
                for pkg in packageList:
                    package_info[pkg] = PackageInfo(
                        url="",
                        error="No files found in build"
                    )
                return package_info
            
            # 初始化所有包的错误状态
            for pkg in packageList:
                package_info[pkg] = PackageInfo(
                    url="",
                    error="Package not found in build"
                )
                
            for link in file_links:
                href = link.get('href', '')
                if not href:
                    continue
                
                size_text = link.find_next_sibling(string=True)
                size = size_text.strip().strip('()').strip() if size_text else None
                filename = href.split('/')[-1]
                package_name = filename.split('_')[0]
                
                if package_name in packageList:
                    package_info[package_name] = PackageInfo(
                        url=href,
                        size=self._convert_size_to_bytes(size),
                        error=None  # 成功获取则清除错误
                    )
            
        except requests.RequestException as e:
            # 记录网络请求错误
            for pkg in packageList:
                package_info[pkg] = PackageInfo(
                    url="",
                    error=f"Network error: {str(e)}"
                )
        except Exception as e:
            # 记录其他错误
            for pkg in packageList:
                package_info[pkg] = PackageInfo(
                    url="",
                    error=f"Unexpected error: {str(e)}"
                )
            
        return package_info

    def _convert_size_to_bytes(self, size_str: str) -> int:
        """
        将文件大小字符串转换为字节数
        
        Args:
            size_str: 文件大小字符串，如 "22.6 KiB", "13.3 MiB"
            
        Returns:
            int: 字节数
            
        Examples:
            >>> convert_size_to_bytes("22.6 KiB")
            23142
            >>> convert_size_to_bytes("13.3 MiB")
            13944832
        """
        
        if not size_str:
            self._console.print("[yellow]Empty size string, returning 0[/yellow]")
            return 0
            
        # 移除多余空格并分割数字和单位
        parts = size_str.strip().split()
        if len(parts) != 2:
            return 0
            
        try:
            number = float(parts[0])
            unit = parts[1].upper()
            
            # 定义单位转换
            units = {
                'KIB': 1024,
                'MIB': 1024 * 1024, 
                'GIB': 1024 * 1024 * 1024,
                'KB': 1024,
                'MB': 1024 * 1024,
                'GB': 1024 * 1024 * 1024,
                'B': 1
            }
            
            if unit not in units:
                return 0
                
            # 计算字节数并四舍五入为整数
            result = round(number * units[unit])
            return result
            
        except (ValueError, TypeError) as e:
            self._console.print(f"[red]Error converting size: {str(e)}[/red]")
            return 0    
        
    def getOnePackageDownloadUrl(self, version: str, archList: list, packageList: list, save: bool = False) -> VersionInfo:
        """
        获取指定GLIBC版本的包下载URL

        Args:
            version: GLIBC版本字符串 (例如: "2.31-0ubuntu9")
            archList: 目标架构列表 (例如: ["amd64", "i386"])
            packageList: 需要下载的包名列表 (例如: ["libc6", "libc6-dbg"])
            save: 是否保存结果到JSON文件 (默认: False)

        Returns:
            VersionInfo: 包含版本、架构和包信息的数据结构
        """
        if not self._check_version(version):
            raise ValueError(f"Invalid version format: {version}")
            
        self._console.print(f"\n[bold cyan]Fetching packages for GLIBC {version}[/bold cyan]")
        self._console.print(f"[cyan]Architectures: {', '.join(archList)}[/cyan]")
        self._console.print(f"[cyan]Packages: {', '.join(packageList)}[/cyan]\n")
        
        version_info = self._get_one_version_packages(version, archList, packageList)
        self._results[version] = version_info
        
        self._print_summary([version])
        
        if save:
            self._save_results("glibc_packages.json")
            
        return version_info

    def getPackageDownloadUrl(self, archList: list, packageList: list, save: bool = False) -> Dict[str, VersionInfo]:
        """
        获取所有可用GLIBC版本的包下载URL

        Args:
            archList: 目标架构列表 (例如: ["amd64", "i386"])
            packageList: 需要下载的包名列表 (例如: ["libc6", "libc6-dbg"])
            save: 是否保存结果到JSON文件 (默认: False)

        Returns:
            Dict[str, VersionInfo]: 版本到下载信息的映射
        """
        self._get_version_list()
        self._console.print(f"\n[bold cyan]Starting package URL collection:[/bold cyan]")
        self._console.print(f"[cyan]Found {len(self._version_list)} versions[/cyan]")
        self._console.print(f"[cyan]Architectures: {', '.join(archList)}[/cyan]")
        self._console.print(f"[cyan]Packages: {', '.join(packageList)}[/cyan]\n")
        
        with ThreadPoolExecutor() as executor:
            futures = []
            for version in self._version_list:
                future = executor.submit(self._get_one_version_packages, version, archList, packageList)
                futures.append((version, future))
            
            with Progress() as progress:
                task = progress.add_task("[cyan]Fetching package URLs...", total=len(futures))
                
                for version, future in futures:
                    try:
                        version_info = future.result()
                        self._results[version] = version_info
                    except Exception as e:
                        self._console.print(f"[red]Error processing version {version}: {str(e)}[/red]")
                    finally:
                        progress.advance(task)
        
        self._print_summary(self._version_list)
        
        if save:
            self._save_results("glibc_packages.json")
            
        return self._results

    def _get_version_count(self):
        """获取可用的GLIBC版本总数"""
        url = self.baseUrl + "ubuntu/+source/glibc/+publishinghistory"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        items_count_element = soup.select('#maincontent > div > div:nth-child(3) > div > table.upper-batch-nav > tbody > tr > td.batch-navigation-index')
        self._version_count = int(re.search(r'of\s+(\d+)\s+results', items_count_element[0].text.strip()).group(1))

    def _get_version_list_one_page(self, start: int, batch: int, memo: int) -> List[str]:
        """获取一页的GLIBC版本列表"""
        url = f"{self.baseUrl}ubuntu/+source/glibc/+publishinghistory?batch={batch}&memo={memo}&start={start}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        version_elements = soup.select('#publishing-summary > tbody > tr > td:nth-child(8) > a')
        
        versions = []
        for element in version_elements:
            version = element.text.strip()
            if self._check_version(version) and version not in self._version_list:
                versions.append(version)
                self._version_list.append(version)
        
        return versions

    def _get_version_list(self) -> List[str]:
        """获取所有可用的GLIBC版本列表"""
        self._get_version_count()
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Fetching GLIBC versions...", total=self._version_count)
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(0, self._version_count, 300):
                    future = executor.submit(self._get_version_list_one_page, i, 300, i)
                    futures.append(future)
                
                for future in as_completed(futures):
                    try:
                        future.result()
                        progress.update(task, advance=300)
                    except Exception as e:
                        self._console.print(f"[red]Error fetching versions: {str(e)}[/red]")
        
        # 按版本号排序
        self._version_list.sort(key=lambda x: [int(i) for i in re.match(r'^(2)\.(\d+)\-(\d+)ubuntu(\d+)(?:\.(\d+))?$', x).groups(default='0')])
        return self._version_list

    def _check_version(self, version: str) -> bool:
        """检查版本号格式是否有效"""
        pattern = r'^2\.\d{2}\-\d+ubuntu\d+(?:\.\d+)?$'
        return bool(re.match(pattern, version))

    def _get_one_version_packages(self, version: str, archList: list, packageList: list) -> VersionInfo:
        """获取单个版本的包信息"""
        url = self.baseUrl + "ubuntu/+source/glibc/" + version
        version_info = VersionInfo(
            version=version,
            source_url=url,
            architectures={}
        )
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            build_links = soup.select('#source-builds p a')
            
            for link in build_links:
                href = link.get('href', '')
                arch_text = link.text.strip().lower()
                
                if arch_text in [arch.lower() for arch in archList]:
                    full_url = self.baseUrl.rstrip('/') + href
                    packages = self._get_package_download_url_by_build(full_url, packageList)
                    
                    version_info.architectures[arch_text] = ArchitectureInfo(
                        build_url=full_url,
                        packages=packages
                    )
            
        except requests.RequestException as e:
            self._console.print(f"[red]Error fetching package URLs for version {version}: {str(e)}[/red]")
        except Exception as e:
            self._console.print(f"[red]Unexpected error processing version {version}: {str(e)}[/red]")
            
        return version_info

    def _print_summary(self, versions: List[str]):
        """
        打印爬取结果的统计信息
        
        Args:
            versions: 要显示的版本列表
        """
        self._console.print("\n[bold green]Crawling Summary:[/bold green]")
        
        # 检查是否有结果
        if not self._results or not any(self._results.get(v) for v in versions):
            self._console.print("[yellow]No results to display[/yellow]")
            return
            
        # 获取第一个有效的版本信息用于初始化表格
        first_version = None
        first_arch_info = None
        for version in versions:
            info = self._results.get(version)
            if info and info.architectures:
                first_version = version
                first_arch = next(iter(info.architectures))
                first_arch_info = info.architectures[first_arch]
                break
                
        if not first_version or not first_arch_info:
            self._console.print("[yellow]No valid package information found[/yellow]")
            return
        
        # 创建主表格
        table = Table(show_header=True, header_style="bold magenta", show_lines=True)
        table.add_column("Version", style="cyan")
        table.add_column("Architecture", style="cyan")
        
        # 为每个包添加一列
        package_columns = {}
        for package in first_arch_info.packages.keys():
            table.add_column(package, justify="center")
            package_columns[package] = True
        
        total_success = {pkg: 0 for pkg in package_columns}
        total_attempts = {pkg: 0 for pkg in package_columns}
        errors = []  # 收集所有错误信息
        
        for version in versions:
            info = self._results.get(version)
            if not info:
                continue
                
            for arch, arch_info in info.architectures.items():
                row = [version, arch]
                
                # 检查每个包的状态
                for package in package_columns.keys():
                    pkg_info = arch_info.packages.get(package)
                    if pkg_info and not pkg_info.error:
                        row.append("[green]✓[/green]")
                        total_success[package] += 1
                    else:
                        row.append("[red]✗[/red]")
                        if pkg_info and pkg_info.error:
                            errors.append({
                                'version': version,
                                'arch': arch,
                                'package': package,
                                'error': pkg_info.error
                            })
                    total_attempts[package] += 1
                
                table.add_row(*row)
        
        self._console.print(table)
        
        # 打印成功率统计
        self._console.print("\n[bold green]Package Success Rate:[/bold green]")
        for package, success in total_success.items():
            attempts = total_attempts[package]
            success_rate = (success / attempts * 100) if attempts > 0 else 0
            color = "green" if success_rate > 80 else "yellow" if success_rate > 50 else "red"
            self._console.print(f"[{color}]{package}: {success}/{attempts} ({success_rate:.1f}%)[/{color}]")
        
        # 打印错误详情
        if errors:
            self._console.print("\n[bold red]Error Details:[/bold red]")
            error_table = Table(show_header=True, header_style="bold red", show_lines=True)
            error_table.add_column("Version", style="cyan")
            error_table.add_column("Architecture", style="cyan")
            error_table.add_column("Package", style="yellow")
            error_table.add_column("Error", style="red")
            
            for error in errors:
                # 根据错误类型选择颜色
                error_text = error['error']
                if "Network error" in error_text:
                    error_color = "red"
                elif "No files found" in error_text or "Package not found" in error_text:
                    error_color = "yellow"
                else:
                    error_color = "magenta"
                
                error_table.add_row(
                    f"[cyan]{error['version']}[/cyan]",
                    f"[cyan]{error['arch']}[/cyan]",
                    f"[yellow]{error['package']}[/yellow]",
                    f"[{error_color}]{error_text}[/{error_color}]"
                )
            
            self._console.print(error_table)

    def _save_results(self, filename: str):
        """保存结果到JSON文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({version: asdict(info) for version, info in self._results.items()}, 
                     f, indent=2, ensure_ascii=False)
        self._console.print(f"[green]Results saved to {filename}[/green]")