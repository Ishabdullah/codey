# Codey Multi-Model Architecture Refactoring Plan

**Date:** December 24, 2025
**Target:** Local-first, mobile-capable AI coding powerhouse
**Author:** Senior AI Systems Architect

---

## 1. Current State Diagnosis

### 1.1 What Codey Currently Does Well

| Strength | Location | Details |
|----------|----------|---------|
| **Modular Agent Pattern** | `agents/` | Clean separation: `CodingAgent`, `DebugAgent`, `TodoPlanner` each handle specific tasks |
| **Safety-First Design** | `core/permission_manager.py`, `core/shell_manager.py` | Comprehensive permission system, command classification (SAFE/RISKY/FORBIDDEN), forbidden pattern detection |
| **Tool Abstraction** | `core/tools.py`, `core/git_manager.py` | File operations and git wrapped behind clean interfaces |
| **Profile System** | `utils/config.py` | Hardware-specific model profiles (GPU layers, threads, context size) already exist |
| **Hybrid Fallback** | `agents/perplexity_api.py` | External API fallback when local model is insufficient |
| **Multi-step Execution** | `core/engine_v2.py:683-828` | Complex instruction breakdown with user confirmation per step |

### 1.2 Where Responsibilities Are Mixed Incorrectly

#### Problem 1: Monolithic Engine (CRITICAL)
**File:** `core/engine_v2.py` (1,114 lines)

The engine conflates:
- Intent detection (`_is_complex_instruction`, `_should_use_hybrid`)
- Command routing (`process_command` massive if/elif chain)
- Tool orchestration (git, shell, file operations)
- Task execution (all `_handle_*` methods)
- UI/UX (todo list display, confirmations)

```
process_command()
├── _is_complex_instruction()     # Intent detection
├── _handle_plan_command()        # Planning
├── _handle_git_command()         # Tool execution
├── _handle_shell_command()       # Tool execution
├── parser.parse()                # Intent detection
├── _should_use_hybrid()          # Model routing (primitive)
├── _handle_create()              # Coding task
├── _handle_edit()                # Coding task
├── _handle_general()             # General Q&A
└── _local_query()                # Direct model call
```

**Impact:** Cannot swap intent detection or model routing without touching the entire engine.

#### Problem 2: Single Model Manager for All Tasks
**File:** `models/manager.py` (135 lines)

```python
class ModelManager:
    def __init__(self, config):
        self.model = None  # ONE model slot
```

All agents share one model. No ability to:
- Load different models for different task types
- Keep a router model hot while loading coder on-demand
- Escalate between models based on confidence

#### Problem 3: Regex-Based Intent Parsing
**File:** `core/parser.py`

```python
self.action_patterns = {
    'create': [r'create\s+...', r'make\s+...'],
    'edit': [r'edit\s+...', r'modify\s+...'],
    ...
}
```

**Impact:** Fails on natural language variations. No confidence scoring. No escalation path when parsing fails.

#### Problem 4: Direct Model Calls in Agents
**Files:** `agents/coding_agent.py`, `agents/debug_agent.py`

```python
# coding_agent.py:73-78
response = self.model.generate(
    prompt,
    temperature=self.config.temperature,
    max_tokens=self.config.max_tokens,
    ...
)
```

Agents call `self.model.generate()` directly with hardcoded parameters. No task-type-aware model selection.

### 1.3 Single-Model Design Limitations

| Limitation | Impact |
|------------|--------|
| **Always-on 7B Model** | High memory footprint even for simple queries |
| **No Fast Path** | "list files" requires same model load as "refactor entire module" |
| **No Confidence Routing** | If router is uncertain, there's no way to escalate |
| **No Specialization** | Same model for intent parsing, code generation, algorithm design |
| **Context Waste** | Full conversation context sent to coder for simple tool calls |

### 1.4 Specific Files Causing Coupling/Rigidity

| File | Issue | Lines |
|------|-------|-------|
| `core/engine_v2.py` | God object; mixes routing, execution, UI | 1,114 |
| `models/manager.py` | Single model slot; no multi-model support | 135 |
| `core/parser.py` | Regex-only; no confidence; no fallback | 119 |
| `agents/coding_agent.py` | Direct model.generate() calls | 215 |
| `agents/debug_agent.py` | Direct model.generate() calls | 277 |

---

## 2. Target Architecture (Concrete)

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INTENT ROUTER                                        │
│  Model: FunctionGemma 270M (always-resident, ~200MB RAM)                    │
│  File: router/intent_router.py                                               │
│                                                                              │
│  Responsibilities:                                                           │
│  • Parse user intent from natural language                                   │
│  • Classify: TOOL_CALL | SIMPLE_ANSWER | CODING_TASK | ALGORITHM_TASK       │
│  • Extract tool parameters (filename, command, git action)                   │
│  • Assess confidence (0.0 - 1.0)                                            │
│  • Decide: handle directly OR escalate to coder                              │
│                                                                              │
│  Output: IntentResult { intent, confidence, params, escalate_to }           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────────────┐
│   TOOL EXECUTOR   │   │  PRIMARY CODER    │   │  ALGORITHMIC SPECIALIST   │
│                   │   │                   │   │                           │
│ No model needed   │   │ Qwen2.5-Coder 7B  │   │ DeepSeek-Coder 6.7B       │
│                   │   │ (~4GB, on-demand) │   │ (~4GB, cold-loaded)       │
│ Direct execution: │   │                   │   │                           │
│ • File ops        │   │ Responsibilities: │   │ Responsibilities:         │
│ • Git commands    │   │ • Code generation │   │ • Algorithm design        │
│ • Shell commands  │   │ • Multi-file edit │   │ • Performance code        │
│ • Directory ops   │   │ • Refactoring     │   │ • Parser/state machines   │
│                   │   │ • Code review     │   │ • Math-heavy logic        │
│                   │   │ • Bug fixes       │   │                           │
│ File:             │   │                   │   │ File:                     │
│ executor/         │   │ File:             │   │ models/algorithm_model.py │
│ tool_executor.py  │   │ models/coder.py   │   │                           │
└───────────────────┘   └───────────────────┘   └───────────────────────────┘
        │                           │                           │
        └───────────────────────────┴───────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RESPONSE HANDLER                                     │
│  File: core/response_handler.py                                              │
│                                                                              │
│  • Format model outputs for CLI                                              │
│  • Handle streaming (future)                                                 │
│  • Error formatting                                                          │
│  • Memory storage                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Model Stack Specification

