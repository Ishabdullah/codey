# Codey: Multi-Model Local AI Coding Assistant

**A local-first, mobile-capable AI coding system** delivering Claude Code-like functionality using specialized local GGUF models.

Codey is designed for **privacy**, **speed**, and **mobile hardware** (Android/Termux), with intelligent model routing and memory management.

---

## 🎯 What Makes Codey Different

- **Multi-Model Architecture**: 3 specialized models instead of one monolith
- **Smart Routing**: Small router model (270M) routes to larger specialists only when needed
- **Memory Efficient**: 6GB budget with automatic LRU unloading
- **Local-First**: No API keys required, runs completely offline
- **Mobile Optimized**: Designed for S24 Ultra / Snapdragon 8 Gen 3, works on Linux too

---

## 🏗️ Architecture (Phase 1 + 2 Complete)

```
┌─────────────────────────────────────────────────────────────┐
│                       USER INPUT                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              INTENT ROUTER (Phase 2)                         │
│  FunctionGemma 270M - Always resident, ~335MB               │
│                                                              │
│  ✓ Classifies intent (tool, code, algorithm, question)     │
│  ✓ Extracts parameters from natural language               │
│  ✓ Falls back to regex when uncertain                      │
│  ✓ Routes in <300ms                                        │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────────┐
    │          │          │              │
    ▼          ▼          ▼              ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐
│  GIT   │ │ SHELL  │ │ FILE   │ │   MODELS    │
│ TOOLS  │ │ TOOLS  │ │ TOOLS  │ │             │
└────────┘ └────────┘ └────────┘ │ Coder 7B    │
                                  │ Algorithm   │
    TOOL EXECUTOR (Phase 2)       │  6.7B       │
    No model needed!              └─────────────┘
    ~50-100ms latency              (Phase 3 - TBD)
```

### Model Stack

| Role | Model | Size | RAM | When Loaded |
|------|-------|------|-----|-------------|
| **Intent Router** | FunctionGemma 270M Q8_0 | 279MB | ~335MB | Always resident |
| **Primary Coder** | Qwen2.5-Coder 7B Q4_K_M | 4.4GB | ~5.3GB | On-demand (Phase 3) |
| **Algorithm Specialist** | DeepSeek-Coder 6.7B Q4_K_M | 3.9GB | ~5.0GB | Cold-loaded (Phase 3) |

---

## ✨ Features

### Phase 1: Model Lifecycle Management ✅

- **Multi-model support** with independent configuration
- **Memory budget enforcement** (default 6GB)
- **LRU unloading** automatically frees memory
- **Backward compatible** with existing code

### Phase 2: Intent Router & Tool Executor ✅

- **Intent classification** using FunctionGemma 270M
- **Direct tool execution** without loading heavy models
- **10-100x faster** for git/shell/file operations
- **Regex fallback** for uncertain classifications

### Phase 3-5: Coming Soon ⏳

- Specialized model wrappers (Qwen/DeepSeek)
- Engine decomposition (<200 lines)
- Diff-based editing (10x fewer tokens)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- 8-12GB RAM (for S24 Ultra / mobile)
- Models in `~/LLM_Models/`:
  - `functiongemma-270m-it-Q8_0.gguf` (router)
  - `qwen2.5-coder-7b-instruct-q4_k_m.gguf` (coder)
  - `deepseek-coder-6.7b-instruct-q4_k_m.gguf` (algorithm)

### Installation

```bash
# Clone repository
git clone https://github.com/Ishabdullah/codey.git
cd codey

# Install dependencies
pip install ninja cmake scikit-build
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
  pip install llama-cpp-python --no-cache-dir
```

### Test Installation

```bash
# Test Phase 1 (Model Lifecycle)
python3 test_phase1.py

# Test Phase 2 (Intent Router)
python3 test_phase2.py
```

Expected: **All tests passing** ✅

---

## 📖 Usage

### Current (Phase 2)

Phase 2 supports intelligent routing and direct tool execution:

```python
from core.orchestrator import Orchestrator
from utils.config import Config
from models.lifecycle import ModelLifecycleManager
# ... (see PHASE2_TESTING.md for full setup)

config = Config()
lifecycle = ModelLifecycleManager(config)
orchestrator = Orchestrator(config, lifecycle, tool_executor)

# Fast tool execution (~100ms)
response = orchestrator.process("git status")
response = orchestrator.process("list files")

# Simple answers via router
response = orchestrator.process("what is python?")

# Coding/algorithm tasks (Phase 3+)
response = orchestrator.process("create a file test.py")
# → Returns placeholder message (to be implemented in Phase 3)
```

### Legacy (Still Works)

Existing code using `CodeyEngineV2` works unchanged:

```python
from core.engine_v2 import CodeyEngineV2

engine = CodeyEngineV2()
response = engine.process_command("create test.py that prints hello world")
```

---

## 🧪 Testing

| Test | Command | What It Tests |
|------|---------|---------------|
| **Phase 1** | `python3 test_phase1.py` | Multi-model lifecycle, memory management |
| **Phase 2** | `python3 test_phase2.py` | Intent routing, tool execution |
| **Unit Tests** | `pytest tests/ -v` | Individual components |

### Quick Test

```bash
python3 test_phase2.py
```

