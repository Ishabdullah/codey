# Codey: The Local, CPU-Optimized AI Engineer

> **Version:** 3.0 (Audited)
> **Architecture:** Local Multi-Model Orchestration
> **Focus:** Privacy, Zero-Cloud Dependency, Efficiency

Codey is a command-line AI software engineer designed to run **entirely on your local machine**. Unlike cloud-based assistants, Codey keeps your code private and works offline. It is specifically architected for standard consumer hardware (CPUs), prioritizing system stability and memory management over raw speed.

---

## ⚡ Capability Reality Check

### What Codey DOES
*   **Runs Locally:** No API keys, no monthly fees, no data egress.
*   **Edits Code:** Can read, analyze, and modify files in your workspace.
*   **Plans Tasks:** Breaks down complex instructions ("create a react app") into steps.
*   **Manages Git:** Handles commits, status checks, and history.
*   **Optimizes Resources:** strictly manages RAM usage to prevent system slowdowns.

### What Codey IS NOT
*   **Instant:** On a CPU, "thinking" takes time. Generating a complex function might take 30-60 seconds.
*   **A Supercomputer:** It uses 7B parameter models. It is competent at junior-to-mid-level tasks but will not architect a microservices backend in one shot.
*   **Magic:** It relies on clear instructions and context.

---

## 🏗 System Architecture

Codey uses a **Split-Brain Architecture** to balance speed and intelligence:

1.  **The Reflex Layer (Router):**
    *   **Model:** FunctionGemma 270M (Tiny, Fast)
    *   **Role:** Instantly decides if your request is a simple tool command (`git status`), a question, or a coding task.
    *   **Latency:** < 1 second.

2.  **The Deep Layer (Coder):**
    *   **Model:** Qwen2.5-Coder 7B (State-of-the-art for size)
    *   **Role:** Handles complex code generation, refactoring, and logic.
    *   **Latency:** Loaded on-demand. 5-30 seconds to generate.

3.  **Lifecycle Manager:**
    *   Actively manages RAM. If you have a 6GB limit, Codey ensures it unloads idle models before loading new ones to prevent crashing your OS.

---

## 🚀 Getting Started

### Prerequisites
*   **OS:** Linux / macOS / WSL2
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

### Configuration
Codey auto-generates a `config.json` on first run. Key settings to tune:
*   `memory_budget_mb`: Set this to ~70% of your available RAM.
*   `n_threads`: Set to number of physical CPU cores.

---

## 🚦 Usage

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

---

## 🔬 Performance Tuning

Running LLMs on CPU requires patience. Here is where the time goes:

| Action | Time Cost | Why? |
|os|---|---|
| **Routing** | < 1s | Small model, resident in memory. |
| **Model Loading** | 2-10s | Reading 5GB from disk into RAM. Happens when switching tasks. |
| **Generation** | 2-10 tok/s | Matrix multiplication on CPU is bandwidth-limited. |

**Pro Tip:** Group your tasks. Do all your coding at once. Do all your git operations at once. This avoids "thrashing" (repeatedly loading/unloading models).

---

## 🛠 Future Roadmap

*   **Streaming Output:** To make generation feel faster.
*   **Unified Model Strategy:** Merging Algorithm/Coder roles to reduce loading times.
*   **Smart Context:** Better handling of long conversation history.
