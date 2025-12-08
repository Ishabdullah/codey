# NOTICE
This repository is now private and proprietary while we prepare commercial launch.
All code and assets are © 2025 Ishabdullah — all rights reserved.

# Codey - Claude Code Edition

**A production-grade local AI coding assistant with Claude Code-like capabilities**

Codey is a fully-featured AI coding assistant that runs locally on your Android S24 Ultra using CodeLlama-7B-Instruct. It combines the power of local GGUF models with optional Perplexity API integration, providing intelligent code generation, Git integration, shell command execution, and autonomous task planning - all with comprehensive permission management.

---

## 🚀 Key Features

### **Claude Code-Like Capabilities**
- **Permission-First Design**: Every operation requires explicit user approval
- **Natural Language Interface**: Interact with code using plain English
- **Git Integration**: Clone, commit, push, pull - all with confirmations
- **Shell Command Execution**: Safe command execution with permission checks
- **Dependency Management**: Install packages with approval
- **Directory Management**: Create and manage directories safely

### **Core AI Features**
- **Intelligent Code Generation**: Creates and edits code based on natural language
- **Hybrid Reasoning**: Combines local LLM with Perplexity API for best results
- **Autonomous Task Planning**: Breaks complex tasks into executable steps
- **Advanced Debugging**: Analyze and auto-fix code issues
- **Context Awareness**: Maintains conversation history and file context
- **Multi-Language Support**: Python, JavaScript, Java, C++, Go, and more

