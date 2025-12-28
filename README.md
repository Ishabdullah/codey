# Codey: The Local, CPU-Optimized AI Engineer

> **Version:** 3.0 (Audited)
> **Architecture:** Local Multi-Model Orchestration
> **Focus:** Privacy, Zero-Cloud Dependency, Efficiency

Codey is a command-line AI software engineer designed to run **entirely on your local machine**. Unlike cloud-based assistants that rely on massive server farms, Codey runs on standard consumer hardware, including high-end mobile devices via Termux or UserLAnd. It maintains complete data privacy by ensuring no code or telemetry ever leaves your machine.

---

## Design Philosophy

Codey is built upon three core principles regarding local AI execution:

1.  **CPU-First by Design:** Codey is not a GPU-native application that merely tolerates CPUs. It is engineered specifically for the latency and bandwidth constraints of system RAM and CPU inference.
2.  **Stability Over Speed:** On local hardware, aggressive resource usage leads to system instability. Codey strictly budgets memory and prioritizes system responsiveness over raw token generation speed.
3.  **Iterative Correctness:** Codey favors iterative improvement over one-shot generation. Given the constraints of 7B parameter models, reliability is achieved by breaking complex tasks into smaller, verifiable steps rather than attempting complex architecture in a single pass.

---

## Capability Reality Check

### What Codey Does
*   **Runs Locally:** Operates without API keys, monthly fees, or data egress.
*   **Edits Code:** Reads, analyzes, and modifies files directly in the workspace.
*   **Plans Tasks:** Decomposes complex instructions (e.g., "create a react app") into executable steps.
*   **Manages Git:** Handles commits, status checks, and history.
*   **Optimizes Resources:** Enforces strict RAM budgeting to prevent operating system slowdowns.

### What Codey Is Not
*   **Instant:** On a CPU, inference takes time. Generating a complex function requires patience (often 30-60 seconds).
*   **A Supercomputer:** It utilizes 7B parameter models. It is competent at junior-to-mid-level tasks but will not architect microservices backends in a single prompt.
*   **Magic:** It relies on clear instructions, established context, and iterative refinement.

### Self-Awareness Boundaries
Codey operates within strict confidence and capability limits. It is designed to:
*   Explicitly report when a task exceeds its context window or logical capabilities.
*   Treat guessing and hallucination as critical failures, not features.
*   Request narrower scope or clarification rather than attempting low-confidence generation.

---

## System Architecture

Codey uses a Split-Brain Architecture to balance latency and intelligence:

1.  **The Reflex Layer (Router):**
    *   **Model:** FunctionGemma 270M
    *   **Role:** Instantly classifies requests as simple tool commands, questions, or coding tasks.
    *   **Latency:** Sub-second.

2.  **The Deep Layer (Coder):**
    *   **Model:** Qwen2.5-Coder 7B
    *   **Role:** Handles complex code generation, refactoring, and logic.
    *   **Latency:** Loaded on-demand (5-30 seconds).

3.  **Lifecycle Manager:**
    *   Actively manages RAM. If a memory limit is set (e.g., 6GB), Codey ensures idle models are unloaded before new ones are initialized to maintain system stability.

## Tool Registry & Safety

Codey employs a strict tool execution policy to prevent hallucinated actions:

*   **Registry:** Only explicitly defined tools (`git`, `shell`, `file`) are executable.
*   **Safety Fallback:** If the Intent Router predicts a tool that doesn't exist (e.g., "tool: fix_code"), the system automatically intercepts this error and redirects the request to the general coding or Q&A path.
*   **Normalization:** Aliases are automatically mapped (e.g., "read" → "file", "terminal" → "shell") to handle natural language variations.

---

## Getting Started

### Prerequisites
*   **OS:** Linux / macOS / WSL2 / Android (Termux/UserLAnd)
*   **RAM:** 8GB minimum (16GB recommended)
*   **Storage:** ~10GB for models
*   **Python:** 3.10+

### Installation
```bash
# Clone the repository
git clone https://github.com/your-repo/codey.git
cd codey

# Install dependencies (incorporates hardware-specific builds)
pip install -r requirements.txt
```

### Getting Started Example: Mobile-First Demo

Codey has been validated to run end-to-end on high-end mobile devices (e.g., Samsung Galaxy S24 Ultra) via Termux or UserLAnd.

#### Termux Setup
To reproduce this demo on your Android device:

```bash
# 1. Install system dependencies
pkg update && pkg upgrade
pkg install python git clang make build-essential

# 2. Clone Codey
git clone https://github.com/your-repo/codey.git
cd codey

# 3. Install Python dependencies (compiles llama-cpp-python locally)
pip install -r requirements.txt

# 4. Launch Engine
python engine_v3.py
```

#### Example Command Run
**Device:** Samsung Galaxy S24 Ultra (Termux / UserLAnd)
**Prompt:** "Create Fibonacci function"

```text
~/codey$ python engine_v3.py
> Create Fibonacci function

📦 Loading model: Qwen2.5-Coder 7B...
✓ Loaded qwen2.5-coder-7b-instruct-q4_k_m.gguf
⚙️ Generating code...

def fibonacci(n):
    if n <= 0:
        return "Input should be a positive integer"
    elif n == 1:
        return 0
    elif n == 2:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n):
            a, b = b, a + b
        return b
```

