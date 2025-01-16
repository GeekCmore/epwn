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
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import sys

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
                readable, _, _ = select.select([proc.stdout], [], [], 0.01)
                if not readable:
                    if output:  # 如果已经有输出了，再等待一小段时间确保没有更多数据
                        readable, _, _ = select.select([proc.stdout], [], [], 0.05)
                        if not readable:
                            break
                    continue
                
                # 使用read()一次性读取所有可用数据
                chunk = os.read(proc.stdout.fileno(), 4096).decode()
                if not chunk:
                    break
                output += chunk
                
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
        """自动分析程序并生成PWN脚本
        
        Args:
            binary_path: 目标程序路径
            template_path: 模板文件路径
            user_prompt: 用户提供的额外提示
            
        Returns:
            str: 生成的脚本内容
        """
        try:
            console.print(f"[cyan]Processing binary: {binary_path}[/cyan]")
            
            # 加载模板
            template_content = ""
            if template_path:
                console.print(f"[cyan]Loading template from: {template_path}[/cyan]")
                try:
                    with open(template_path, 'r') as f:
                        template_content = f.read()
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to load template: {e}[/yellow]")
            
            # 存储用户提示
            self.user_prompt = user_prompt
            
            # 并行探索程序状态
            self.parallel_explore(binary_path)
            
            # 生成基础脚本
            program_name = os.path.basename(binary_path)
            script_content = self.generate_script(program_name, self.interaction_history)
            
            # 合并模板
            if template_content:
                console.print("[cyan]Merging with template...[/cyan]")
                # 保留模板的头部注释
                header = ""
                for line in template_content.split('\n'):
                    if line.startswith('#') or line.startswith("'''") or line.startswith('"""'):
                        header += line + '\n'
                    else:
                        break
                
                # 在模板中查找插入点
                if "# SCRIPT_CONTENT" in template_content:
                    parts = template_content.split("# SCRIPT_CONTENT")
                    script_content = parts[0] + script_content + parts[1]
                else:
                    script_content = header + "\n" + script_content
            
            console.print("[green]Script generation completed successfully[/green]")
            return script_content
            
        except Exception as e:
            console.print(f"[red]Error generating script: {str(e)}[/red]")
            raise

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
        """保存生成的脚本到文件
        
        Args:
            script_content: 生成的脚本内容
            filename: 目标文件名
        """
        # 清理markdown代码块格式
        clean_content = script_content
        if "```" in script_content:
            # 移除markdown代码块标记
            lines = script_content.split('\n')
            clean_lines = []
            for line in lines:
                if line.strip() and not line.strip().startswith('```'):
                    clean_lines.append(line)
            clean_content = '\n'.join(clean_lines)
            
        try:
            with open(filename, 'w') as f:
                f.write(clean_content)
        except Exception as e:
            raise

class InteractionRecorder:
    """交互记录器"""
    def __init__(self, binary_path: str):
        self.binary_path = binary_path
        self.process_manager = ProcessManager(binary_path)
        self.interaction_history: List[InteractionResult] = []
        self.running = False
        
    def start(self):
        """启动记录会话"""
        try:
            self.process = self.process_manager.start_process()
            self.running = True
            
            # 获取初始输出
            initial_output = self.process_manager.read_output(self.process)
            if initial_output:
                self.interaction_history.append(InteractionResult(
                    input_sequence=[],
                    output=initial_output
                ))
                
            console.print("[green]Recording started. Press Ctrl+D to end.[/green]")
            
            # 确保输出完整显示
            sys.stdout.write(initial_output)
            sys.stdout.flush()
            
            while self.running:
                try:
                    # 使用sys.stdout.write确保输出完整显示
                    sys.stdout.flush()
                    user_input = input()
                    
                    # 发送用户输入并获取输出
                    output = self.process_manager.interact(self.process, user_input)
                    
                    # 记录交互
                    self.interaction_history.append(InteractionResult(
                        input_sequence=[user_input],
                        output=output
                    ))
                    
                    # 确保输出完整显示
                    sys.stdout.write(output)
                    sys.stdout.flush()
                    
                except EOFError:
                    self.running = False
                except KeyboardInterrupt:
                    self.running = False
                    
        finally:
            if hasattr(self, 'process'):
                self.process_manager.cleanup_process(self.process)
                
    def get_history(self) -> List[InteractionResult]:
        """获取记录的交互历史"""
        return self.interaction_history

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