Expected output:
```
✓ PASS: classification
✓ PASS: tool_execution
✓ PASS: orchestrator
✓ PASS: fallback
✓ PASS: memory

🎉 ALL TESTS PASSED - PHASE 2 COMPLETE!
```

---

## 📂 Project Structure

```
codey/
├── router/              # Phase 2: Intent classification
│   ├── intent_router.py # FunctionGemma 270M classifier
│   └── prompts.py       # Classification prompts
│
├── executor/            # Phase 2: Direct tool execution
│   └── tool_executor.py # Git/Shell/File without models
│
├── models/              # Phase 1: Model management
│   ├── base.py          # Abstract model interface
│   ├── lifecycle.py     # Multi-model coordinator
│   └── manager.py       # Legacy wrapper
│
├── core/                # Core components
│   ├── orchestrator.py  # Phase 2: Central routing
│   ├── engine_v2.py     # Legacy engine (still works)
│   ├── parser.py        # DEPRECATED (use router)
│   ├── tools.py         # File operations
│   ├── git_manager.py   # Git operations
│   └── shell_manager.py # Shell operations
│
├── agents/              # Legacy agents
│   ├── coding_agent.py
│   ├── debug_agent.py
│   └── todo_planner.py
│
├── tests/               # Unit tests
│   └── test_lifecycle.py
│
├── test_phase1.py       # Phase 1 integration test
├── test_phase2.py       # Phase 2 integration test
│
└── utils/
    └── config.py        # Multi-model configuration
```

---

## ⚙️ Configuration

Codey uses `~/codey/config.json` for configuration:

```json
{
  "models": {
    "router": {
      "path": "functiongemma-270m-it-Q8_0.gguf",
      "context_size": 2048,
      "always_resident": true
    },
    "coder": {
      "path": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
      "context_size": 8192,
      "unload_after_seconds": 60
    },
    "algorithm": {
      "path": "deepseek-coder-6.7b-instruct-q4_k_m.gguf",
      "context_size": 8192,
      "unload_after_seconds": 30
    }
  },
  "memory_budget_mb": 6000,
  "model_dir": "/home/userland/LLM_Models"
}
```

Auto-generated on first run. Points to `~/LLM_Models/`.

---

## 🔧 Troubleshooting

### llama-cpp-python Installation

**Error:** `ninja: No such file or directory`

**Fix:**
```bash
pip install ninja cmake scikit-build
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
  pip install llama-cpp-python --no-cache-dir --force-reinstall
```

### Models Not Found

**Error:** `FileNotFoundError: Model file not found`

**Fix:**
```bash
ls ~/LLM_Models/*.gguf

# Verify models exist
# See PHASE1_TESTING.md for download instructions
```

### Out of Memory

**Error:** Models fail to load

**Fix:** Reduce memory budget in `config.json`:
```json
"memory_budget_mb": 4000
```

---

## 📊 Performance

### Phase 2 vs Legacy

| Operation | Legacy (v2.1) | Phase 2 | Speedup |
|-----------|---------------|---------|---------|
| git status | ~5-10s (load 7B model) | ~100-300ms | **50-100x faster** |
| list files | ~5-10s | ~10-50ms | **500x faster** |
| Simple answer | ~8-12s | ~500ms | **16-24x faster** |

### Memory Usage

| Configuration | RAM Used | Models Loaded |
|---------------|----------|---------------|
| **Idle** | ~100MB | None |
| **Phase 2 Active** | ~435MB | Router only |
| **Legacy (v2.1)** | ~5.4GB | Qwen 7B always loaded |

Phase 2 uses **92% less memory** when idle!

---

## 🚧 Roadmap

- [x] **Phase 1**: Multi-model lifecycle manager
- [x] **Phase 2**: Intent router & tool executor
- [ ] **Phase 3**: Specialized model wrappers (Qwen/DeepSeek)
- [ ] **Phase 4**: Engine decomposition (<200 lines)
- [ ] **Phase 5**: Diff-based editing

See `REFACTORING_PLAN.md` for full details.

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| **README.md** (this file) | Overview and quick start |
| **QUICK_START.md** | Fast reference guide |
| **REFACTORING_PLAN.md** | Full architecture plan |
| **PHASE1_TESTING.md** | Phase 1 testing guide |
| **PHASE2_TESTING.md** | Phase 2 testing guide |
| **PHASE1_COMPLETE.md** | Phase 1 summary |

---

## 🤝 Contributing

Codey is under active development. Current focus:

- Phase 3: Specialized model integration
- Phase 4: Lightweight orchestration
- Phase 5: Efficient editing

---

## 📄 License

Proprietary - See LICENSE file

---

## 🎯 Design Principles

1. **Local-first**: No cloud dependency
2. **Privacy**: Your code stays on your device
3. **Speed**: Fast routing, on-demand loading
4. **Efficiency**: Memory budgets, smart unloading
5. **Mobile-capable**: Optimized for 6-8GB RAM devices

---

## 🙏 Credits

- **Architecture**: Multi-model routing inspired by Claude Code
- **Models**: FunctionGemma (Google), Qwen2.5-Coder (Alibaba), DeepSeek-Coder
- **Backend**: llama.cpp by ggerganov
- **Platform**: Optimized for S24 Ultra / Android (works on Linux)

---

**Current Status:** Phase 2 Complete ✅

Run `python3 test_phase2.py` to verify your installation!
