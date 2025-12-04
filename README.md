# Codey - Advanced Local AI Coding Assistant

A production-grade local AI coding assistant with hybrid reasoning capabilities. Codey combines local GGUF models (llama.cpp) with Perplexity API for enhanced intelligence, autonomous task execution, and advanced debugging.

## Features

### Core Capabilities
- **Natural Language Interface**: Just tell Codey what you want in plain English
- **Intelligent Code Generation**: Creates and edits code based on your instructions
- **File Management**: Safe file operations with automatic backups
- **Context Awareness**: Remembers your work and maintains conversation history
- **Multi-Language Support**: Python, JavaScript, Java, C++, Go, and more
- **Safety Built-in**: Confirmation prompts and automatic backups

### Advanced Features
- **Hybrid Reasoning**: Automatically uses local LLM or Perplexity based on task complexity
- **Perplexity Integration**: Access deep knowledge, debugging patterns, and real-world solutions
- **Autonomous Task Planning**: Breaks complex requests into structured, executable todo lists
- **Auto-Execution**: Execute multi-step plans automatically with progress tracking
- **Advanced Debugging**: Analyze, detect, and auto-fix issues in your code
- **Multi-File Operations**: Handle complex changes across multiple files
- **Research Mode**: Query Perplexity for libraries, best practices, and solutions
- **Intelligent Decision Making**: Knows when to use local vs. online resources

## Architecture

```
codey/
├── core/              # Main engine and orchestration
│   ├── engine.py      # Central coordinator
│   ├── parser.py      # Natural language command parser
│   └── tools.py       # File operation tools
├── models/            # Model management
│   └── manager.py     # llama.cpp model loader
├── agents/            # Specialized AI agents
│   └── coding_agent.py  # Code generation agent
├── cli/               # Command-line interface
│   └── main.py        # Interactive CLI
├── utils/             # Utilities
│   └── config.py      # Configuration management
├── memory/            # Persistent storage
│   └── store.py       # Memory and context persistence
├── LLM_Models/        # GGUF model storage
├── workspace/         # Your code files (created on first run)
└── codey              # Main executable
```

## Installation

### Prerequisites

1. **Python 3.8+** (Termux includes Python)
2. **pip** (Python package manager)
3. **GGUF Model** (e.g., CodeLlama, DeepSeek Coder, etc.)

### Step 1: Install Dependencies

On Termux:
```bash
# Update packages
pkg update && pkg upgrade

# Install Python if not already installed
pkg install python

# Install build dependencies for llama-cpp-python
pkg install clang python-numpy

# Install required packages
pip install llama-cpp-python

# Note: No additional packages needed - Perplexity uses urllib (built-in)
```

Or use requirements.txt:
```bash
pip install -r requirements.txt
```

### Step 2: Download a GGUF Model

Place your GGUF model file in the `LLM_Models/` directory.

**Recommended models:**
- CodeLlama-7B-Instruct.Q4_K_M.gguf (included)
- DeepSeek-Coder-6.7B-Instruct.Q4_K_M.gguf
- Mistral-7B-Instruct.Q4_K_M.gguf

