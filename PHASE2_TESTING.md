# Phase 2 Testing Guide

Testing instructions for Phase 2: Intent Router & Tool Executor

---

## What's New in Phase 2

Phase 2 introduces intelligent intent routing and direct tool execution:

- **Intent Router** (FunctionGemma 270M) - Always-on model that classifies user intent
- **Tool Executor** - Executes tools (git, shell, file) without loading heavy models
- **Orchestrator** - Central coordinator that routes requests to the right handler
- **Regex Fallback** - Falls back to pattern matching when model confidence is low

---

## Quick Test (5 minutes)

```bash
cd ~/codey
python3 test_phase2.py
```

Expected: **5/5 tests passing** ✅

---

## What Gets Tested

### Test 1: Intent Classification

Tests router's ability to classify different types of requests:

```
Input: "git status" → intent: tool_call, tool: git
Input: "list files" → intent: tool_call, tool: file
Input: "create a file test.py" → intent: coding_task
Input: "implement quicksort" → intent: algorithm_task
Input: "what is python?" → intent: simple_answer
```

### Test 2: Tool Execution

Tests direct tool execution without model loading:

```
- Git operations (status, commit, push)
- File operations (list, read, delete)
- Shell commands (mkdir, run, install)
```

### Test 3: Orchestrator Integration

Tests end-to-end flow:

```
User Input → Intent Router → Tool Executor/Model → Response
```

### Test 4: Regex Fallback

Tests fallback when model confidence is low:

```
Input: "git log"
Input: "mkdir test_dir"
Input: "read test.py"
```

### Test 5: Memory Efficiency

Verifies only the router model is loaded (not coder or algorithm):

```
✓ Router: LOADED (~335 MB)
✓ Coder: NOT LOADED (0 MB)
✓ Algorithm: NOT LOADED (0 MB)
```

---

## Manual Testing

### Test Intent Classification

```bash
cd ~/codey
python3
```

```python
from router.intent_router import IntentRouter
from utils.config import Config
from models.lifecycle import ModelLifecycleManager, ModelRole

config = Config()
lifecycle = ModelLifecycleManager(config)

# Load router
router_model = lifecycle.load_model(ModelRole.ROUTER)
router = IntentRouter(router_model.model_path, router_model.config)
router._model = router_model._model
router._loaded = True

# Test classification
result = router.classify("git status")
print(f"Intent: {result.intent}")
print(f"Tool: {result.tool}")
print(f"Confidence: {result.confidence}")

# Test more
result = router.classify("create a python file")
print(f"Intent: {result.intent}")
print(f"Escalate to: {result.escalate_to}")

# Cleanup
lifecycle.unload_all()
exit()
```

### Test Tool Executor

```python
from executor.tool_executor import ToolExecutor
from core.git_manager import GitManager
from core.shell_manager import ShellManager
from core.tools import FileTools
from core.permission_manager import PermissionManager
from utils.config import Config

config = Config()
perm = PermissionManager(config)
git = GitManager(perm, config.workspace_dir)
shell = ShellManager(perm, config.workspace_dir, config)
files = FileTools(config)

executor = ToolExecutor(git, shell, files, perm)

# Test git status
result = executor.execute("git", {"action": "status"})
print(f"Success: {result.success}")
print(f"Output: {result.output}")

# Test file list
result = executor.execute("file", {"raw_input": "list files"})
print(f"Files: {result.output}")

exit()
```

### Test Orchestrator

```python
from core.orchestrator import Orchestrator
from utils.config import Config
from models.lifecycle import ModelLifecycleManager
# ... (create executor as above)

lifecycle = ModelLifecycleManager(config)
orchestrator = Orchestrator(config, lifecycle, executor)

# Process requests
response = orchestrator.process("git status")
print(response)

response = orchestrator.process("list files")
print(response)

response = orchestrator.process("what is python?")
print(response)

# Cleanup
orchestrator.shutdown()
exit()
```

---

## Expected Outputs

### Intent Classification

```
Input: "git status"
  Intent: tool_call (confidence: 0.99)
  Tool: git
  Escalate to: None
  Used fallback: False
  ✓ PASS
```

### Tool Execution

```
Test: Git Status
  ✓ PASS: git status executed

Test: List Files
  ✓ PASS: file list executed
  Files: 15
```

### Orchestrator

```
Input: 'git status'
  Response preview: ✓ Working directory is clean...
  ✓ PASS
```

---

## Troubleshooting

### Router Model Not Loading

**Error:** `FileNotFoundError: Model file not found`

**Solution:**
```bash
ls ~/LLM_Models/functiongemma*
# Verify router model exists

# If missing, download:
# See PHASE1_TESTING.md for download instructions
```

### JSON Parse Errors

**Error:** `JSON parse error: ...`

**Solution:**
This is normal! The router will fall back to regex patterns automatically.

### Low Confidence Warnings

**Warning:** `confidence: 0.50`

**Solution:**
Router uses regex fallback for uncertain cases. This is expected behavior.

---

## Success Criteria

Phase 2 is complete when:

- ✅ All 5 integration tests pass
- ✅ Router classifies intents correctly
- ✅ Tool executor runs without loading heavy models
- ✅ Orchestrator coordinates requests properly
- ✅ Fallback works when needed
- ✅ Only router model is loaded (~335 MB)

---

## Performance Benchmarks

Expected performance on S24 Ultra:

| Operation | Time |
|-----------|------|
| Intent classification | ~100-300ms |
| Git status (tool exec) | ~50ms |
| File list (tool exec) | ~10ms |
| Simple answer | ~500ms |

Total: Most requests complete in <1 second

---

## Comparison: Phase 1 vs Phase 2

| Metric | Phase 1 | Phase 2 |
|--------|---------|---------|
| Models loaded | 1 (7B, ~5.3GB) | 1 (270M, ~335MB) |
| Tool call latency | ~5-10s | ~100-500ms |
| Intent accuracy | Regex only | Model + fallback |
| Memory efficient | No | Yes |

Phase 2 is **10-100x faster** for tool operations!

---

## Next Steps

After Phase 2 passes:

1. **Commit changes** (see commands in PHASE2_COMPLETE.md)
2. **Update README.md** with Phase 1 + 2 changes
3. **Phase 3** - Specialized model wrappers (Qwen/DeepSeek)

---

## Known Limitations

Phase 2 limitations (to be addressed in Phase 3):

- **Coding tasks** return placeholder messages (need Qwen2.5-Coder integration)
- **Algorithm tasks** return placeholder messages (need DeepSeek integration)
- **Simple answers** use router model (basic, not specialized)

These will be fully functional in Phase 3!

---

## Documentation

- **PHASE2_TESTING.md** (this file) - Testing guide
- **PHASE1_TESTING.md** - Phase 1 testing
- **REFACTORING_PLAN.md** - Full architecture plan
- **QUICK_START.md** - Quick reference

---

**Status: Phase 2 Ready for Testing**

Run `python3 test_phase2.py` to verify!