| Role | Model | GGUF Quantization | RAM Estimate | Load Strategy |
|------|-------|-------------------|--------------|---------------|
| **Intent Router** | FunctionGemma 270M | Q8_0 | ~300MB | Always resident |
| **Intent Router (Alt)** | Phi-3 Mini 3.8B | Q4_K_M | ~2.5GB | Always resident |
| **Primary Coder** | Qwen2.5-Coder 7B | Q4_K_M | ~4.5GB | On-demand, unload after task |
| **Algorithm Specialist** | DeepSeek-Coder 6.7B | Q4_K_M | ~4.2GB | Cold-load only when escalated |

### 2.3 Component Responsibilities

#### Intent Router (`router/intent_router.py`)

```python
class IntentRouter:
    """Always-on, low-latency intent detection"""

    def __init__(self, model_path: Path, context_size: int = 2048):
        self.model = None  # FunctionGemma or Phi-3 Mini

    def classify(self, user_input: str, context: dict) -> IntentResult:
        """
        Returns:
            IntentResult:
                intent: str  # "tool_call", "simple_answer", "coding_task", "algorithm_task"
                confidence: float  # 0.0 - 1.0
                params: dict  # extracted parameters
                escalate_to: Optional[str]  # "coder" | "algorithm" | None
                tool: Optional[str]  # "git", "shell", "file", "debug"
        """

    def should_escalate(self, confidence: float, task_complexity: str) -> bool:
        """Determine if task should go to larger model"""
```

**What Intent Router Does NOT Do:**
- Deep code reasoning
- Multi-file refactoring
- Writing production code
- Architecture decisions

#### Tool Executor (`executor/tool_executor.py`)

```python
class ToolExecutor:
    """Executes tools without model inference"""

    def __init__(self, git_manager, shell_manager, file_tools, permission_manager):
        self.git = git_manager
        self.shell = shell_manager
        self.files = file_tools
        self.permissions = permission_manager

    def execute(self, tool: str, params: dict) -> ToolResult:
        """Execute tool based on intent router's extracted params"""

    # Supported tools:
    # - file_read, file_write, file_delete, file_list
    # - git_status, git_commit, git_push, git_pull, git_clone
    # - shell_execute, shell_mkdir, shell_run_python
    # - install_package, install_requirements
```

#### Primary Coder (`models/coder.py`)

```python
class PrimaryCoder:
    """On-demand coding model for deep reasoning"""

    def __init__(self, model_path: Path, config: dict):
        self.model = None  # Loaded on-demand
        self.loaded = False

    def load(self) -> None:
        """Load model into memory - called before coding tasks"""

    def unload(self) -> None:
        """Unload to free RAM - called after task completion"""

    def generate_code(self, task: CodingTask) -> CodeResult:
        """Generate or modify code"""

    def explain_code(self, code: str, context: str) -> str:
        """Explain code logic"""

    def review_code(self, code: str, criteria: list) -> ReviewResult:
        """Review code for issues"""
```

**CodingTask Structure:**
```python
@dataclass
class CodingTask:
    task_type: str  # "create", "edit", "refactor", "fix"
    target_files: List[str]
    instructions: str
    existing_code: Optional[Dict[str, str]]  # filename -> content
    language: str
    constraints: List[str]  # e.g., ["preserve existing API", "add tests"]
```

#### Algorithm Specialist (`models/algorithm_model.py`)

```python
class AlgorithmSpecialist:
    """Cold-loaded specialist for hard algorithmic problems"""

    def __init__(self, model_path: Path, config: dict):
        self.model = None
        self.loaded = False

    def solve(self, problem: AlgorithmTask) -> AlgorithmResult:
        """Solve algorithmic problems"""

# Triggered when:
# - Intent router detects algorithm keywords with high complexity
# - Primary coder explicitly escalates
# - User requests "optimize performance" on specific functions
```

### 2.4 Task and Context Flow

```
User: "Create a binary search tree implementation with insert and delete"

1. INTENT ROUTER (FunctionGemma 270M)
   Input: "Create a binary search tree implementation with insert and delete"
   Analysis:
     - Detects: coding task (create)
     - Complexity: high (data structure, multiple methods)
     - Algorithm keywords: "binary search tree"
   Output: IntentResult {
     intent: "coding_task",
     confidence: 0.92,
     params: {filename: "bst.py", type: "create"},
     escalate_to: "algorithm"  # BST is algorithmic
   }

2. MODEL LIFECYCLE MANAGER
   - Receives escalation request for "algorithm"
   - Checks RAM availability
   - Loads DeepSeek-Coder 6.7B (cold load ~5s)
   - Unloads any previously loaded coder model

3. ALGORITHM SPECIALIST (DeepSeek-Coder 6.7B)
   Input (DISTILLED - not full conversation):
     Task: Create Python file bst.py
     Requirements: Binary search tree with insert and delete operations
     Constraints: Production quality, include type hints
   Output: Complete BST implementation

4. TOOL EXECUTOR
   - Receives generated code from specialist
   - Requests file creation permission
   - Writes bst.py

5. MODEL LIFECYCLE MANAGER
   - Task complete
   - Schedules algorithm model for unload (after cooldown period)

6. RESPONSE HANDLER
   - Formats success message
   - Stores in memory
   - Returns to user
```

### 2.5 Tool Call Flow

```
User: "git status"

1. INTENT ROUTER (FunctionGemma 270M)
   Input: "git status"
   Analysis:
     - Direct tool call pattern
     - No coding required
     - High confidence match
   Output: IntentResult {
     intent: "tool_call",
     confidence: 0.99,
     tool: "git",
     params: {action: "status"},
     escalate_to: None
   }

2. TOOL EXECUTOR
   - No model needed
   - Direct execution via GitManager
   - Returns status

3. RESPONSE HANDLER
   - Formats git status output
   - Returns to user

Total latency: ~100ms (router inference) + ~50ms (git execution)
Models loaded: Only router (270M)
```

---

## 3. Model Routing & Escalation Logic

### 3.1 Decision Flow Diagram

