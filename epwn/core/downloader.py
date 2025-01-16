from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.console import Console
from rich.table import Table
from pathlib import Path
import requests
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
from .config import config

@dataclass
class DownloadResult:
    """下载结果数据结构"""
    url: str
    success: bool
    file_path: Optional[str] = None
    error: Optional[str] = None

class Downloader:
    """下载管理器"""
    def __init__(self):
        self.console = Console()
        
        # 从配置获取下载参数
        try:
            config.ensure_initialized()
            self.save_dir = config.get_download("download_dir")
            self.max_workers = config.get_download("max_workers")
            self.chunk_size = config.get_download("chunk_size")
            self.max_retries = config.get_download("max_retries")
            self.timeout = config.get_download("timeout")
            self.proxies = config.get_download("proxies")
            
            # 确保下载目录存在
            os.makedirs(self.save_dir, exist_ok=True)
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Failed to load download configuration: {e}[/yellow]")
            self.console.print("[yellow]Using default values[/yellow]")
            
            # 使用默认值
            self.save_dir = os.path.join(os.path.expanduser("~"), ".cache", "epwn", "downloads")
            self.max_workers = 5
            self.chunk_size = 8192
            self.max_retries = 3
            self.timeout = 30
            self.proxies = None
            
            # 确保下载目录存在
            os.makedirs(self.save_dir, exist_ok=True)

    def _download_file(self, url: str, size: int, progress, overall_task) -> DownloadResult:
        """下载单个文件"""
        filename = os.path.basename(url)
        save_path = os.path.join(self.save_dir, filename)
        
        # 创建任务
        task = progress.add_task(
            f"[cyan]Downloading {filename}",
            total=size,
            start=False
        )
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 发起请求
                response = requests.get(
                    url,
                    stream=True,
                    timeout=self.timeout,
                    proxies=self.proxies
                )
                response.raise_for_status()
                
                # 开始下载
                progress.start_task(task)
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))
                            progress.update(overall_task, advance=len(chunk))
                
                # 下载成功
                progress.update(task, description=f"[green]✓ {filename}")
                return DownloadResult(
                    url=url,
                    success=True,
                    file_path=save_path
                )
                
            except requests.RequestException as e:
                # 处理网络错误
                error_msg = f"Download failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                progress.update(task, description=f"[red]{error_msg}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # 重试前等待
                    continue
                    
                return DownloadResult(
                    url=url,
                    success=False,
                    error=error_msg
                )
            
            except Exception as e:
                # 处理其他错误
                error_msg = f"Unexpected error: {str(e)}"
                progress.update(task, description=f"[red]{error_msg}")
                return DownloadResult(
                    url=url,
                    success=False,
                    error=error_msg
                )
                
    def download(self, files: List[Tuple[str, int]]) -> List[DownloadResult]:
        """
        并发下载多个文件
        
        Args:
            files: 下载文件列表，每个元素为(url, size)的元组
            
        Returns:
            List[DownloadResult]: 下载结果列表
        """
        results = []
        
        # 计算总大小
        total_size = sum(int(size) if isinstance(size, str) else size for _, size in files)
        
        # 创建进度条
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            # 创建总体进度任务
            overall_task = progress.add_task("[yellow]Total Progress", total=total_size)
            
            # 并发下载
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for url, size in files:
                    # 确保size是整数
                    size = int(size) if isinstance(size, str) else size
                    future = executor.submit(
                        self._download_file,
                        url,
                        size,
                        progress,
                        overall_task
                    )
                    futures.append(future)
                    
                # 收集结果
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    
        # 打印下载结果表格
        table = Table(title="Download Results")
        table.add_column("URL", style="cyan")
        table.add_column("Status")
        table.add_column("Path/Error")
        
        for result in results:
            status = "[green]✓ Success" if result.success else "[red]✗ Failed"
            path_or_error = result.file_path if result.success else f"[red]{result.error or ''}"
            table.add_row(
                os.path.basename(result.url),
                status,
                path_or_error
            )
        
        self.console.print(table)
                    
        return results