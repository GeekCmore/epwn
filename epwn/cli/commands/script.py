"""
脚本生成命令组
"""
import click
from rich.console import Console
from pathlib import Path
import sys

from epwn.core.script import get_script_generator

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
            console.print(f"[green]Script generated and saved to {output_file}![/green]")
    except Exception as e:
        console.print(f"[red]Error generating script: {str(e)}[/red]")
        sys.exit(1)

@script.command()
@click.argument('menu_text', type=click.File('r'))
def analyze_menu(menu_text):
    """分析程序菜单并提供建议
    
    参数说明:
    \b
    MENU_TEXT: 包含程序菜单输出的文件
    
    示例:
    \b
    # 分析菜单文件
    epwn script analyze-menu menu.txt
    """
    try:
        content = menu_text.read()
        suggestion = script_generator.analyze_menu(content)
        if suggestion:
            console.print("\n[green]Analysis complete![/green]")
    except Exception as e:
        console.print(f"[red]Error analyzing menu: {str(e)}[/red]")
        sys.exit(1)

@script.command()
@click.argument('input_text')
@click.argument('output_text')
@click.option('--success/--failure', default=True, help="标记交互是否成功")
@click.option('--error', default="", help="如果失败，提供错误信息")
def add_interaction(input_text, output_text, success, error):
    """添加程序交互记录
    
    参数说明:
    \b
    INPUT_TEXT: 输入的命令或数据
    OUTPUT_TEXT: 程序的输出结果
    
    示例:
    \b
    # 添加成功的交互
    epwn script add-interaction "1" "Menu option 1 selected"
    
    # 添加失败的交互
    epwn script add-interaction "invalid" "Error: Invalid input" --failure --error "Invalid menu option"
    """
    try:
        script_generator.add_interaction(input_text, output_text, success, error)
        console.print("[green]Interaction added successfully![/green]")
    except Exception as e:
        console.print(f"[red]Error adding interaction: {str(e)}[/red]")
        sys.exit(1)

@script.command()
def next_action():
    """获取下一步操作建议
    
    示例:
    \b
    # 获取建议
    epwn script next-action
    """
    try:
        suggestion = script_generator.get_next_action()
        if suggestion:
            console.print("\n[green]Suggestion generated![/green]")
    except Exception as e:
        console.print(f"[red]Error getting next action: {str(e)}[/red]")
        sys.exit(1)

@script.command()
@click.argument('program_name')
@click.argument('output_file')
def generate(program_name, output_file):
    """生成完整的PWN脚本
    
    参数说明:
    \b
    PROGRAM_NAME: 目标程序名称
    OUTPUT_FILE: 输出脚本文件路径
    
    示例:
    \b
    # 生成脚本
    epwn script generate vuln exploit.py
    """
    try:
        script_content = script_generator.generate_script(program_name, script_generator.interaction_history)
        if script_content:
            script_generator.save_script(script_content, output_file)
            console.print(f"[green]Script generated and saved to {output_file}![/green]")
    except Exception as e:
        console.print(f"[red]Error generating script: {str(e)}[/red]")
        sys.exit(1)

@script.command()
def clear():
    """清除交互历史
    
    示例:
    \b
    # 清除历史
    epwn script clear
    """
    try:
        script_generator.interaction_history.clear()
        console.print("[green]Interaction history cleared![/green]")
    except Exception as e:
        console.print(f"[red]Error clearing history: {str(e)}[/red]")
        sys.exit(1) 