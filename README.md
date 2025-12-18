# Codey: Local AI Coding Assistant

Codey is a modular, local AI coding assistant designed to help developers with tasks ranging from file manipulation and git operations to autonomous planning and debugging. It leverages `llama.cpp` for local inference, ensuring privacy and offline capability, with optional hybrid reasoning via the Perplexity API.

**Note:** This project includes optimizations specifically tuned for the Samsung S24 Ultra (Snapdragon 8 Gen 3), but is compatible with standard Linux/PC environments.

## 🚀 Features

*   **Interactive CLI**: A rich terminal interface with colored output and command history.
*   **Autonomous Planning**: Breaks down complex, multi-step instructions into executable plans.
*   **Local Intelligence**: Uses GGUF models via `llama.cpp` for code generation and analysis.
*   **Hybrid Reasoning**: Optional integration with Perplexity API for research-backed coding.
*   **File Management**: Safe create, read, update, and delete operations with automatic backups.
*   **Git Integration**: Built-in support for cloning, status, committing, pushing, and pulling.
*   **Shell Integration**: Can execute shell commands, manage dependencies, and run scripts.
*   **Safety First**: `PermissionManager` ensures user approval for all file system and shell changes.
*   **Debugging**: Basic static analysis and auto-fix capabilities.

## 🛠️ Installation & Setup

### Prerequisites
*   Python 3.8 or higher
*   `git`
*   A GGUF format LLM (e.g., Llama 3, Mistral)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/codey.git
    cd codey
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: `llama-cpp-python` installation may require specific compilation flags depending on your hardware (CUDA, Metal, etc.).*

3.  **Configuration:**
    *   Copy `config.example.json` to `config.json` (if it exists) or create a new one.
    *   Set the `model_path` in `config.json` to point to your local GGUF model.
    *   (Optional) Add your Perplexity API key for hybrid mode.

## 📖 Usage

Start the interactive CLI:

```bash
python -m cli.main
```
*Or depending on the entry point configuration:*
```bash
./codey
```

### Common Commands

*   **File Operations:**
    *   `create file.py that prints hello world`
    *   `edit main.py to add a new function`
    *   `read utils.py`
    *   `delete temp.log`
*   **Git:**
    *   `git status`
    *   `commit "Updated README"`
    *   `push origin main`
*   **Planning:**
    *   `plan Create a fastAPI backend with a user route`
    *   `execute plan`
    *   `show plan`
*   **Debugging:**
    *   `debug script.py`
    *   `debug fix script.py`
*   **Research:**
    *   `ask What is the best way to handle async in Python?`

## 🏗️ Architecture

Codey follows a Manager-Agent architecture:

*   **Engine (`CodeyEngineV2`)**: Orchestrates the system, routing commands to appropriate agents.
*   **Agents**:
    *   `CodingAgent`: Handles code generation and modification.
    *   `DebugAgent`: Performs static analysis and auto-fixes.
    *   `TodoPlanner`: Manages task breakdown and execution.
*   **Managers**:
    *   `ModelManager`: Handles LLM loading and inference (optimized for specific hardware).
    *   `GitManager`: Wraps Git CLI operations.
    *   `ShellManager`: Handles system commands and package installation.
    *   `PermissionManager`: Enforces user consent.

## ⚠️ Current Limitations

*   **Static Analysis**: Currently limited to basic syntax checks; unused import detection is a placeholder.
*   **File Editing**: Rewrites entire files rather than applying patches, which may be slow for large files.
*   **Parser**: Relies heavily on regex, which can be brittle with complex natural language.

## 📄 License

[License Name/Type] - See LICENSE file for details.