**Where to get models:**
- [TheBloke on HuggingFace](https://huggingface.co/TheBloke)
- [llama.cpp compatible models](https://huggingface.co/models?search=gguf)

### Step 3: Configure (Optional)

Edit `config.json` to customize settings:
- Model configuration
- Perplexity API settings
- Workspace directory
- Safety and behavior settings

The config file is automatically created on first run with defaults.

### Step 4: Make Executable

```bash
chmod +x codey
```

### Step 5: Add to PATH (Optional)

Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export PATH="$HOME/codey:$PATH"
```

Then reload:
```bash
source ~/.bashrc
```

## Usage

### Starting Codey

From the codey directory:
```bash
./codey
```

Or if added to PATH:
```bash
codey
```

### Example Interactions

#### Basic File Operations
```
codey> create hello.py that prints "Hello, World!"
Created hello.py

codey> edit hello.py to also print the current date
Updated hello.py

codey> read config.py
[displays file contents]

codey> list files
Files in workspace: hello.py, config.py, server.py

codey> delete old_code.py
Deleted old_code.py (backed up)
```

#### Hybrid Reasoning Mode
```
codey> create api_client.py that implements OAuth2 authentication with best practices
[Hybrid Mode] Consulting Perplexity for best practices...
[Hybrid Mode] Received Perplexity suggestion
Created api_client.py (with Perplexity assistance)
```

#### Autonomous Task Planning
```
codey> plan Add the ability for the system to scan the top 10 fastest moving stocks and create a list
Creating plan...
Created plan with 5 tasks:

1. research: Best Python stock APIs
2. create utils/stock_api.py: API client for stock data
3. create services/stock_scanner.py: Stock scanning and sorting logic
4. edit main.py: Add stock scanning function and CLI command
5. create tests/test_stock_scanner.py: Unit tests for scanner

(Plan enhanced with Perplexity research)
Use 'execute plan' to run automatically or handle tasks manually.

codey> execute plan
Executing plan with 5 tasks...
Task 1/5: Best Python stock APIs
  ✓ Completed
Task 2/5: API client for stock data
  ✓ Completed
...
Plan execution complete!
```

#### Advanced Debugging
```
codey> debug server.py
Analyzing server.py...
Found 3 issue(s):
  [MEDIUM] (line 45) Bare except clause - should specify exception type
  [LOW] (line 12) Debug print statement found
  [LOW] (line 78) TODO comment

codey> debug fix server.py
[Analyzing with Perplexity]
Applied 3 fixes to server.py
Backup: logs/backups/server.py.20231204_143022.bak
```

#### Direct Perplexity Queries
```
codey> ask What's the best way to handle async database connections in Python?
Asking Perplexity...
[Detailed response with modern best practices...]

codey> ask How do I implement rate limiting for an API?
[Expert guidance from Perplexity...]
```

#### Complex Feature Requests
```
codey> Add JWT authentication to the FastAPI application with refresh tokens
[Hybrid Mode] Consulting Perplexity for JWT best practices...
Created auth/jwt_handler.py (with Perplexity assistance)
Updated main.py with authentication middleware
Created auth/models.py for token models
```

### Commands

#### Basic Commands
| Command | Description | Example |
|---------|-------------|---------|
| `create <file> <description>` | Create a new file | `create app.py with a Flask web server` |
| `edit <file> <changes>` | Edit existing file | `edit app.py to add authentication` |
| `read <file>` | Display file contents | `read config.json` |
| `delete <file>` | Delete a file | `delete test.py` |
| `list files` | List workspace files | `list files` |

#### Advanced Commands
| Command | Description | Example |
|---------|-------------|---------|
| `plan <task>` | Create autonomous task plan | `plan Implement user authentication system` |
| `execute plan` | Run current plan autonomously | `execute plan` |
| `show plan` | Display current plan status | `show plan` |
| `debug <file>` | Analyze file for issues | `debug server.py` |
| `debug fix <file>` | Auto-fix issues | `debug fix server.py` |
| `ask <question>` | Query Perplexity directly | `ask Best Python logging practices` |

#### System Commands
| Command | Description |
|---------|-------------|
| `help` | Show help |
| `clear` | Clear screen |
| `exit` | Exit Codey |

### Natural Language Understanding

Codey has advanced natural language understanding:

**Simple requests:**
- "write a function to sort a list"
- "add comments to my code"
- "what does this code do?"

**Complex requests:**
- "Implement a caching layer with Redis for the API endpoints"
- "Add WebSocket support with authentication and real-time updates"
- "Create a microservice for processing payments with Stripe"
- "Refactor the database layer to use async SQLAlchemy"

**Research requests:**
- "What's the best approach for handling file uploads in FastAPI?"
- "How should I structure a large Python project?"
- "What libraries should I use for machine learning?"

## Configuration

Edit `config.json` in the codey directory:

```json
{
  "model_dir": "/path/to/LLM_Models",
  "model_name": "CodeLlama-7B-Instruct.Q4_K_M.gguf",
  "workspace_dir": "/path/to/workspace",
  "temperature": 0.3,
  "max_tokens": 2048,
  "context_size": 4096,
  "n_gpu_layers": 0,
  "require_confirmation": true,
  "backup_before_edit": true,
  "perplexity_api_key": "your-api-key-here",
  "use_perplexity": true,
  "hybrid_mode": true
}
```

### Configuration Options

#### Model Settings
- `model_name`: GGUF model filename
- `model_dir`: Directory containing models
- `temperature`: 0.0-1.0 (lower = more deterministic)
- `max_tokens`: Maximum response length
- `context_size`: Model context window
- `n_gpu_layers`: GPU layers (0 = CPU only)

#### Perplexity Settings
- `perplexity_api_key`: Your Perplexity API key ([get one here](https://www.perplexity.ai/))
- `use_perplexity`: Enable/disable Perplexity integration
- `hybrid_mode`: Automatically choose local vs. Perplexity based on task complexity

#### Safety Settings
- `require_confirmation`: Show previews before saving
- `backup_before_edit`: Auto-backup before edits
- `workspace_dir`: Where to store generated files

### Hybrid Mode

When `hybrid_mode` is enabled, Codey automatically decides when to use:
- **Local LLM**: For fast, straightforward code generation and edits
- **Perplexity**: For complex tasks requiring research, best practices, or deep knowledge

Hybrid indicators (automatic Perplexity use):
- "best way", "how to", "implement", "design pattern"
- API integration tasks
- Security/authentication requests
- Performance optimization
- Framework/library selection

## Safety Features

1. **Automatic Backups**: Files are backed up before edits
2. **Confirmation Prompts**: Optional confirmation for destructive operations
3. **Preview Mode**: See generated code before saving
4. **Workspace Isolation**: All files contained in workspace directory
5. **Error Handling**: Graceful error recovery

## Performance Tips

1. **Use appropriate model size**: Smaller models (7B) run faster
2. **Adjust temperature**: Lower temperature (0.2-0.4) for code generation
3. **Set context_size wisely**: Smaller context = faster inference
4. **Use Q4 quantization**: Good balance of quality and speed

## Troubleshooting

### Model not loading
```
Error: Model not found
```
**Solution**: Ensure GGUF model is in `LLM_Models/` directory and `config.json` has correct path.

### Out of memory
```
RuntimeError: Failed to load model
```
**Solution**: Use a smaller model or reduce `context_size` in config.

### Import errors
```
ImportError: No module named 'llama_cpp'
```
**Solution**: Install llama-cpp-python:
```bash
pip install llama-cpp-python
```

### Slow responses
**Solution**:
- Use smaller model (7B instead of 13B)
- Reduce `max_tokens`
- Lower `context_size`

## Development

### Project Structure

- **core/**: Main application logic
- **models/**: Model loading and management
- **agents/**: AI agent implementations
- **cli/**: User interface
- **utils/**: Shared utilities
- **memory/**: Persistence layer

### Extending Codey

Add new agents in `agents/`:
```python
class MyAgent:
    def __init__(self, model_manager, file_tools, config):
        self.model = model_manager
        self.tools = file_tools
        self.config = config

    def do_something(self):
        # Your implementation
        pass
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Credits

- Built with [llama.cpp](https://github.com/ggerganov/llama.cpp)
- Inspired by Claude Code and other AI coding assistants
- Models from the open-source AI community

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting section

## Version

Current version: **1.0.0**

---

**Happy Coding with Codey!** 🚀