```
                    ┌─────────────────────┐
                    │    USER INPUT       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   INTENT ROUTER     │
                    │   (FunctionGemma)   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
    │  TOOL_CALL?     │ │ SIMPLE_Q?   │ │ CODING_TASK?    │
    │  confidence>0.9 │ │ conf>0.85   │ │ conf>0.7        │
    └────────┬────────┘ └──────┬──────┘ └────────┬────────┘
             │                 │                  │
             ▼                 ▼                  ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
    │ TOOL EXECUTOR   │ │ ROUTER      │ │ COMPLEXITY?     │
    │ (no model)      │ │ ANSWERS     │ │                 │
    └─────────────────┘ └─────────────┘ └────────┬────────┘
                                                  │
                              ┌───────────────────┼───────────────────┐
                              │                   │                   │
                              ▼                   ▼                   ▼
                    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
                    │ LOW COMPLEXITY  │ │ MEDIUM          │ │ HIGH/ALGORITHM  │
                    │ single file     │ │ multi-file      │ │ perf-critical   │
                    │ simple edit     │ │ refactor        │ │ data structures │
                    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
                             │                   │                   │
                             ▼                   ▼                   ▼
                    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
                    │ PRIMARY CODER   │ │ PRIMARY CODER   │ │ ALGORITHM       │
                    │ (Qwen2.5 7B)    │ │ (Qwen2.5 7B)    │ │ SPECIALIST      │
                    │ short context   │ │ full context    │ │ (DeepSeek 6.7B) │
                    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 3.2 Intent Classification Rules

```python
# router/classification.py

INTENT_PATTERNS = {
    "tool_call": {
        "patterns": [
            r"^(git|ls|pwd|cd|mkdir|rm|cat|show|list|read|delete)\b",
            r"^(run|execute|install)\s+",
            r"^clone\s+",
            r"^(commit|push|pull|status)\b",
        ],
        "min_confidence": 0.90,
        "escalation": None,
    },

    "simple_answer": {
        "patterns": [
            r"^(what is|what's|how do|how does|why|explain)\b",
            r"^(can you|could you)\s+(tell|explain)",
        ],
        "min_confidence": 0.85,
        "escalation": None,  # Router handles directly
        "max_response_tokens": 256,
    },

    "coding_task": {
        "patterns": [
            r"(create|write|generate|implement|build)\s+.*(file|script|class|function|module)",
            r"(edit|modify|update|change|fix)\s+",
            r"(refactor|optimize|improve)\s+",
            r"(add|remove)\s+.*(feature|functionality|method)",
        ],
        "min_confidence": 0.70,
        "escalation": "coder",
    },

    "algorithm_task": {
        "patterns": [
            r"(binary search|sorting|graph|tree|heap|hash|dynamic programming)",
            r"(algorithm|data structure|complexity|O\(n\)|performance)",
            r"(parser|lexer|state machine|automaton)",
            r"(optimize|performance-critical|low-latency)",
        ],
        "min_confidence": 0.75,
        "escalation": "algorithm",
    },
}
```

### 3.3 Confidence Thresholds and Actions

| Confidence | Router Action |
|------------|---------------|
| ≥ 0.95 | Execute immediately, no confirmation |
| 0.85 - 0.94 | Execute with brief confirmation |
| 0.70 - 0.84 | Escalate to appropriate coder model |
| 0.50 - 0.69 | Ask user for clarification |
| < 0.50 | "I'm not sure what you mean. Could you rephrase?" |

### 3.4 Escalation Triggers

**Router → Primary Coder:**
- Intent is `coding_task` with confidence > 0.7
- Task involves file creation/modification
- User explicitly asks to "write code" or "implement"
- Router's simple answer would exceed 256 tokens

**Router → Algorithm Specialist:**
- Intent is `algorithm_task` with confidence > 0.75
- Primary coder explicitly escalates (returns `needs_algorithm_specialist: true`)
- Task contains keywords: "optimize", "performance", "algorithm", "data structure"
- Complexity score > 0.8 (measured by router)

**Primary Coder → Algorithm Specialist:**
- Coder identifies algorithm-heavy subtask during reasoning
- Performance optimization requested on compute-intensive code
- Parsing/compilation logic detected

### 3.5 Fallback and Recovery

```python
# core/fallback.py

class FallbackManager:
    """Handle failures and uncertainty gracefully"""

    def handle_router_failure(self, error: Exception) -> IntentResult:
        """Router crashed or returned invalid output"""
        return IntentResult(
            intent="unknown",
            confidence=0.0,
            message="I encountered an issue understanding your request. Could you rephrase?"
        )

    def handle_coder_failure(self, error: Exception, task: CodingTask) -> CodeResult:
        """Coder failed to generate valid code"""
        # Attempt 1: Retry with simplified prompt
        # Attempt 2: Escalate to algorithm specialist
        # Attempt 3: Return error with partial result

    def handle_model_load_failure(self, model_name: str) -> None:
        """Model failed to load (OOM, file not found)"""
        # Fallback chain:
        # 1. Try loading smaller quantization
        # 2. Reduce context size
        # 3. Fall back to Perplexity API (if configured)
        # 4. Inform user of hardware limitations

    def handle_low_confidence(self, result: IntentResult) -> str:
        """Router returned low confidence"""
        options = self._generate_clarification_options(result)
        return f"I'm not certain I understood. Did you mean:\n{options}"
```

---

## 4. Refactoring Phases (Incremental)

### Phase 1: Foundation - Model Lifecycle Manager
**Goal:** Enable multi-model support without breaking existing functionality
**Files to Create/Modify:** 4 new, 2 modified
**Risk:** Low (additive changes)

#### 4.1.1 Create Model Lifecycle Manager

**New File:** `models/lifecycle.py`

```python
from enum import Enum
from typing import Optional, Dict
from pathlib import Path
import gc

class ModelRole(Enum):
    ROUTER = "router"
    CODER = "coder"
    ALGORITHM = "algorithm"

class ModelLifecycleManager:
    """Manages loading/unloading of multiple models"""

    def __init__(self, config):
        self.config = config
        self.models: Dict[ModelRole, Optional[object]] = {
            ModelRole.ROUTER: None,
            ModelRole.CODER: None,
            ModelRole.ALGORITHM: None,
        }
        self.model_configs = self._load_model_configs()

    def load_model(self, role: ModelRole) -> object:
        """Load model for role, unloading others if necessary"""

    def unload_model(self, role: ModelRole) -> None:
        """Unload model and free memory"""

    def ensure_loaded(self, role: ModelRole) -> object:
        """Ensure model is loaded, loading if necessary"""

    def get_memory_usage(self) -> dict:
        """Return current memory usage per model"""

    def _enforce_memory_limit(self, required_mb: int) -> None:
        """Unload models to fit within memory budget"""
```

#### 4.1.2 Update Config for Multi-Model

**Modified File:** `utils/config.py`

Add new config section:

```python
# New config structure
"models": {
    "router": {
        "path": "functiongemma-270m.Q8_0.gguf",
        "context_size": 2048,
        "always_resident": true,
        "n_gpu_layers": 10
    },
    "coder": {
        "path": "qwen2.5-coder-7b-instruct.Q4_K_M.gguf",
        "context_size": 8192,
        "always_resident": false,
        "n_gpu_layers": 35,
        "unload_after_seconds": 60
    },
    "algorithm": {
        "path": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "context_size": 8192,
        "always_resident": false,
        "n_gpu_layers": 35,
        "unload_after_seconds": 30
    }
},
"memory_budget_mb": 6000
```

#### 4.1.3 Create Model Base Class

**New File:** `models/base.py`

```python
from abc import ABC, abstractmethod
from pathlib import Path

