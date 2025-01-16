# EPWN

EPWN is a Python-based PWN automation tool that integrates script generation and program analysis capabilities.

## Features

- Automatic binary program analysis and pwntools script generation
- Intelligent analysis powered by OpenAI API
- Support for script templates and custom prompts
- Parallel program state exploration
- Interactive menu analysis
- Comprehensive CLI command support

## Installation

```bash
pip install epwn
```

## Configuration

Configure OpenAI API parameters before first use:

```bash
epwn config set openai.api_key "your-api-key"
epwn config set openai.base_url "https://api.openai.com/v1"  # Optional, defaults to OpenAI official API
epwn config set openai.model "gpt-3.5-turbo"  # Optional, defaults to gpt-3.5-turbo
```

## Usage

### Auto-Generate PWN Script

Basic usage:
```bash
epwn script auto ./vuln exploit.py
```

Using a template:
```bash
epwn script auto ./vuln exploit.py -t template.py
```

Providing additional hints:
```bash
epwn script auto ./vuln exploit.py -p "Watch out for integer overflow"
```

### Analyze Program Menu

```bash
# Save program menu output to file
./vuln > menu.txt
# Analyze menu
epwn script analyze-menu menu.txt
```

### Record Interactions Manually

Add successful interaction:
```bash
epwn script add-interaction "1" "Menu option 1 selected"
```

Add failed interaction:
```bash
epwn script add-interaction "invalid" "Error: Invalid input" --failure --error "Invalid menu option"
```

### Get Next Action Suggestion

```bash
epwn script next-action
```

### Generate Script from Records

```bash
epwn script generate vuln exploit.py
```

### Clear Interaction History

```bash
epwn script clear
```

## Script Templates

You can create custom script templates using the `# SCRIPT_CONTENT` marker to specify where generated content should be inserted:

```python
from pwn import *

# Custom settings
context.log_level = 'debug'
context.arch = 'amd64'

# SCRIPT_CONTENT

# Custom helper functions
def debug():
    gdb.attach(io)
    pause()
```

## Important Notes

1. Ensure target programs have executable permissions
2. It's recommended to backup important files before use
3. Generated scripts may need adjustments based on specific scenarios

## Contributing

Issues and Pull Requests are welcome!

## License

MIT License 