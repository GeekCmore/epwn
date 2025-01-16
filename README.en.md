# EPwn

English | [简体中文](README.md)

EPwn is a powerful GLIBC version management and ELF file patching tool designed for CTF players and binary security researchers.

## Features

- **GLIBC Version Management**
  - Automatic download and installation of different GLIBC versions
  - Support for libc6, libc6-dbg, and glibc-source packages
  - Manage multiple GLIBC versions for easy switching and testing
  - View detailed information of installed versions

- **ELF File Patching**
  - Automatically fix ELF file dependencies
  - Support custom patching rules
  - Smart handling of file paths and version compatibility

- **Configuration Management**
  - Flexible configuration system
  - Support for custom settings and preferences
  - Convenient command-line interface

- **Script Generation**
  - Support for automated operation scripts
  - Rich scripting interface
  - Simplify repetitive tasks

## System Requirements

- Python >= 3.7
- Linux Operating System
- Dependencies:
  - click >= 8.0.0
  - rich >= 10.0.0

## Installation

```bash
pip install epwn
```

## Detailed Usage

### 1. Configuration Management (config)

The configuration management commands are used to manage EPwn settings, including path configuration, download settings, and OpenAI API configuration.

#### Initialize Configuration

```bash
epwn config setup
```

This command will guide you through the basic configuration, including:
- Data directory settings
- Download directory settings
- OpenAI API configuration
- Other basic settings

#### View Current Configuration

```bash
epwn config show
```

Displays all current configuration items, including:
- Path configuration
- Database settings
- Download configuration
- OpenAI settings

#### Modify Configuration

```bash
# Set paths
epwn config set paths data_dir ~/.epwn/data
epwn config set paths download_dir ~/.epwn/downloads

# Set download parameters
epwn config set download max_workers 10
epwn config set download timeout 30

# Set OpenAI
epwn config set openai api_key your-api-key
epwn config set openai model gpt-4
```

#### Reset and Delete Configuration

```bash
# Reset to default configuration
epwn config reset

# Delete all configuration
epwn config delete
```

### 2. GLIBC Version Management (glibc)

GLIBC version management is one of EPwn's core features for managing different versions of GLIBC.

#### View Installed Versions

```bash
epwn glibc show
```

Displays all installed GLIBC versions, including:
- Version number
- libc path
- Debug symbols path
- Source code path
- Installation time

#### View Specific Version Details

```bash
epwn glibc info 2.27
```

#### Install GLIBC

```bash
# Install specific version
epwn glibc install --version 2.27

# Install with debug symbols
epwn glibc install --version 2.27 -p libc6 -p libc6-dbg

# Install source code
epwn glibc install --version 2.27 -p glibc-source

# Force reinstallation
epwn glibc install --version 2.27 --force

# Install multiple versions
epwn glibc install --nums 3  # Keep 3 latest subversions for each major version
```

#### Clean GLIBC

```bash
# Clean all versions
epwn glibc clean

# Force clean
epwn glibc clean --force
```

### 3. ELF Patching (patch)

The ELF patching feature is used to fix GLIBC dependencies in ELF files.

#### Manual Version Selection

```bash
# Create backup and patch
epwn patch choose your_binary

# Patch without backup
epwn patch choose your_binary --no-backup
```

#### Automatic Fixing

```bash
# Automatically fix based on provided libc file
epwn patch auto your_binary path/to/libc.so.6

# Download debug symbols simultaneously
epwn patch auto your_binary path/to/libc.so.6 -p libc6 -p libc6-dbg
```

### 4. PWN Script Generation (script)

The PWN script generation feature helps automate the creation of exploit scripts.

#### Automatic Script Generation

```bash
# Basic usage
epwn script auto ./vuln exploit.py

# Use template
epwn script auto ./vuln exploit.py -t template.py

# Provide additional hints
epwn script auto ./vuln exploit.py -p "Watch out for integer overflow"
```

#### Interactive Recording

```bash
# Record interactions and generate script
epwn script record ./vuln exploit.py

# Record with template
epwn script record ./vuln exploit.py -t template.py
```

## Best Practices

### GLIBC Management Best Practices

1. Keep multiple subversions for each major version
2. Install debug symbols for important CTF environments
3. Install source packages when deep analysis is needed

### ELF Patching Best Practices

1. Always use the --backup option to create backups
2. Prefer auto mode to let the tool choose appropriate versions
3. Use choose mode manually for special cases

### Script Generation Best Practices

1. Use templates to maintain consistent script style
2. Provide additional vulnerability information through prompts
3. Use record mode for complex programs that require manual exploration

## Common Issues

1. Configuration File Location
   - Default location: `~/.local/share/epwn/`
   - Can be modified via `config set`

2. GLIBC Version Compatibility
   - Backward compatible: Higher GLIBC versions can usually run programs compiled with lower versions
   - Not forward compatible: Lower GLIBC versions may not run programs compiled with higher versions

3. Patch Failure Handling
   - Check if GLIBC version is correct
   - Verify ELF file architecture matches
   - Restore from backup file

## Contributing

Pull Requests and Issues are welcome! Before submitting, please ensure:

1. Code follows PEP 8 style guide
2. Necessary test cases are added
3. Documentation is updated

## Feedback

If you encounter any issues while using EPwn, you can provide feedback through:

- GitHub Issues: https://github.com/GeekCmore/epwn/issues
- Project Homepage: https://github.com/GeekCmore/epwn

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

Thanks to all developers who have contributed to this project!

## Development Status

Current Version: 0.1.0 (Beta)

This project is under active development. Feedback and suggestions are welcome.