class BaseModel(ABC):
    """Abstract base for all model wrappers"""

    def __init__(self, model_path: Path, config: dict):
        self.model_path = model_path
        self.config = config
        self._model = None
        self._loaded = False

    @abstractmethod
    def load(self) -> None:
        """Load model into memory"""

    @abstractmethod
    def unload(self) -> None:
        """Unload model from memory"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""

    @property
    def loaded(self) -> bool:
        return self._loaded

    def get_memory_estimate_mb(self) -> int:
        """Estimate memory usage for this model"""
```

#### 4.1.4 Refactor Existing ModelManager

**Modified File:** `models/manager.py`

```python
# Keep backward compatibility by wrapping new system
class ModelManager:
    """Legacy wrapper - delegates to ModelLifecycleManager"""

    def __init__(self, config):
        from models.lifecycle import ModelLifecycleManager, ModelRole
        self._lifecycle = ModelLifecycleManager(config)
        self._default_role = ModelRole.CODER  # Backward compat

    def load_model(self):
        """Legacy method - loads default coder"""
        return self._lifecycle.load_model(self._default_role)

    def generate(self, prompt, **kwargs):
        """Legacy method - uses default model"""
        model = self._lifecycle.ensure_loaded(self._default_role)
        return model.generate(prompt, **kwargs)
```

#### 4.1.5 Deliverables

- [ ] `models/lifecycle.py` - Model lifecycle manager
- [ ] `models/base.py` - Abstract base class
- [ ] Update `utils/config.py` - Multi-model config
- [ ] Update `models/manager.py` - Legacy compatibility wrapper
- [ ] Unit tests for lifecycle manager

**Stable After Phase 1:** Existing functionality works unchanged. New multi-model infrastructure ready.

---

### Phase 2: Intent Router Implementation
**Goal:** Replace regex parsing with model-based intent detection
**Files to Create/Modify:** 5 new, 1 modified, 1 deprecated
**Risk:** Medium (changes routing logic)

#### 4.2.1 Create Intent Router

**New File:** `router/intent_router.py`

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from models.base import BaseModel

@dataclass
class IntentResult:
    intent: str  # "tool_call", "simple_answer", "coding_task", "algorithm_task"
    confidence: float
    params: Dict[str, Any]
    escalate_to: Optional[str]  # "coder", "algorithm", None
    tool: Optional[str]  # For tool_call: "git", "shell", "file"
    raw_response: str  # For debugging

class IntentRouter(BaseModel):
    """Low-latency intent detection using small model"""

    SYSTEM_PROMPT = """You are an intent classifier. Given a user request, output JSON:
{
  "intent": "tool_call" | "simple_answer" | "coding_task" | "algorithm_task",
  "confidence": 0.0-1.0,
  "tool": "git" | "shell" | "file" | null,
  "params": {...},
  "escalate": "coder" | "algorithm" | null
}"""

    def classify(self, user_input: str, context: Optional[dict] = None) -> IntentResult:
        """Classify user intent"""

    def _parse_response(self, response: str) -> IntentResult:
        """Parse model JSON output"""

    def _fallback_regex(self, user_input: str) -> IntentResult:
        """Fallback to regex if model output is invalid"""
```

#### 4.2.2 Create Router Prompt Templates

**New File:** `router/prompts.py`

```python
INTENT_CLASSIFICATION_PROMPT = """
Classify this user request. Output valid JSON only.

User: {user_input}

Recent context (if relevant):
{context}

Classification:"""

PARAMETER_EXTRACTION_PROMPT = """
Extract parameters from this request.

User: {user_input}
Intent: {intent}

Extract as JSON:"""
```

#### 4.2.3 Create Tool Executor

**New File:** `executor/tool_executor.py`

```python
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ToolResult:
    success: bool
    output: Any
    error: Optional[str]

class ToolExecutor:
    """Executes tools without needing model inference"""

    def __init__(self, git_manager, shell_manager, file_tools, permission_manager):
        self.git = git_manager
        self.shell = shell_manager
        self.files = file_tools
        self.permissions = permission_manager

        self._tool_handlers = {
            "git": self._handle_git,
            "shell": self._handle_shell,
            "file": self._handle_file,
        }

    def execute(self, tool: str, params: Dict[str, Any]) -> ToolResult:
        """Execute tool based on router's classification"""
        handler = self._tool_handlers.get(tool)
        if not handler:
            return ToolResult(success=False, output=None, error=f"Unknown tool: {tool}")
        return handler(params)

    def _handle_git(self, params: dict) -> ToolResult:
        """Handle git operations"""

    def _handle_shell(self, params: dict) -> ToolResult:
        """Handle shell commands"""

    def _handle_file(self, params: dict) -> ToolResult:
        """Handle file operations"""
```

#### 4.2.4 Create Orchestrator (Replace Engine Routing)

**New File:** `core/orchestrator.py`

```python
class Orchestrator:
    """Central coordination between router, models, and tools"""

    def __init__(self, config, lifecycle_manager, tool_executor):
        self.config = config
        self.lifecycle = lifecycle_manager
        self.tools = tool_executor
        self.router = None  # Loaded on init

    def process(self, user_input: str) -> str:
        """Main entry point - replaces engine.process_command()"""
        # 1. Classify intent
        intent_result = self.router.classify(user_input)

        # 2. Route based on intent
        if intent_result.intent == "tool_call":
            return self._handle_tool_call(intent_result)
        elif intent_result.intent == "simple_answer":
            return self._handle_simple_answer(intent_result, user_input)
        elif intent_result.intent == "coding_task":
            return self._handle_coding_task(intent_result, user_input)
        elif intent_result.intent == "algorithm_task":
            return self._handle_algorithm_task(intent_result, user_input)
        else:
            return self._handle_unknown(intent_result, user_input)
```

#### 4.2.5 Deprecate Old Parser

**Modified File:** `core/parser.py`

```python
import warnings

class CommandParser:
    """DEPRECATED: Use router/intent_router.py instead"""

    def __init__(self):
        warnings.warn(
            "CommandParser is deprecated. Use IntentRouter for intent detection.",
            DeprecationWarning
        )
        # Keep existing implementation for fallback
