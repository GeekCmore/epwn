"""
脚本生成命令组
"""
import click
from rich.console import Console
from pathlib import Path
import sys
import os

from epwn.core.script import get_script_generator, InteractionRecorder

console = Console()

# Create script generator instance
script_generator = get_script_generator()

@click.group()
def script():
    """PWN脚本生成命令组"""
    pass

@script.command()
@click.argument('binary', type=click.Path(exists=True))
@click.argument('output_file')
@click.option('--template', '-t', type=click.Path(exists=True), help="脚本模板文件路径")
@click.option('--prompt', '-p', help="提供给AI的额外提示信息")
def auto(binary, output_file, template, prompt):
    """自动分析程序并生成PWN脚本
    
    参数说明:
    \b
    BINARY: 目标程序路径
    OUTPUT_FILE: 输出脚本文件路径
    
    示例:
    \b
    # 基本用法
    epwn script auto ./vuln exploit.py
    
    # 使用模板
    epwn script auto ./vuln exploit.py -t template.py
    
    # 提供额外提示
    epwn script auto ./vuln exploit.py -p "注意处理整数溢出"
    """
    try:
        script_content = script_generator.auto_generate(binary, template, prompt)
        if script_content:
            script_generator.save_script(script_content, output_file)
            console.print(f"[green]Script generated and saved to {output_file}![green]")
    except Exception as e:
        console.print(f"[red]Error generating script: {str(e)}[red]")
        sys.exit(1)

@script.command()
@click.argument('binary', type=click.Path(exists=True))
@click.argument('output_file')
@click.option('--template', '-t', type=click.Path(exists=True), help="脚本模板文件路径")
@click.option('--prompt', '-p', help="提供给AI的额外提示信息")
def record(binary, output_file, template, prompt):
    """记录与程序的手动交互并生成PWN脚本
    
    参数说明:
    \b
    BINARY: 目标程序路径
    OUTPUT_FILE: 输出脚本文件路径
    
    示例:
    \b
    # 基本用法
    epwn script record ./vuln exploit.py
    
    # 使用模板
    epwn script record ./vuln exploit.py -t template.py
    
    # 提供额外提示
    epwn script record ./vuln exploit.py -p "注意处理整数溢出"
    """
    try:
        # 创建记录器
        recorder = InteractionRecorder(binary)
        
        # 开始记录
        console.print(f"[cyan]Starting interaction recording for {binary}[/cyan]")
        recorder.start()
        
        # 获取交互历史
        history = recorder.get_history()
        if not history:
            console.print("[yellow]No interactions recorded[/yellow]")
            return
            
        # 生成脚本
        console.print("[cyan]Generating script from recorded interactions...[/cyan]")
        script_content = script_generator.generate_script(
            os.path.basename(binary),
            history
        )
        
        if script_content:
            script_generator.save_script(script_content, output_file)
            console.print(f"[green]Script generated and saved to {output_file}![/green]")
            
    except Exception as e:
        console.print(f"[red]Error recording interactions: {str(e)}[/red]")
        sys.exit(1)