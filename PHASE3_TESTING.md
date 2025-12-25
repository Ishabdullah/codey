# Phase 3 Testing Guide

Testing instructions for Phase 3: Specialized Model Wrappers (Primary Coder + Algorithm Specialist)

---

## What's New in Phase 3

Phase 3 introduces specialized model wrappers for code generation and algorithmic tasks:

- **Primary Coder** (Qwen2.5-Coder 7B) - Code generation, editing, refactoring
- **Algorithm Specialist** (DeepSeek-Coder 6.7B) - Algorithm design, data structures, performance optimization
- **Model Escalation** - Automatic routing between coder and algorithm specialist
- **Full Integration** - Orchestrator now fully functional with all intent types

---

## Quick Test (10 minutes)

```bash
cd ~/codey
python3 test_phase3.py
```

Expected: **6/6 tests passing** ✅

---

## What Gets Tested

### Test 1: Primary Coder - Code Generation

Tests basic code generation with Qwen2.5-Coder:

```
Input: Create a hello world function
Output: Generated Python code with function definition
```

### Test 2: Primary Coder - Escalation Detection

Tests automatic detection of algorithmic tasks:

```
Input: Implement binary search tree
Output: Identifies need for algorithm specialist
```

### Test 3: Algorithm Specialist - Algorithm Generation

Tests algorithm generation with DeepSeek-Coder:

```
Input: Binary search algorithm with O(log n)
Output:
  - Complete implementation
  - Complexity analysis (time/space)
  - Explanation of approach
```

### Test 4: Orchestrator - Coding Task

Tests end-to-end coding task flow:

```
User Input → Router → Primary Coder → Code Result
```

### Test 5: Orchestrator - Algorithm Task

Tests end-to-end algorithm task flow:

```
User Input → Router → Algorithm Specialist → Algorithm Result
```

### Test 6: Model Memory Management

Verifies models are loaded/unloaded correctly:

```
✓ Only necessary models loaded
✓ Memory budget respected
✓ Automatic unloading when needed
```

---

## Manual Testing

### Test Primary Coder

```bash
cd ~/codey
python3
```

```python
from models.lifecycle import ModelLifecycleManager, ModelRole
from models.coder import PrimaryCoder, CodingTask
from utils.config import Config

config = Config()
lifecycle = ModelLifecycleManager(config)

# Load coder model
coder_model = lifecycle.load_model(ModelRole.CODER)
coder = PrimaryCoder(coder_model.model_path, coder_model.config)
coder._model = coder_model._model
coder._loaded = True

# Create a coding task
task = CodingTask(
    task_type="create",
    target_files=["test.py"],
    instructions="Create a function to calculate factorial",
    language="python"
)

# Generate code
result = coder.generate_code(task)
print(f"Success: {result.success}")
if result.code:
    for filename, code in result.code.items():
        print(f"\n{filename}:\n{code}")

# Cleanup
lifecycle.unload_all()
exit()
```

### Test Algorithm Specialist

```python
from models.lifecycle import ModelLifecycleManager, ModelRole
from models.algorithm_model import AlgorithmSpecialist, AlgorithmTask
from utils.config import Config

config = Config()
lifecycle = ModelLifecycleManager(config)

# Load algorithm model
algo_model = lifecycle.load_model(ModelRole.ALGORITHM)
specialist = AlgorithmSpecialist(algo_model.model_path, algo_model.config)
specialist._model = algo_model._model
specialist._loaded = True

# Create algorithm task
task = AlgorithmTask(
    problem_description="Implement merge sort algorithm",
    expected_complexity="O(n log n)",
    language="python",
    optimize_for="time"
)

# Generate solution
result = specialist.solve(task)
print(f"Success: {result.success}")
if result.complexity_analysis:
    print(f"Time: {result.complexity_analysis.get('time')}")
    print(f"Space: {result.complexity_analysis.get('space')}")
if result.code:
    print(f"\nCode:\n{result.code[:300]}...")

# Cleanup
lifecycle.unload_all()
exit()
```

### Test Full Orchestrator