```

#### 4.2.6 Deliverables

- [ ] `router/intent_router.py` - Intent classification model
- [ ] `router/prompts.py` - Prompt templates
- [ ] `router/__init__.py` - Package init
- [ ] `executor/tool_executor.py` - Tool execution
- [ ] `executor/__init__.py` - Package init
- [ ] `core/orchestrator.py` - New coordination layer
- [ ] Deprecation warning in `core/parser.py`
- [ ] Integration tests for routing

**Stable After Phase 2:** Router handles intent detection. Tool calls bypass coder model.

---

### Phase 3: Specialized Model Integration
**Goal:** Integrate Qwen2.5-Coder and DeepSeek-Coder as specialized models
**Files to Create/Modify:** 4 new, 2 modified
**Risk:** Medium (new model integrations)

#### 4.3.1 Create Primary Coder Wrapper

**New File:** `models/coder.py`

```python
from models.base import BaseModel
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class CodingTask:
    task_type: str  # "create", "edit", "refactor", "fix", "explain"
    target_files: List[str]
    instructions: str
    existing_code: Optional[Dict[str, str]]  # filename -> content
    language: str
    constraints: List[str]

@dataclass
class CodeResult:
    success: bool
    code: Optional[Dict[str, str]]  # filename -> content
    explanation: Optional[str]
    needs_algorithm_specialist: bool
    error: Optional[str]

class PrimaryCoder(BaseModel):
    """Qwen2.5-Coder 7B for code generation and editing"""

    SYSTEM_PROMPT = """You are an expert coding assistant. Generate clean, production-ready code.
When editing, output ONLY the modified code blocks, not the entire file.
When you need algorithmic expertise, indicate: NEEDS_ALGORITHM_SPECIALIST: true"""

    def generate_code(self, task: CodingTask) -> CodeResult:
        """Generate or modify code based on task"""

    def explain_code(self, code: str, filename: str) -> str:
        """Explain what code does"""

    def review_code(self, code: str, criteria: List[str]) -> Dict:
        """Review code against criteria"""

    def _should_escalate(self, task: CodingTask) -> bool:
        """Determine if task needs algorithm specialist"""
```

#### 4.3.2 Create Algorithm Specialist Wrapper

**New File:** `models/algorithm_model.py`

```python
from models.base import BaseModel
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AlgorithmTask:
    problem_description: str
    constraints: List[str]
    expected_complexity: Optional[str]  # e.g., "O(n log n)"
    language: str
    context_code: Optional[str]  # Surrounding code for integration

@dataclass
class AlgorithmResult:
    success: bool
    code: str
    explanation: str
    complexity_analysis: str
    error: Optional[str]

class AlgorithmSpecialist(BaseModel):
    """DeepSeek-Coder 6.7B for algorithmic problems"""

    SYSTEM_PROMPT = """You are an algorithm expert. Generate efficient, correct algorithms.
Always include:
1. Time complexity analysis
2. Space complexity analysis
3. Edge case handling
4. Clear comments explaining the approach"""

    def solve(self, task: AlgorithmTask) -> AlgorithmResult:
        """Solve algorithmic problem"""

    def optimize(self, code: str, target_complexity: str) -> AlgorithmResult:
        """Optimize existing code for performance"""

    def analyze_complexity(self, code: str) -> Dict:
        """Analyze time/space complexity of code"""
```

#### 4.3.3 Update Orchestrator for Model Escalation

**Modified File:** `core/orchestrator.py`

Add escalation logic:

```python
def _handle_coding_task(self, intent: IntentResult, user_input: str) -> str:
    """Handle coding tasks with potential escalation"""
    # 1. Load primary coder
    coder = self.lifecycle.ensure_loaded(ModelRole.CODER)

    # 2. Build coding task
    task = self._build_coding_task(intent, user_input)

    # 3. Execute
    result = coder.generate_code(task)

    # 4. Check for escalation
    if result.needs_algorithm_specialist:
        return self._escalate_to_algorithm(task, result)

    return self._format_code_result(result)

def _escalate_to_algorithm(self, task: CodingTask, partial_result: CodeResult) -> str:
    """Escalate to algorithm specialist"""
    # 1. Unload coder to free memory
    self.lifecycle.unload_model(ModelRole.CODER)

    # 2. Load algorithm specialist
    specialist = self.lifecycle.ensure_loaded(ModelRole.ALGORITHM)

    # 3. Build algorithm task from coding task
    algo_task = self._extract_algorithm_task(task, partial_result)

    # 4. Solve
    result = specialist.solve(algo_task)

    return self._format_algorithm_result(result)
```

#### 4.3.4 Refactor Agents to Use New Models

**Modified Files:** `agents/coding_agent.py`, `agents/debug_agent.py`

```python
# coding_agent.py - Updated to use PrimaryCoder

class CodingAgent:
    """Agent using PrimaryCoder model"""

    def __init__(self, lifecycle_manager, file_tools, config):
        self.lifecycle = lifecycle_manager
        self.tools = file_tools
        self.config = config

    def create_file(self, filename: str, instructions: str) -> dict:
        """Generate and create a new file"""
        from models.coder import CodingTask, PrimaryCoder

        coder = self.lifecycle.ensure_loaded(ModelRole.CODER)

        task = CodingTask(
            task_type="create",
            target_files=[filename],
            instructions=instructions,
            existing_code=None,
            language=self._infer_language(filename),
            constraints=[]
        )

        result = coder.generate_code(task)
        # ... rest of implementation
```

#### 4.3.5 Deliverables

- [ ] `models/coder.py` - Qwen2.5-Coder wrapper
- [ ] `models/algorithm_model.py` - DeepSeek-Coder wrapper
- [ ] Update `core/orchestrator.py` - Escalation logic
- [ ] Update `agents/coding_agent.py` - Use new model
- [ ] Update `agents/debug_agent.py` - Use new model
- [ ] Integration tests for escalation

**Stable After Phase 3:** Full multi-model routing operational.

---

### Phase 4: Engine Decomposition
**Goal:** Break apart monolithic engine_v2.py
**Files to Create/Modify:** 3 new, 1 heavily modified, 1 deprecated
**Risk:** High (core refactor)

#### 4.4.1 Extract Response Handler

**New File:** `core/response_handler.py`

```python
class ResponseHandler:
    """Format and deliver responses"""

    def __init__(self, memory_store, config):
        self.memory = memory_store
        self.config = config

    def format_code_result(self, result: CodeResult, task: CodingTask) -> str:
        """Format code generation result"""

    def format_tool_result(self, result: ToolResult, tool: str) -> str:
        """Format tool execution result"""

    def format_error(self, error: str, context: dict) -> str:
        """Format error message"""

    def store_interaction(self, user_input: str, response: str, action: str) -> None:
        """Store in memory"""