### **Optimized for S24 Ultra**
- **Full Context Window**: 16,384 tokens (CodeLlama's full capacity)
- **GPU Acceleration**: 35 layers offloaded to Adreno 750 GPU
- **CPU Optimization**: 6 threads utilizing Snapdragon 8 Gen 3 performance cores
- **Memory Efficient**: Memory-mapped loading for mobile optimization

---

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Natural Language Commands](#natural-language-commands)
- [Git Operations](#git-operations)
- [Shell Operations](#shell-operations)
- [File Operations](#file-operations)
- [Advanced Features](#advanced-features)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Installation

### Prerequisites

- **Termux** (Android terminal emulator)
- **Python 3.8+** (included in Termux)
- **Git** (for version control operations)
- **4GB+ RAM** recommended for optimal performance

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/codey.git
cd codey
```

### Step 2: Install Dependencies

```bash
# Update packages
pkg update && pkg upgrade

# Install system dependencies
pkg install python git clang

# Install Python packages
pip install -r requirements.txt
```

The main dependency is `llama-cpp-python` for running GGUF models.

### Step 3: Download Model

The repository includes CodeLlama-7B-Instruct.Q4_K_M.gguf in `LLM_Models/`. If you need to download it manually:

```bash
cd LLM_Models
# Download your preferred GGUF model
# Recommended: CodeLlama-7B-Instruct.Q4_K_M.gguf
```

**Model Sources:**
- [TheBloke on HuggingFace](https://huggingface.co/TheBloke)
- [llama.cpp models](https://huggingface.co/models?search=gguf)

### Step 4: Configure (Optional)

Edit `config.json` to customize:
- Model paths
- GPU/CPU settings
- Perplexity API key (optional)
- Workspace directory

### Step 5: Make Executable

```bash
chmod +x codey
```

### Step 6: Run Codey

```bash
./codey
```

---

## ⚡ Quick Start

### First Run

```bash
./codey
```

You'll see the initialization screen:

```
╔═══════════════════════════════════════════════╗
║                CODEY                          ║
║  Local AI Coding Assistant                   ║
║  Claude Code Edition                          ║
╚═══════════════════════════════════════════════╝

Loading model from LLM_Models/CodeLlama-7B-Instruct.Q4_K_M.gguf...
Optimizing for S24 Ultra (GPU + NPU acceleration)...
Auto-detected GPU: offloading 35 layers to GPU
Model loaded successfully!
Context window: 16384 tokens
GPU layers: 35
CPU threads: 6

✓ Codey initialized - Claude Code Edition
✓ Context: 16384 tokens
✓ GPU layers: 35
✓ Git enabled: True
✓ Shell enabled: True

Ready! Type 'help' for commands or start coding.

codey>
```

### Your First Commands

```bash
codey> create hello.py that prints "Hello, World!"
```

Codey will generate the code, show you a preview, and ask for permission:

```
🔒 Permission required: Create file?
   Filename: hello.py
   Preview:
     print("Hello, World!")

   Proceed? [y/n]: y

✓ Created hello.py
```

---

## 💬 Natural Language Commands

Codey understands natural language. Here are examples:

### File Creation

```bash
# Simple file
codey> create hello.py that prints hello world

# Complex file
codey> create api_client.py with REST API functions for user authentication

# With specific requirements
codey> create server.py that implements a Flask REST API with JWT authentication
```

### File Editing

```bash
# Simple edit
codey> edit hello.py to also print the current date

# Complex edit
codey> edit server.py to add error handling and logging

# Refactoring
codey> refactor utils.py to use async/await
```

### Code Understanding

```bash
# Explain code
codey> explain what hello.py does

# Ask questions
codey> what libraries are used in api_client.py?

# Get suggestions
codey> ask What's the best way to handle database connections in Python?
```

---

## 🔀 Git Operations

All Git operations require explicit permission.

### Clone Repository

```bash
codey> clone https://github.com/user/repo my_project

🔒 Permission required: Clone repository?
   Repository: https://github.com/user/repo
   Destination: /data/data/com.termux/files/home/codey/workspace/my_project

   Proceed? [y/n]: y

✓ Successfully cloned to workspace/my_project
```

### Check Status

```bash
codey> git status

Git status:

Staged (2):
  + src/main.py
  + README.md

Modified (1):
  M config.json

Untracked (3):
  ? test.py
  ? .env
  ? backup/
```

### Commit Changes

```bash
codey> commit with message "Add authentication feature"

🔒 Permission required: Create git commit?
   Message: "Add authentication feature"
   Files: 5 file(s)
     - src/auth.py
     - src/models.py
     - README.md
     - requirements.txt
     - config.json

   Proceed? [y/n]: y

✓ Committed 5 file(s): Add authentication feature
```

### Push to Remote

```bash
codey> push origin main

🔒 Permission required: Push to remote repository?
   Remote: origin
   Branch: main
   ⚠️  This will modify the remote repository!

   Proceed? [y/n]: y

✓ Pushed to origin/main
```

### Pull from Remote

```bash
codey> pull

✓ Pulled from origin/main
Already up to date.
```

### Initialize Repository

```bash
codey> git init

✓ Initialized git repository at /data/data/com.termux/files/home/codey/workspace
```

---

## 🖥️ Shell Operations

Execute shell commands and manage dependencies with permission checks.

### Install Dependencies

```bash
codey> install requirements.txt

🔒 Permission required: Install Python packages?
   From: requirements.txt
   Packages: 15 package(s)
     - flask
     - requests
     - sqlalchemy
     - pydantic
     - pytest
     ... and 10 more

   Proceed? [y/n]: y

✓ Installation completed
```

### Install Single Package

```bash
codey> install numpy

🔒 Permission required: Install Python packages?
   Packages: 1 package(s)
     - numpy

   Proceed? [y/n]: y

✓ Installation completed
```

### Create Directory

```bash
codey> mkdir src/models

🔒 Permission required: Create directory?
   Directory: workspace/src/models

   Proceed? [y/n]: y

✓ Created directory: workspace/src/models
```

### Run Python File

```bash
codey> run test.py

🔒 Permission required: Execute shell command?
   Command: python workspace/test.py
   Purpose: Run Python script: test.py

   Proceed? [y/n]: y

✓ Executed test.py

Output:
All tests passed!
3 tests run, 0 failures
```

### Execute Shell Command

```bash
codey> execute ls -la

🔒 Permission required: Execute shell command?
   Command: ls -la
   Purpose: Execute: ls

   Proceed? [y/n]: y

✓ Command executed

Output:
total 48
drwx------. 2 u0_a644 u0_a644 3452 Dec  4 06:00 .
drwx------. 8 u0_a644 u0_a644 3452 Dec  4 05:00 ..
-rw-------.  1 u0_a644 u0_a644  543 Dec  4 06:00 hello.py
-rw-------.  1 u0_a644 u0_a644 1234 Dec  4 05:55 server.py
```

---

## 📁 File Operations

### Create Files

```bash
codey> create app.py with a Flask web server

🔒 Permission required: Create file?
   Filename: app.py
   Preview:
     from flask import Flask, jsonify

     app = Flask(__name__)

     @app.route('/')
     def index():
         return jsonify({"message": "Hello, World!"})

     if __name__ == '__main__':
         app.run(debug=True)

   Proceed? [y/n]: y

✓ Created app.py
```

### Edit Files

```bash
codey> edit app.py to add error handling

🔒 Permission required: Edit file?
   Filename: app.py
   Backup will be created: logs/backups/app.py.bak
   Preview:
     [Shows edited code...]

   Proceed? [y/n]: y

✓ Updated app.py
(Backup: logs/backups/app.py.2024-12-04_06-30-15.bak)
```

### Read Files

```bash
codey> read config.json

Contents of config.json:

{
  "model_dir": "/data/data/com.termux/files/home/codey/LLM_Models",
  "context_size": 16384,
  ...
}
```

### Delete Files

```bash
codey> delete old_test.py

🔒 Permission required: Delete file?
   Filename: old_test.py
   Backup will be created: logs/backups/old_test.py.bak
   ⚠️  This action cannot be easily undone!

   Proceed? [y/n]: y

✓ Deleted old_test.py
(Backup: logs/backups/old_test.py.2024-12-04_06-35-22.bak)
```

### List Files

```bash
codey> list files

Files in workspace:
  - hello.py
  - app.py
  - server.py
  - config.json
  - requirements.txt
```

---

## 🎯 Advanced Features

### Autonomous Task Planning

Break complex tasks into executable steps:

```bash
codey> plan Implement a REST API with user authentication and database

Creating plan...
Created plan with 6 tasks:

1. research: Best Python REST API frameworks and auth patterns
2. create src/database.py: Database connection and models
3. create src/auth.py: JWT authentication implementation
4. create src/api.py: REST API endpoints
5. create tests/test_auth.py: Authentication unit tests
6. edit README.md: Add API documentation

(Plan enhanced with Perplexity research)
Use 'execute plan' to run automatically or handle tasks manually.
```

Execute the plan autonomously:

```bash
codey> execute plan

Executing plan with 6 tasks...

Task 1/6: Best Python REST API frameworks and auth patterns
  ✓ Completed

Task 2/6: Database connection and models
  🔒 Permission required: Create file?
     ...
  ✓ Completed

Task 3/6: JWT authentication implementation
  🔒 Permission required: Create file?
     ...
  ✓ Completed

...

Plan execution complete!
```

### Advanced Debugging

```bash
codey> debug server.py

Analyzing server.py...
Found 3 issue(s):

  [MEDIUM] (line 45) Bare except clause - should specify exception type
  [LOW] (line 12) Debug print statement found
  [LOW] (line 78) TODO comment

codey> debug fix server.py

[Analyzing with Perplexity]

🔒 Permission required: Edit file?
   Filename: server.py
   ...

Applied 3 fixes to server.py
Backup: logs/backups/server.py.20241204_143022.bak
```

### Hybrid Reasoning Mode

Codey automatically uses Perplexity for complex tasks:

```bash
codey> create oauth_client.py with OAuth2 implementation and best practices

[Hybrid Mode] Consulting Perplexity for best practices...
[Hybrid Mode] Received Perplexity suggestion

🔒 Permission required: Create file?
   Filename: oauth_client.py
   Preview:
     [Shows OAuth2 implementation with best practices from Perplexity]

✓ Created oauth_client.py (with Perplexity assistance)
```

### Direct Perplexity Queries

```bash
codey> ask What's the best way to handle async database connections in Python?

Asking Perplexity...

[Detailed expert response about async database patterns in Python, including:
- asyncio and aiopg/aiomysql
- Connection pooling best practices
- Error handling patterns
- Example code implementations]
```

### System Information

```bash
codey> info

System Information:

Model:
  Path: LLM_Models/CodeLlama-7B-Instruct.Q4_K_M.gguf
  Context: 16384 tokens
  GPU layers: 35
  CPU threads: 6
  Batch size: 512

System:
  Python: Python 3.11.6
  Pip: pip 23.3.1
  Git: ✓
  NPM: ✗

Workspace: /data/data/com.termux/files/home/codey/workspace
```

---

## ⚙️ Configuration

Edit `config.json` to customize Codey:

```json
{
  "model_dir": "/data/data/com.termux/files/home/codey/LLM_Models",
  "model_name": "CodeLlama-7B-Instruct.Q4_K_M.gguf",
  "workspace_dir": "/data/data/com.termux/files/home/codey/workspace",

  "context_size": 16384,
  "n_gpu_layers": 35,
  "n_threads": 6,
  "n_threads_batch": 6,
  "temperature": 0.3,
  "max_tokens": 2048,

  "require_confirmation": true,
  "backup_before_edit": true,
  "auto_backup": true,

  "perplexity_api_key": "",
  "use_perplexity": true,
  "hybrid_mode": true,

  "git_enabled": true,
  "shell_enabled": true
}
```

### Configuration Options

#### Model Settings
- **model_name**: GGUF model filename
- **model_dir**: Directory containing models
- **context_size**: Context window (16384 for CodeLlama)
- **n_gpu_layers**: GPU acceleration (35 for S24 Ultra with 7B model)
- **n_threads**: CPU threads (6 recommended for Snapdragon 8 Gen 3)
- **temperature**: 0.0-1.0 (lower = more deterministic)
- **max_tokens**: Maximum response length

#### Perplexity Settings
- **perplexity_api_key**: Your Perplexity API key
- **use_perplexity**: Enable/disable Perplexity integration
- **hybrid_mode**: Auto-select local vs. Perplexity based on task

#### Safety Settings
- **require_confirmation**: Show permission prompts (recommended: true)
- **backup_before_edit**: Create backups before modifications
- **auto_backup**: Automatic backup system

#### Feature Toggles
- **git_enabled**: Enable Git operations
- **shell_enabled**: Enable shell command execution

---

## 🏗️ Architecture

```
codey/
├── core/                    # Core engine and managers
│   ├── engine_v2.py         # Main orchestration engine
│   ├── parser.py            # Natural language parser
│   ├── tools.py             # File operation tools
│   ├── permission_manager.py # Permission system
│   ├── git_manager.py       # Git operations
│   └── shell_manager.py     # Shell command execution
│
├── models/                  # Model management
│   └── manager.py           # Optimized model loader
│
├── agents/                  # Specialized AI agents
│   ├── coding_agent.py      # Code generation
│   ├── debug_agent.py       # Debugging and analysis
│   ├── todo_planner.py      # Task planning
│   └── perplexity_api.py    # Perplexity integration
│
├── cli/                     # Command-line interface
│   └── main.py              # Interactive CLI
│
├── utils/                   # Utilities
│   └── config.py            # Configuration management
│
├── memory/                  # Persistent storage
│   ├── store.py             # Context and memory
│   ├── memory.json          # Conversation history
│   └── todos.json           # Task tracking
│
├── LLM_Models/              # GGUF model storage
│   └── CodeLlama-7B-Instruct.Q4_K_M.gguf
│
├── workspace/               # Your code files
├── logs/                    # Logs and backups
├── config.json              # Configuration
└── codey                    # Main executable
```

### Key Components

1. **Permission Manager**: Handles all user approval requests
2. **Git Manager**: Safe Git operations with confirmations
3. **Shell Manager**: Secure shell command execution
4. **Model Manager**: Optimized GGUF model loading for S24 Ultra
5. **Coding Agent**: Intelligent code generation and editing
6. **Todo Planner**: Autonomous task breakdown and execution
7. **Debug Agent**: Code analysis and auto-fixing

---

## 🔍 Troubleshooting

### Model Not Loading

**Error**: `Model not found`

**Solution**:
```bash
# Check model path
ls LLM_Models/

# Update config.json with correct path
```

### Out of Memory

**Error**: `RuntimeError: Failed to load model`

**Solutions**:
1. Reduce `context_size` in config.json (try 8192)
2. Reduce `n_gpu_layers` (try 20-25)
3. Use a smaller model (use Q3 quantization instead of Q4)

### Permission Errors

**Error**: `Permission denied by user`

**This is normal!** Codey asks permission before all operations. To proceed:
- Answer `y` or `yes` to approve
- Answer `n` or `no` to cancel

### Git Operations Failing

**Error**: `Git is not installed`

**Solution**:
```bash
pkg install git
```

### Slow Performance

**Solutions**:
1. Increase `n_gpu_layers` in config.json (up to 35 for 7B models)
2. Ensure you're using Q4 or Q3 quantization
3. Reduce `context_size` if needed
4. Close other apps to free RAM

### Import Errors

**Error**: `ImportError: No module named 'llama_cpp'`

**Solution**:
```bash
pip install llama-cpp-python
```

---

## 📚 Advanced Usage

### Batch Operations

For multiple file operations, Codey supports batch approval:

```bash
codey> create multiple test files

🔒 Permission required: Batch operation
   Operation: Create multiple files
   Count: 5 operations

   Options:
     y - Approve all (auto-approve mode)
     a - Ask for each operation individually
     n - Cancel

   Choice [y/a/n]: y

⚠️  Auto-approval enabled. All operations will proceed without confirmation.
```

### Custom Workflows

Combine commands for custom workflows:

```bash
# 1. Clone repo
codey> clone https://github.com/user/project

# 2. Install dependencies
codey> install requirements.txt

# 3. Run tests
codey> run tests/test_all.py

# 4. Make changes
codey> edit src/main.py to add new feature

# 5. Commit and push
codey> commit with message "Add new feature"
codey> push
```

---

## 🔐 Security Best Practices

1. **API Keys**: Never commit API keys to Git. Add them locally after cloning.
2. **Permissions**: Always review permission prompts carefully
3. **Backups**: Keep `backup_before_edit: true` enabled
4. **Dangerous Commands**: Codey warns about potentially dangerous shell commands
5. **Code Review**: Always review generated code before running

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Credits

- Built with [llama.cpp](https://github.com/ggerganov/llama.cpp)
- Inspired by [Claude Code](https://claude.com/claude-code) and Anthropic's AI assistants
- Models from the open-source AI community
- Optimized for Samsung Galaxy S24 Ultra

---

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the troubleshooting section
- Review configuration options

---

## 🎯 Version

**Current version: 2.0.0 - Claude Code Edition**

### What's New in 2.0:
- ✅ Full permission system for all operations
- ✅ Git integration (clone, commit, push, pull)
- ✅ Shell command execution with safety checks
- ✅ Optimized for S24 Ultra (16K context, 35 GPU layers)
- ✅ Enhanced natural language understanding
- ✅ Comprehensive backup system
- ✅ Batch operation support
- ✅ System information display

---

**Happy Coding with Codey!** 🚀

---

## 🎮 GPU Acceleration (NEW!)

**Status:** ✅ GPU build completed successfully!

Codey now has GPU acceleration support built using OpenCL for the Adreno 750 GPU on Samsung S24 Ultra.

### GPU Build Details
- **Backend:** OpenCL with Adreno-optimized kernels
- **GPU:** QUALCOMM Adreno 750 (Snapdragon 8 Gen 3)
- **Performance:** 3-5x faster than CPU-only (expected)
- **Documentation:** See `GPU_BUILD_GUIDE.md` for complete details

### Quick Test
```bash
export LD_LIBRARY_PATH=/vendor/lib64:$LD_LIBRARY_PATH
~/llama.cpp/build-android/bin/llama-cli \
  -m ~/codey/LLM_Models/CodeLlama-7B-Instruct.Q4_K_M.gguf \
  -ngl 35 --verbose
```

Look for "offloaded X/Y layers to GPU" in the output.

### Features Added
- ✅ **GPU-Accelerated llama.cpp**: Built with OpenCL + Adreno optimization
- ✅ **Automatic Cleanup**: Junk files removed on exit
- ✅ **Optimized Configuration**: Reduced context for faster inference
- ✅ **Comprehensive Docs**: Step-by-step build guide included

**Read `GPU_BUILD_GUIDE.md` for full setup instructions and `GPU_BUILD_SUCCESS.md` for build summary.**