```python
from core.orchestrator import Orchestrator
from utils.config import Config
from models.lifecycle import ModelLifecycleManager
from executor.tool_executor import ToolExecutor
# ... (see test_phase3.py for full setup)

orchestrator = Orchestrator(config, lifecycle, tool_executor)

# Test coding task
response = orchestrator.process("Create a file calc.py with basic calculator functions")
print(response)

# Test algorithm task
response = orchestrator.process("Implement quicksort algorithm in Python")
print(response)

# Cleanup
orchestrator.shutdown()
exit()
```

---

## Expected Outputs

### Primary Coder - Code Generation

```
✓ Code generation successful

Generated hello.py:
```python
def greet(name):
    """Return a personalized greeting"""
    return f"Hello, {name}!"
...
```

Explanation: Simple function that takes a name and returns a greeting message.
```

### Algorithm Specialist - Algorithm Generation

```
✓ Algorithm solution generated

Complexity Analysis:
  Time: O(log n)
  Space: O(1)

Approach: Uses iterative binary search...

Implementation:
```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        ...
```
```

---

## Performance Benchmarks

Expected performance on S24 Ultra:

| Operation | Time |
|-----------|------|
| Intent classification | ~100-300ms |
| Coder model load | ~5-8s |
| Algorithm model load | ~5-8s |
| Code generation (simple) | ~3-8s |
| Algorithm generation | ~5-15s |
| Model swap (coder→algo) | ~6-10s |

Total: Simple tasks <10s, complex tasks <30s

---

## Comparison: Phase 2 vs Phase 3

| Feature | Phase 2 | Phase 3 |
|---------|---------|---------|
| Coding tasks | Placeholder only | Fully functional ✅ |
| Algorithm tasks | Placeholder only | Fully functional ✅ |
| Model escalation | Not implemented | Automatic ✅ |
| Complexity analysis | Not available | Available ✅ |
| Code quality | N/A | Production-ready ✅ |

Phase 3 unlocks the full multi-model architecture!

---

## Troubleshooting

### Coder Model Not Loading

**Error:** `FileNotFoundError: Model file not found`

**Solution:**
```bash
ls ~/LLM_Models/qwen*
# Verify Qwen2.5-Coder model exists

# If missing, download (see README.md for instructions)
```

### Algorithm Model Not Loading

**Error:** `FileNotFoundError: Model file not found`

**Solution:**
```bash
ls ~/LLM_Models/deepseek*
# Verify DeepSeek-Coder model exists
```

### Out of Memory During Model Swap

**Error:** Models fail to load

**Solution:** Reduce memory budget in `config.json`:
```json
"memory_budget_mb": 5000
```

### Code Generation Produces Invalid Output

**Issue:** Generated code has syntax errors

**Solution:**
- Try regenerating (models are probabilistic)
- Adjust temperature in config (lower = more conservative)
- Check if task is too complex (may need decomposition)

---

## Success Criteria

Phase 3 is complete when:

- ✅ All 6 integration tests pass
- ✅ Primary Coder generates valid code
- ✅ Algorithm Specialist produces correct algorithms
- ✅ Complexity analysis is included
- ✅ Model escalation works automatically
- ✅ Memory management respects budget

---

## Next Steps

After Phase 3 passes:

1. **Commit changes** - All Phase 3 files to git
2. **Update README.md** - Mark Phase 3 complete
3. **Phase 4** - Engine decomposition (<200 lines)
4. **Phase 5** - Diff-based editing

---

## Known Limitations

Phase 3 limitations (to be addressed in later phases):

- **No diff-based editing** - Full file regeneration (Phase 5 will fix)
- **No streaming** - Wait for complete response
- **No context distillation** - Sends full instructions (could be optimized)
- **Manual file writing** - Orchestrator doesn't auto-write files

These are by design for Phase 3. Future phases will add these features.

---

## Documentation

- **PHASE3_TESTING.md** (this file) - Testing guide
- **PHASE3_COMPLETE.md** - Implementation summary
- **PHASE2_TESTING.md** - Phase 2 testing
- **REFACTORING_PLAN.md** - Full architecture plan

---

**Status: Phase 3 Ready for Testing**

Run `python3 test_phase3.py` to verify!