```

#### 4.4.2 Extract Complex Instruction Handler

**New File:** `core/task_planner.py`

```python
class TaskPlanner:
    """Handle multi-step complex instructions"""

    def __init__(self, orchestrator, permission_manager):
        self.orchestrator = orchestrator
        self.permissions = permission_manager

    def is_complex_instruction(self, user_input: str) -> bool:
        """Detect multi-step instructions"""

    def plan_tasks(self, user_input: str) -> List[PlannedTask]:
        """Break instruction into tasks"""

    def execute_plan(self, tasks: List[PlannedTask]) -> PlanResult:
        """Execute tasks with confirmation"""
```

#### 4.4.3 Create New Lightweight Engine

**New File:** `core/engine_v3.py`

```python
class CodeyEngineV3:
    """Lightweight engine - delegates to specialized components"""

    def __init__(self):
        # Initialize components
        self.config = Config()
        self.lifecycle = ModelLifecycleManager(self.config)
        self.tool_executor = ToolExecutor(...)
        self.orchestrator = Orchestrator(self.config, self.lifecycle, self.tool_executor)
        self.task_planner = TaskPlanner(self.orchestrator, ...)
        self.response_handler = ResponseHandler(...)

    def process_command(self, user_input: str) -> str:
        """Main entry point"""
        # Check for complex instruction
        if self.task_planner.is_complex_instruction(user_input):
            return self._handle_complex(user_input)

        # Delegate to orchestrator
        return self.orchestrator.process(user_input)

    def _handle_complex(self, user_input: str) -> str:
        """Handle multi-step instructions"""
        tasks = self.task_planner.plan_tasks(user_input)
        return self.task_planner.execute_plan(tasks)

    def shutdown(self) -> None:
        """Clean shutdown"""
        self.lifecycle.unload_all()
        self.response_handler.memory.save_memory()
```

#### 4.4.4 Deprecate engine_v2.py

**Modified File:** `core/engine_v2.py`

```python
import warnings

class CodeyEngineV2:
    """DEPRECATED: Use CodeyEngineV3"""

    def __init__(self):
        warnings.warn(
            "CodeyEngineV2 is deprecated. Use CodeyEngineV3 for multi-model support.",
            DeprecationWarning
        )
        # Keep implementation for backward compatibility
```

#### 4.4.5 Deliverables

- [ ] `core/response_handler.py` - Response formatting
- [ ] `core/task_planner.py` - Complex instruction handling
- [ ] `core/engine_v3.py` - New lightweight engine
- [ ] Deprecate `core/engine_v2.py`
- [ ] Update `cli/main.py` to use v3 (with fallback to v2)
- [ ] Migration tests

**Stable After Phase 4:** Clean architecture. Engine under 200 lines.

---

### Phase 5: Diff-Based Editing
**Goal:** Replace full-file regeneration with targeted edits
**Files to Create/Modify:** 2 new, 1 modified
**Risk:** Medium (changes edit behavior)

#### 4.5.1 Create Diff Generator

**New File:** `core/diff_generator.py`

```python
from dataclasses import dataclass
from typing import List

@dataclass
class EditBlock:
    start_line: int
    end_line: int
    old_content: str
    new_content: str
    description: str

class DiffGenerator:
    """Generate and apply code diffs"""

    def generate_edit_prompt(self, filename: str, code: str, instructions: str) -> str:
        """Generate prompt that asks for edit blocks, not full file"""

    def parse_edit_blocks(self, model_response: str) -> List[EditBlock]:
        """Parse model output into edit blocks"""

    def apply_edits(self, original: str, edits: List[EditBlock]) -> str:
        """Apply edit blocks to original code"""

    def validate_edits(self, original: str, edits: List[EditBlock]) -> List[str]:
        """Validate edits won't break the file"""
```

#### 4.5.2 Update File Tools

**Modified File:** `core/tools.py`

```python
class FileTools:
    # ... existing methods ...

    def patch_file(self, filename: str, edits: List[EditBlock]) -> dict:
        """Apply diff-based edits to file"""
        # Read original
        read_result = self.read_file(filename)
        if not read_result['success']:
            return read_result

        original = read_result['content']

        # Backup
        backup_path = self._backup_file(filename)

        # Apply edits
        from core.diff_generator import DiffGenerator
        diff_gen = DiffGenerator()

        # Validate
        errors = diff_gen.validate_edits(original, edits)
        if errors:
            return {'success': False, 'error': f"Invalid edits: {errors}"}

        # Apply
        new_content = diff_gen.apply_edits(original, edits)

        # Write
        return self.write_file(filename, new_content, overwrite=True)
```

#### 4.5.3 Deliverables

- [ ] `core/diff_generator.py` - Diff parsing and application
- [ ] Update `core/tools.py` - patch_file method
- [ ] Update `models/coder.py` - Generate edits instead of full files
- [ ] Tests for diff application

**Stable After Phase 5:** Edits use 10x fewer tokens on large files.

---

## 5. Performance & Mobile Constraints

### 5.1 Model Lifecycle Management Strategy

```python
# models/lifecycle.py - Key strategies

class ModelLifecycleManager:
    def __init__(self, config):
        self.memory_budget_mb = config.get("memory_budget_mb", 6000)
        self.unload_cooldown_seconds = 60
        self._last_used: Dict[ModelRole, float] = {}

    def _enforce_memory_limit(self, required_mb: int) -> None:
        """Unload models to fit within budget"""
        current_usage = self._get_total_memory_usage()

        if current_usage + required_mb <= self.memory_budget_mb:
            return  # Fits within budget

        # Unload strategy: LRU (Least Recently Used)
        unload_order = sorted(
            [r for r in ModelRole if self.models[r] is not None],
            key=lambda r: self._last_used.get(r, 0)
        )

        for role in unload_order:
            if role == ModelRole.ROUTER:
                continue  # Never unload router

            self.unload_model(role)
            current_usage = self._get_total_memory_usage()

            if current_usage + required_mb <= self.memory_budget_mb:
                break

    def schedule_unload(self, role: ModelRole, delay_seconds: int) -> None:
        """Schedule model unload after inactivity"""
        # Implementation using threading.Timer or asyncio
```

### 5.2 Load/Unload Strategy

| Model | Load Trigger | Unload Trigger |
|-------|-------------|----------------|
| **Router** | App startup | Never (always resident) |
| **Primary Coder** | First coding task | 60s inactivity OR algorithm load |
| **Algorithm Specialist** | Explicit escalation | 30s after task completion |

### 5.3 RAM and Context Minimization

```python
# Context distillation - don't send full conversation to coder