This demo validates that Codey's split-brain architecture (Router + Coder) functions correctly on mobile ARM64 CPUs, effectively managing memory to load the 7B model on-demand.

![Codey Mobile Demo](Screenshot_20251228_025055_UserLAnd.jpg)

### Configuration
Codey auto-generates a `config.json` on first run. Key settings to tune:
*   `memory_budget_mb`: Set this to approximately 70% of available RAM.
*   `n_threads`: Set to the number of physical CPU cores.

---

## Usage

Start the engine:
```bash
python engine_v3.py
```

### Example Workflows

**1. Quick Tool Use (Fast)**
Codey executes these instantly using the Router.
```text
> git status
> create a directory named 'tests'
> read config.json
```

**2. Coding Tasks (Slower, Intelligent)**
Codey loads the 7B model. Expect a loading pause.
```text
> Create a Python script to scrape HackerNews headlines
> Refactor utils.py to use async/await
> Fix the bug in line 42 of main.py
```

**3. Multi-Step Planning**
Codey decomposes these into a sequence of actions.
```text
> Create a flask app structure and then write a hello world route
> 1. git pull 2. run tests 3. if pass, git push
```

## Performance Tuning

Running LLMs on CPU requires understanding the bottlenecks:

| Action | Time Cost | Explanation |
|---|---|---|
| **Routing** | < 1s | Small model, resident in memory. |
| **Model Loading** | 2-10s | Reading GBs from disk into RAM. Occurs when switching tasks. |
| **Generation** | 2-10 tok/s | Matrix multiplication on CPU is bandwidth-limited. |

**Recommendation:** Group similar tasks. Perform all coding tasks in sequence, then all git operations. This prevents "thrashing" (repeatedly loading/unloading models).

### Mobile Performance Notes (Validated on Samsung S24 Ultra)

Performance on mobile devices is constrained by thermal management and power limits. The following metrics were collected on a Samsung Galaxy S24 Ultra running Ubuntu inside UserLAnd.

```text
Test Device: Samsung Galaxy S24 Ultra
Environment: Ubuntu (UserLAnd)
Peak RAM Usage: 5229 MB
Model Load Time: 0.62 s (first coding task)
Generation Speed: 1.26 tok/s (Avg)
Observed Quirks:
 - CPU temperature ranged ~44-58°C during generation (normal thermal rise, no throttling observed)
 - Background apps may affect token generation speed
```

### Measurement Checklist (Internal)
For maintainers reproducing these metrics:
*   **RAM:** Use `benchmark_s24.py` (included in repo) or monitor `VmRSS` in `/proc/[pid]/status`.
*   **Load Time:** Calculated from the `model_load_ms` metric in `PerformanceTracker`.
*   **Speed:** Average `output_tokens / generation_ms` across 3 representative coding tasks.
*   **Thermals:** Subjective observation of device heat or CPU throttling flags.

---

## Tool Registry & Recommendations

Codey supports a variety of local tools to enhance your development workflow. These tools are executed directly on your machine, leveraging the OS capabilities.

| Category | Tool | Description | Example Usage |
| :--- | :--- | :--- | :--- |
| **File Management** | `file` | Read, write, list, and delete files in your workspace. | [`read config.json`](#example-workflows), `list files` |
| **Git** | `git` | Full version control integration. | [`git status`](#example-workflows), `git commit` |
| **Shell** | `shell` | Execute safe system commands. | `run tests.py`, `mkdir build`, `install numpy` |
| **Testing** | `pytest` | Run test suites (via shell). | `run pytest tests/` |
| **Documentation** | `pydoc` | View Python documentation (via shell). | `run pydoc -b` |
| **Search** | `grep` | Search codebase (via shell). | `execute grep -r "TODO" .` |
| **System** | `top` | Monitor system resources (via shell). | `execute top -n 1` |

---

## Future Enhancements (Realistic Roadmap)

Codey evolves by focusing on achievable milestones that respect local hardware constraints.

### 🟢 Achieved
*   **Split-Brain Architecture:** Router (270M) + Coder (7B) separation.
*   **Lifecycle Management:** Strict RAM budgeting and LRU model unloading.
*   **Mobile Support:** Validated on Android via Termux/UserLAnd.
*   **Tool Safety:** Strict registry and regex fallback for robustness.

### 🟡 Near Term (v3.1 - v3.5)
*   **Streaming Output:** Implement token streaming to reduce perceived latency (eliminating the 30s "thinking" pause).
*   **Unified Model Strategy:** Merge Algorithm/Coder roles into a single 7B model to eliminate reloading times.
*   **Smart Context:** Implement a sliding window or summary mechanism for long conversations.

### 🔴 Long Term (v4.0+)
*   **Multi-Modal Input:** Support for image inputs (e.g., "build this UI") — *requires larger VRAM/RAM*.
*   **Local Knowledge Base:** RAG (Retrieval-Augmented Generation) over your local codebase — *requires embedding model integration*.
*   **Plugin System:** Allow users to define custom tools via Python scripts.
*   **Speculative Decoding:** Use the small router to speed up the large model — *hardware permitting*.

---

## License

Codey is made available under a custom "Source Available" license.

**Summary at a glance:**
*   **You may:** Use, study, run, and modify the source code for personal or educational purposes.
*   **You may NOT:** Sell, redistribute for profit, or commercially exploit this software.

See [LICENSE.md](LICENSE.md) for full terms.
