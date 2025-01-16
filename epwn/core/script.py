"""
OpenAI API 调用模块，用于分析程序交互并生成pwntools脚本
"""
from typing import List, Dict, Any, Optional, Set, Tuple
import openai
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from dataclasses import dataclass
from .config import config as config_instance
from pathlib import Path
import subprocess
import time
import os
import select
import signal
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import itertools

# 创建console并设置不截断输出
console = Console()

@dataclass
class InteractionResult:
    """交互结构数据结构"""
    input_sequence: List[str]  # 存储完整的输入序列
    output: str
    success: bool = True
    error_msg: str = ""

class ProcessManager:
    """进程管理器"""
    def __init__(self, binary_path: str):
        self.binary_path = binary_path
        
    def start_process(self) -> subprocess.Popen:
        """启动新进程"""
        return subprocess.Popen(
            [self.binary_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid
        )
        
    def read_output(self, proc: subprocess.Popen, timeout: float = 1.0) -> str:
        """读取进程输出"""
        output = ""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            if proc.poll() is not None:
                break
                
            try:
                readable, _, _ = select.select([proc.stdout], [], [], 0.1)
                if not readable:
                    continue
                    
                line = proc.stdout.readline()
                if not line:
                    break
                output += line
            except (select.error, IOError):
                break
                
        return output
        
    def interact(self, proc: subprocess.Popen, input_text: str) -> str:
        """与进程交互"""
        try:
            proc.stdin.write(input_text + "\n")
            proc.stdin.flush()
            return self.read_output(proc)
        except IOError:
            return ""
            
    def cleanup_process(self, proc: subprocess.Popen):
        """清理进程"""
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=1)
            except:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except:
                    pass