class ContextDistiller:
    """Reduce context before sending to coder models"""

    def distill_for_coder(self, conversation: List[dict], task: CodingTask) -> str:
        """Extract only relevant context for coding task"""
        # 1. Include only the current task description
        # 2. Include relevant file contents (not entire conversation)
        # 3. Include recent error messages if debugging
        # 4. Exclude unrelated chat history

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: chars/4)"""
        return len(text) // 4

    def truncate_to_fit(self, context: str, max_tokens: int) -> str:
        """Truncate context to fit model's limit"""
```

### 5.4 Avoiding Redundant Inference

```python
# core/inference_cache.py

class InferenceCache:
    """Cache recent inference results"""

    def __init__(self, max_entries: int = 100):
        self._cache: Dict[str, CacheEntry] = {}

    def get_cached_intent(self, user_input: str) -> Optional[IntentResult]:
        """Check if we've classified this input before"""
        key = self._hash_input(user_input)
        entry = self._cache.get(key)

        if entry and not entry.is_expired():
            return entry.result
        return None

    def cache_intent(self, user_input: str, result: IntentResult) -> None:
        """Cache intent classification result"""

    # Cache hit scenarios:
    # - "git status" always classifies the same way
    # - "list files" always classifies the same way
    # - Recent variations of same question
```

### 5.5 Android/Termux Constraints

| Constraint | Mitigation |
|------------|------------|
| **Limited RAM (8-12GB)** | Memory budget enforcement, aggressive unloading |
| **Thermal throttling** | Inference cooldown periods, batch size limits |
| **No swap** | Never exceed physical RAM, fail gracefully |
| **Background app kills** | Fast state serialization, recovery on restart |
| **Storage I/O** | Use mmap for model loading, minimize writes |

```python
# utils/mobile_detector.py

class MobileDetector:
    """Detect mobile constraints and adjust defaults"""

    def detect_platform(self) -> str:
        """Detect: 'android_termux', 'linux', 'macos', 'windows'"""

    def get_recommended_settings(self) -> dict:
        """Return platform-appropriate defaults"""
        if self.detect_platform() == "android_termux":
            return {
                "memory_budget_mb": 5000,
                "router_context_size": 1024,
                "coder_context_size": 4096,
                "unload_cooldown_seconds": 30,
                "max_concurrent_models": 2,
            }
```

---

## 6. Developer Experience & Extensibility

### 6.1 How This Refactor Improves Maintainability

| Before | After | Benefit |
|--------|-------|---------|
| 1,114-line engine_v2.py | ~200-line engine_v3.py + focused modules | Easier to understand and modify |
| Single model manager | Role-based model lifecycle | Clear model responsibilities |
| Regex intent parsing | Model-based with regex fallback | More robust, easier to improve |
| Direct model.generate() in agents | Agents call typed model interfaces | Testable, mockable |
| Hardcoded S24 Ultra settings | Platform detection + config | Works on any hardware |

### 6.2 Adding New Models

```python
# To add a new specialist model (e.g., "security" for vulnerability detection):

# 1. Create model wrapper
# models/security_model.py
class SecuritySpecialist(BaseModel):
    def scan(self, code: str) -> SecurityResult:
        ...

# 2. Add to ModelRole enum
# models/lifecycle.py
class ModelRole(Enum):
    ROUTER = "router"
    CODER = "coder"
    ALGORITHM = "algorithm"
    SECURITY = "security"  # New

# 3. Add config section
# config.json
"models": {
    ...
    "security": {
        "path": "security-coder-7b.Q4_K_M.gguf",
        "context_size": 4096,
        "always_resident": false
    }
}

# 4. Add routing rule
# router/intent_router.py
"security_task": {
    "patterns": [r"security|vulnerability|CVE|injection|XSS"],
    "escalate_to": "security"
}
```

### 6.3 Adding New Tools

```python
# To add a new tool (e.g., "docker"):

# 1. Create tool handler
# executor/docker_handler.py
class DockerHandler:
    def build(self, dockerfile: str, tag: str) -> ToolResult:
        ...
    def run(self, image: str, command: str) -> ToolResult:
        ...

# 2. Register in ToolExecutor
# executor/tool_executor.py
self._tool_handlers = {
    ...
    "docker": DockerHandler(self.permissions),
}

# 3. Add patterns to router
# router/prompts.py
TOOL_PATTERNS["docker"] = [r"docker\s+(build|run|ps|images)"]
```

### 6.4 Interfaces and Contracts

```python
# contracts.py - Enforced interfaces

from abc import ABC, abstractmethod
from typing import Protocol

class ModelProtocol(Protocol):
    """All models must implement"""
    def load(self) -> None: ...
    def unload(self) -> None: ...
    def generate(self, prompt: str, **kwargs) -> str: ...
    @property
    def loaded(self) -> bool: ...

class ToolHandlerProtocol(Protocol):
    """All tool handlers must implement"""
    def execute(self, params: dict) -> ToolResult: ...
    def validate_params(self, params: dict) -> List[str]: ...

class RouterProtocol(Protocol):
    """Router must implement"""
    def classify(self, user_input: str, context: dict) -> IntentResult: ...
