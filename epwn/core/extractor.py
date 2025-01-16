#!/usr/bin/env python3
from pathlib import Path
import subprocess
import shutil
from typing import Optional, Dict, List, Union
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
import os
import tarfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import config

@dataclass
class ExtractionResult:
    """解压结果数据结构"""
    success: bool
    package_name: str
    extract_path: str
    error: Optional[str] = None
    total_bytes: Optional[int] = None

class PackageExtractor:
    """包解压器"""
    def __init__(self, extract_dir: Optional[str] = None, max_workers: int = 5):
        """
        初始化解压器
        
        Args:
            extract_dir: 解压目标目录，默认使用配置值
            max_workers: 最大并发解压数
        """
        # 从配置获取默认值
        self.extract_dir = Path(extract_dir or config.get_path("extract_dir"))
        self.console = Console()
        self.max_workers = max_workers
        
        # 创建解压目录
        os.makedirs(self.extract_dir, exist_ok=True)
        
    def _extract_single_package(self, package_path: str, progress, task_id) -> ExtractionResult:
        """
        解压单个包文件
        
        Args:
            package_path: 包文件路径
            progress: rich进度条对象
            task_id: 任务ID
            
        Returns:
            ExtractionResult: 解压结果
        """
        package_path = Path(package_path)
        package_name = package_path.stem
        
        # 创建解压目录
        extract_path = self.extract_dir / package_name
        os.makedirs(extract_path, exist_ok=True)
        
        try:
            # 获取文件大小
            total_bytes = os.path.getsize(package_path)
            progress.update(task_id, total=total_bytes)
            
            # 使用dpkg命令解压.deb包
            cmd = ["dpkg-deb", "-x", str(package_path), str(extract_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # 更新进度
            progress.update(task_id, advance=total_bytes)
            progress.update(task_id, description=f"[green]Extracted {package_name}")
            
            return ExtractionResult(
                success=True,
                package_name=package_name,
                extract_path=str(extract_path),
                total_bytes=total_bytes
            )
            
        except subprocess.CalledProcessError as e:
            progress.update(task_id, description=f"[red]Failed to extract {package_name}")
            return ExtractionResult(
                success=False,
                package_name=package_name,
                extract_path=str(extract_path),
                error=f"dpkg-deb error: {e.stderr}"
            )
        except Exception as e:
            progress.update(task_id, description=f"[red]Failed to extract {package_name}")
            return ExtractionResult(
                success=False,
                package_name=package_name,
                extract_path=str(extract_path),
                error=str(e)
            )
            
    def extract(self, package_paths: Union[str, List[str]], max_workers: int = 5) -> Union[ExtractionResult, List[ExtractionResult]]:
        """
        解压包文件，支持单个包或多个包
        
        Args:
            package_paths: 包文件路径或路径列表
            max_workers: 最大并发数，默认5
            
        Returns:
            Union[ExtractionResult, List[ExtractionResult]]: 单个包时返回单个结果，多个包时返回结果列表
        """
        # 处理单个包的情况
        if isinstance(package_paths, str):
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
            ) as progress:
                task_id = progress.add_task(f"[cyan]Extracting {Path(package_paths).stem}", total=None)
                result = self._extract_single_package(package_paths, progress, task_id)
                self._print_summary([result])
                return result
                
        # 处理多个包的情况
        package_paths = list(package_paths)  # 确保是列表
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
        ) as progress:
            # 创建总体进度任务
            overall_task = progress.add_task("[yellow]Total Progress", total=None)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for path in package_paths:
                    task_id = progress.add_task(f"[cyan]Extracting {Path(path).stem}", total=None)
                    future = executor.submit(self._extract_single_package, path, progress, task_id)
                    futures.append(future)
                    
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    
        # 打印解压结果
        self._print_summary(results)
                    
        return results
            
    def _print_summary(self, results: List[ExtractionResult]):
        """
        打印解压结果摘要
        
        Args:
            results: 解压结果列表
        """
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        
        self.console.print("\n[bold]Extraction Summary:[/bold]")
        
        # 创建汇总表格
        table = Table(title="Extraction Results")
        table.add_column("Package Name", style="cyan")
        table.add_column("Status")
        table.add_column("Size")
        table.add_column("Path")
        table.add_column("Error")
        
        total_size = 0
        for result in results:
            status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
            
            # 获取文件大小
            size = ""
            if result.success and result.total_bytes:
                size_bytes = result.total_bytes
                total_size += size_bytes
                # 转换为合适的单位
                if size_bytes < 1024:
                    size = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size = f"{size_bytes/1024:.1f} KB"
                else:
                    size = f"{size_bytes/(1024*1024):.1f} MB"
            
            # 获取保存路径和错误信息
            path = result.extract_path if result.success else ""
            error = result.error if not result.success else ""
            
            table.add_row(result.package_name, status, size, path, error)
            
        # 添加总计行
        if total_size > 0:
            total_size_str = f"{total_size/(1024*1024):.1f} MB" if total_size > 1024*1024 else f"{total_size/1024:.1f} KB"
            table.add_row(
                "[bold]Total[/bold]",
                f"[green]{successful}[/green]/[blue]{total}[/blue]",
                f"[bold]{total_size_str}[/bold]",
                "",
                ""
            )
            
        self.console.print(table)