class ScriptGenerator:
    """PWN脚本生成器"""
    
    def __init__(self):
        """初始化生成器"""
        self.client = None
        self.model = None
        self.temperature = None
        self.max_tokens = None
        self.interaction_history: List[InteractionResult] = []
        self.max_threads = 8  # 最大并发线程数
        self.max_depth = 5  # 最大探索深度
        self.explored_sequences: Set[Tuple[str, ...]] = set()  # 已探索的序列
        self.sequence_queue = Queue()  # 待探索的序列队列
        self.process_manager = None
        self.user_prompt = ""  # 添加用户提示存储

    def ensure_initialized(self):
        """确保OpenAI客户端已初始化"""
        if self.client is not None:
            return

        try:
            console.print("[cyan]Initializing OpenAI client...[/cyan]")
            config_instance.ensure_initialized()
            api_key = config_instance.get_openai("api_key")
            if not api_key:
                raise ValueError("OpenAI API key not found in configuration")
            
            base_url = config_instance.get_openai("base_url")
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            self.model = config_instance.get_openai("model")
            self.temperature = config_instance.get_openai("temperature")
            self.max_tokens = config_instance.get_openai("max_tokens")
            console.print("[green]OpenAI client initialized successfully[/green]")
            
        except Exception as e:
            console.print(f"[red]Failed to initialize script generator: {str(e)}[/red]")
            raise

    def get_possible_inputs(self, output: str) -> List[str]:
        """分析程序输出并返回所有可能的输入选项"""
        self.ensure_initialized()
        try:
            console.print("[cyan]Analyzing program output for possible inputs...[/cyan]")
            prompt = f"""Analyze this program output and list ALL possible valid inputs:

            {output}

            Return ONLY a Python list of strings representing valid inputs.
            Example: ['1', '2', '3', '4']
            Do not include any explanations, just the list."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a binary analysis expert. Return only a Python list of possible inputs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            try:
                inputs = eval(response_text)
                if isinstance(inputs, list) and all(isinstance(x, str) for x in inputs):
                    console.print(f"[green]Found {len(inputs)} possible inputs[/green]")
                    return inputs
            except:
                pass
            
            console.print("[yellow]No valid inputs found[/yellow]")
            return []
            
        except Exception as e:
            console.print(f"[red]Error getting possible inputs: {str(e)}[/red]")
            return []

    def explore_sequence(self, input_sequence: List[str]) -> Optional[InteractionResult]:
        """探索一个输入序列"""
        process = self.process_manager.start_process()
        try:
            # 获取初始输出
            initial_output = self.process_manager.read_output(process)
            current_output = initial_output
            
            # 执行输入序列
            for input_text in input_sequence:
                output = self.process_manager.interact(process, input_text)
                if not output:
                    return None
                current_output = output
            
            # 获取当前状态的可能输入
            possible_inputs = self.get_possible_inputs(current_output)
            
            # 将新的序列加入队列
            for new_input in possible_inputs:
                new_sequence = input_sequence + [new_input]
                if len(new_sequence) <= self.max_depth:
                    sequence_key = tuple(new_sequence)
                    if sequence_key not in self.explored_sequences:
                        self.sequence_queue.put(new_sequence)
            
            return InteractionResult(
                input_sequence=input_sequence,
                output=current_output
            )
            
        finally:
            self.process_manager.cleanup_process(process)

    def parallel_explore(self, binary_path: str, max_sequences: int = 1000) -> None:
        """并行探索程序状态空间"""
        self.process_manager = ProcessManager(binary_path)
        
        console.print("[cyan]Starting program exploration...[/cyan]")
        
        # 初始化探索
        process = self.process_manager.start_process()
        initial_output = self.process_manager.read_output(process)
        self.process_manager.cleanup_process(process)
        
        # 记录初始状态
        self.interaction_history.append(InteractionResult(
            input_sequence=[],
            output=initial_output
        ))
        
        # 获取初始可能输入
        initial_inputs = self.get_possible_inputs(initial_output)
        for input_text in initial_inputs:
            self.sequence_queue.put([input_text])
        
        explored_count = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            explore_task = progress.add_task(
                "[cyan]Exploring program states...", 
                total=max_sequences
            )
            
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                futures = set()
                
                while (not self.sequence_queue.empty() and 
                       explored_count < max_sequences and 
                       len(self.explored_sequences) < max_sequences):
                    
                    # 清理完成的任务
                    done = set(f for f in futures if f.done())
                    futures -= done
                    for f in done:
                        try:
                            result = f.result()
                            if result:
                                self.interaction_history.append(result)
                                progress.update(explore_task, advance=1)
                        except Exception as e:
                            console.print(f"[red]Error in exploration task: {str(e)}[/red]")
                    
                    # 如果有可用线程，启动新任务
                    while (len(futures) < self.max_threads and 
                           not self.sequence_queue.empty() and 
                           explored_count < max_sequences):
                        sequence = self.sequence_queue.get()
                        sequence_key = tuple(sequence)
                        
                        if sequence_key not in self.explored_sequences:
                            self.explored_sequences.add(sequence_key)
                            futures.add(executor.submit(self.explore_sequence, sequence))
                            explored_count += 1
                    
                    time.sleep(0.1)  # 避免过度消耗CPU
                
                # 等待所有任务完成
                for f in futures:
                    try:
                        result = f.result()
                        if result:
                            self.interaction_history.append(result)
                            progress.update(explore_task, advance=1)
                    except Exception as e:
                        console.print(f"[red]Error in exploration task: {str(e)}[/red]")
        
        console.print(f"[green]Exploration completed. Found {len(self.interaction_history)} unique interactions[/green]")

    def auto_generate(self, binary_path: str, template_path: Optional[str] = None, user_prompt: str = "") -> str:
        """自动探索程序并生成脚本
        
        Args:
            binary_path: 目标程序路径
            template_path: 脚本模板文件路径
            user_prompt: 用户提供的额外提示信息
        """
        self.ensure_initialized()
        self.user_prompt = user_prompt  # 存储用户提示
        
        try:
            binary_path = os.path.abspath(binary_path)
            if not os.path.exists(binary_path):
                raise FileNotFoundError(f"Binary not found: {binary_path}")
            
            console.print(f"[cyan]Processing binary: {binary_path}[/cyan]")
            
            # 确保文件是可执行的
            os.chmod(binary_path, 0o755)
            
            # 读取模板
            template = ""
            if template_path:
                if os.path.exists(template_path):
                    console.print(f"[cyan]Loading template from: {template_path}[/cyan]")
                    with open(template_path, 'r') as f:
                        template = f.read()
                else:
                    console.print(f"[yellow]Warning: Template file not found: {template_path}[/yellow]")
            
            # 并行探索程序
            self.parallel_explore(binary_path)
            
            # 生成脚本
            program_name = os.path.basename(binary_path)
            console.print("[cyan]Generating pwntools script...[/cyan]")
            script_content = self.generate_script(program_name, self.interaction_history)
            
            # 提取纯代码部分
            if "```python" in script_content:
                script_content = script_content.split("```python")[1]
                if "```" in script_content:
                    script_content = script_content.split("```")[0]
            
            # 清理代码
            script_content = script_content.strip()
            
            # 如果有模板，将生成的内容合并到模板中
            if template:
                console.print("[cyan]Merging with template...[/cyan]")
                script_content = template.replace("# SCRIPT_CONTENT", script_content)
            
            console.print("[green]Script generation completed successfully[/green]")
            return script_content
            
        except Exception as e:
            console.print(f"[red]Error during auto generation: {str(e)}[/red]")
            return ""

    def generate_script(self, program_name: str, interaction_history: List[InteractionResult]) -> str:
        """生成最终的pwntools脚本"""
        self.ensure_initialized()
        try:
            # 构建完整的交互历史
            history_text = "\n".join([
                f"Input sequence: {result.input_sequence}\nOutput: {result.output}\n"
                for result in interaction_history
            ])

            # 构建基础提示
            base_prompt = f"""Based on these program interactions:

            {history_text}

            Generate a complete pwntools script that implements the observed functionality.
            Include functions for each menu option and proper error handling.
            The script should be ready to use without any modifications."""

            # 添加用户提示
            if self.user_prompt:
                base_prompt += f"\n\nAdditional requirements:\n{self.user_prompt}"

            prompt = f"""{base_prompt}
            
            Format the response as:
            ```python
            <complete script>
            ```

            Use this template:
            ```python
            from pwn import *

            filename = "{program_name}"
            elf = context.binary = ELF(filename)

            def start():
                if args.GDB:
                    return gdb.debug(elf.path, gdbscript = gs)
                elif args.REMOTE:
                    return remote(host, port)
                else:
                    return process(elf.path)

            # Implement functions for each menu option
            # Include docstrings and error handling
            ```"""

            console.print("[cyan]Generating pwntools script...[/cyan]")
            
            # 构建系统提示
            system_prompt = """You are an expert in binary exploitation and pwntools scripting. 
            Generate only the script code without any explanations or markdown."""
            
            # 如果有用户提示，添加到系统提示中
            if self.user_prompt:
                system_prompt += "\nPlease also consider these additional requirements while generating the script."

            response_text = ""
            with Live(Markdown(""), refresh_per_second=4, console=console) as live:
                for chunk in self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True
                ):
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_text += content
                        live.update(Markdown(response_text))
            
            console.print("[green]Script generation completed[/green]")
            return response_text
            
        except Exception as e:
            console.print(f"[red]Error generating script: {str(e)}[/red]")
            return ""

    def save_script(self, script_content: str, filename: str) -> None:
        """保存生成的脚本到文件"""
        try:
            console.print(f"[cyan]Saving script to: {filename}[/cyan]")
            script_path = Path(filename)
            script_path.write_text(script_content)
            console.print(f"[green]Script saved successfully to {filename}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving script: {str(e)}[/red]")

def get_script_generator() -> ScriptGenerator:
    """Get or create a script generator instance with proper error handling"""
    try:
        console.print("[cyan]Creating new script generator instance...[/cyan]")
        generator = ScriptGenerator()
        console.print("[green]Script generator created successfully[/green]")
        return generator
    except Exception as e:
        console.print(f"[red]Failed to create script generator: {str(e)}[/red]")
        raise

# Export the function instead of a global instance
__all__ = ['get_script_generator', 'ScriptGenerator', 'InteractionResult']