```

### 6.5 Future-Proofing Decisions

| Decision | Rationale |
|----------|-----------|
| **BaseModel abstract class** | Swap llama.cpp for other backends (MLX, GGML, etc.) |
| **IntentResult dataclass** | Add new fields without breaking existing code |
| **ModelRole enum** | Add new roles without changing lifecycle logic |
| **Config-driven model paths** | Change models without code changes |
| **ToolResult generic** | Different tools can return different payloads |
| **Prompt templates in separate file** | Iterate on prompts without touching logic |

---

## 7. Directory Structure After Refactoring

```
codey/
├── cli/
│   ├── __init__.py
│   ├── main.py              # Entry point (uses engine_v3)
│   └── colors.py            # ANSI colors
│
├── core/
│   ├── __init__.py
│   ├── engine_v3.py         # NEW: Lightweight orchestrator
│   ├── engine_v2.py         # DEPRECATED: Legacy (kept for fallback)
│   ├── engine.py            # DEPRECATED: v1 engine
│   ├── orchestrator.py      # NEW: Model/tool coordination
│   ├── task_planner.py      # NEW: Complex instruction handling
│   ├── response_handler.py  # NEW: Output formatting
│   ├── diff_generator.py    # NEW: Diff-based editing
│   ├── tools.py             # UPDATED: Added patch_file
│   ├── parser.py            # DEPRECATED: Use router instead
│   ├── permission_manager.py
│   ├── git_manager.py
│   └── shell_manager.py
│
├── router/
│   ├── __init__.py
│   ├── intent_router.py     # NEW: Intent classification
│   ├── prompts.py           # NEW: Router prompt templates
│   └── classification.py    # NEW: Intent patterns/rules
│
├── executor/
│   ├── __init__.py
│   ├── tool_executor.py     # NEW: Tool orchestration
│   ├── git_handler.py       # NEW: Git-specific handling
│   ├── shell_handler.py     # NEW: Shell-specific handling
│   └── file_handler.py      # NEW: File-specific handling
│
├── models/
│   ├── __init__.py
│   ├── base.py              # NEW: Abstract base model
│   ├── lifecycle.py         # NEW: Multi-model management
│   ├── manager.py           # UPDATED: Legacy wrapper
│   ├── coder.py             # NEW: Qwen2.5-Coder wrapper
│   ├── algorithm_model.py   # NEW: DeepSeek-Coder wrapper
│   └── router_model.py      # NEW: FunctionGemma wrapper
│
├── agents/
│   ├── __init__.py
│   ├── coding_agent.py      # UPDATED: Uses PrimaryCoder
│   ├── debug_agent.py       # UPDATED: Uses PrimaryCoder
│   ├── todo_planner.py      # (unchanged)
│   └── perplexity_api.py    # (unchanged)
│
├── memory/
│   ├── __init__.py
│   └── store.py             # (unchanged)
│
├── utils/
│   ├── __init__.py
│   ├── config.py            # UPDATED: Multi-model config
│   ├── mobile_detector.py   # NEW: Platform detection
│   ├── inference_cache.py   # NEW: Response caching
│   ├── context_distiller.py # NEW: Context reduction
│   ├── cleanup.py
│   └── command_logger.py
│
├── contracts.py             # NEW: Interface definitions
├── codey                    # Entry point script
├── config.example.json      # UPDATED: Multi-model config
├── requirements.txt
├── README.md
├── REFACTORING_PLAN.md      # This document
└── EXECUTIVE_REVIEW.md
```

---

## 8. Implementation Priority & Timeline

| Phase | Effort | Dependencies | Shippable? |
|-------|--------|--------------|------------|
| **Phase 1: Model Lifecycle** | 2-3 days | None | Yes (backward compat) |
| **Phase 2: Intent Router** | 3-4 days | Phase 1 | Yes (new routing live) |
| **Phase 3: Specialized Models** | 3-4 days | Phases 1-2 | Yes (multi-model works) |
| **Phase 4: Engine Decomposition** | 2-3 days | Phases 1-3 | Yes (clean architecture) |
| **Phase 5: Diff-Based Editing** | 2-3 days | Phase 3 | Yes (faster edits) |

**Total Estimated Effort:** 12-17 days

---

## 9. Success Criteria

### 9.1 Functional Criteria

- [ ] Router classifies intents with >85% accuracy on test set
- [ ] Tool calls complete without loading coder model
- [ ] Coding tasks use appropriate model (coder vs. algorithm)
- [ ] Memory usage stays within 6GB budget during typical usage
- [ ] Existing tests pass after each phase

### 9.2 Performance Criteria

- [ ] "git status" latency <300ms (router only)
- [ ] Simple file creation latency <10s (coder load + inference)
- [ ] Algorithm task escalation adds <6s (model swap)
- [ ] No OOM crashes on 8GB Android devices

### 9.3 Code Quality Criteria

- [ ] Engine v3 <200 lines
- [ ] Each new module has >80% test coverage
- [ ] No circular imports
- [ ] All models implement BaseModel interface
- [ ] All tools implement ToolResult pattern

---

## 10. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FunctionGemma accuracy too low | Medium | High | Fall back to Phi-3 Mini; keep regex fallback |
| Model swap latency unacceptable | Medium | Medium | Preload likely models; optimize mmap loading |
| Qwen/DeepSeek unavailable in GGUF | Low | High | Use alternative models (CodeLlama, Mistral) |
| Breaking backward compatibility | Medium | Medium | Keep engine_v2 as fallback; feature flag |
| Diff-based editing introduces bugs | Medium | Medium | Validate edits before applying; keep backups |

---

## Appendix A: Model Acquisition

```bash
# Download recommended models

# Router (choose one)
# Option 1: FunctionGemma 270M (~200MB)
huggingface-cli download google/functiongemma-2b --local-dir ~/codey/LLM_Models/

# Option 2: Phi-3 Mini (if Gemma unavailable)
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf \
  -O ~/codey/LLM_Models/phi-3-mini-4k-instruct.Q4_K_M.gguf

# Primary Coder: Qwen2.5-Coder 7B
wget https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  -O ~/codey/LLM_Models/qwen2.5-coder-7b-instruct.Q4_K_M.gguf

# Algorithm Specialist: DeepSeek-Coder 6.7B
wget https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf \
  -O ~/codey/LLM_Models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf
```

---

## Appendix B: Sample Config After Refactor

```json
{
  "models": {
    "router": {
      "path": "phi-3-mini-4k-instruct.Q4_K_M.gguf",
      "context_size": 2048,
      "n_gpu_layers": 10,
      "always_resident": true
    },
    "coder": {
      "path": "qwen2.5-coder-7b-instruct.Q4_K_M.gguf",
      "context_size": 8192,
      "n_gpu_layers": 35,
      "always_resident": false,
      "unload_after_seconds": 60,
      "temperature": 0.3,
      "max_tokens": 2048
    },
    "algorithm": {
      "path": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
      "context_size": 8192,
      "n_gpu_layers": 35,
      "always_resident": false,
      "unload_after_seconds": 30,
      "temperature": 0.2,
      "max_tokens": 4096
    }
  },
  "memory_budget_mb": 6000,
  "platform": "auto",

  "routing": {
    "confidence_threshold_tool": 0.90,
    "confidence_threshold_simple": 0.85,
    "confidence_threshold_code": 0.70,
    "enable_regex_fallback": true,
    "cache_intent_results": true
  },

  "model_dir": "~/codey/LLM_Models",
  "memory_dir": "~/codey/memory",
  "log_dir": "~/codey/logs",
  "workspace_dir": "~/codey/workspace",

  "safety": {
    "require_confirmation": true,
    "backup_before_edit": true
  },

  "perplexity": {
    "api_key": "",
    "enabled": false,
    "fallback_on_local_failure": true
  }
}
```

---

**END OF REFACTORING PLAN**

*This plan is designed to be executed incrementally. Each phase produces a working system. Implement Phase 1 first, verify stability, then proceed.*
