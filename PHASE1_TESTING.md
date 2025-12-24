# Phase 1 Testing Guide

This guide provides complete instructions for testing the Phase 1 implementation of Codey's multi-model architecture.

---

## Prerequisites

### Required Models

Ensure the following GGUF models are in `~/LLM_Models/`:

```bash
ls -lh ~/LLM_Models/
```

Expected output should include:
- `functiongemma-270m-it-Q8_0.gguf` (~279MB) - Router model
- `qwen2.5-coder-7b-instruct-q4_k_m.gguf` (~4.4GB) - Primary coder
- `deepseek-coder-6.7b-instruct-q4_k_m.gguf` (~3.9GB) - Algorithm specialist

### Python Environment

Phase 1 requires:
- Python 3.8+
- llama-cpp-python library

---

## Step 1: Activate Python Environment

### In UserLAnd/Termux:

```bash
# Navigate to Codey directory
cd ~/codey

# If you have a virtual environment, activate it
# source venv/bin/activate

# Verify llama-cpp-python is installed
python3 -c "import llama_cpp; print('llama-cpp-python installed:', llama_cpp.__version__)"
```

If not installed:

```bash
pip install llama-cpp-python
```

---

## Step 2: Clean Configuration (Fresh Start)

Remove old config to force generation of new multi-model config:

```bash
# Backup old config
cp ~/codey/config.json ~/codey/config.json.backup 2>/dev/null || true

# Remove old config to trigger new default generation
rm -f ~/codey/config.json
```

---

## Step 3: Run Phase 1 Integration Tests

### Quick Test (Recommended First)

Run the integration test script:

```bash
cd ~/codey
python3 test_phase1.py
```

### Expected Output

The test will run 5 test suites:

```
======================================================================
  PHASE 1 INTEGRATION TEST
  Multi-Model Architecture - Model Lifecycle Manager
======================================================================

Loading configuration...
✓ Config loaded
  Model directory: /home/userland/LLM_Models
  Memory budget: 6000 MB

Creating ModelLifecycleManager...
ModelLifecycleManager initialized
Memory budget: 6000 MB
✓ Lifecycle manager created

======================================================================
  TEST 1: Router Model (FunctionGemma 270M)
======================================================================

Loading router model...
Loading functiongemma-270m-it-Q8_0.gguf...
✓ Loaded functiongemma-270m-it-Q8_0.gguf
  Context: 2048 tokens, GPU layers: 10, Threads: 4
✓ Router loaded: functiongemma-270m-it-Q8_0.gguf

📊 Memory Usage:
   Total: 335 MB / 6000 MB
   Utilization: 5.6%
   Available: 5665 MB

   Per Model:
     ✓ router      : 335 MB (functiongemma-270m-it-Q8_0.gguf)
     ○ coder       : not loaded
     ○ algorithm   : not loaded

Generating test output...

Prompt: Classify this intent: create a file called test.py
Response: [model output...]

[Similar output for TEST 2, 3, 4, 5...]

======================================================================
  TEST SUMMARY
======================================================================
  ✓ PASS: router
  ✓ PASS: coder
  ✓ PASS: algorithm
  ✓ PASS: swapping
  ✓ PASS: backward_compat

  Total: 5 tests
  Passed: 5
  Failed: 0

======================================================================
  🎉 ALL TESTS PASSED - PHASE 1 COMPLETE!
======================================================================
```

### Understanding Test Results

| Test | What It Validates |
|------|-------------------|
| **router** | FunctionGemma 270M loads and generates text |
| **coder** | Qwen2.5-Coder 7B loads and generates code |
| **algorithm** | DeepSeek-Coder 6.7B loads and generates algorithms |
| **swapping** | LRU unloading works, memory management is correct |
| **backward_compat** | Legacy ModelManager still works with new backend |

---

## Step 4: Run Unit Tests (Optional)

For more granular testing:

```bash
# Install pytest if needed
pip install pytest

# Run unit tests
cd ~/codey
pytest tests/test_lifecycle.py -v
```

Expected output:

```
tests/test_lifecycle.py::TestModelLifecycleManager::test_initialization PASSED
tests/test_lifecycle.py::TestModelLifecycleManager::test_model_configs_loaded PASSED
tests/test_lifecycle.py::TestModelLifecycleManager::test_memory_budget PASSED
tests/test_lifecycle.py::TestModelLifecycleManager::test_get_memory_usage_empty PASSED
tests/test_lifecycle.py::TestModelLifecycleManager::test_load_router_model PASSED
tests/test_lifecycle.py::TestModelLifecycleManager::test_unload_model PASSED
tests/test_lifecycle.py::TestModelLifecycleManager::test_ensure_loaded PASSED
tests/test_lifecycle.py::TestModelLifecycleManager::test_get_model_info PASSED
tests/test_lifecycle.py::TestModelLifecycleManager::test_unload_all PASSED
...
```

---

## Step 5: Manual Testing (Interactive)

Test the lifecycle manager interactively:

```bash
cd ~/codey
python3
```

```python
# Import required modules
from utils.config import Config
from models.lifecycle import ModelLifecycleManager, ModelRole

# Create config and lifecycle manager
config = Config()
lifecycle = ModelLifecycleManager(config)

# Check initial memory usage
print(lifecycle.get_memory_usage())

# Load router model
router = lifecycle.load_model(ModelRole.ROUTER)
print(f"Router loaded: {router.loaded}")

# Generate text
response = router.generate("Hello world", max_tokens=20)
print(f"Generated: {response}")

# Check memory usage
print(lifecycle.get_memory_usage())

# Load coder model
coder = lifecycle.load_model(ModelRole.CODER)
print(f"Coder loaded: {coder.loaded}")

# Unload router
lifecycle.unload_model(ModelRole.ROUTER)
print(lifecycle.get_memory_usage())

# Unload all
lifecycle.unload_all()
print(lifecycle.get_memory_usage())

# Exit
exit()
```

---

## Step 6: Test Legacy Compatibility

Test that existing code still works:

```bash
cd ~/codey
python3
```

```python
from utils.config import config
from models.manager import ModelManager

# Create legacy manager
manager = ModelManager(config)

# Should print: "ModelManager: Using ModelLifecycleManager backend"

# Load model (uses coder by default)
manager.load_model()

# Generate
response = manager.generate("def fibonacci(n):", max_tokens=100)
print(response)

# Unload
manager.unload_model()

exit()
```

---

## Step 7: Verify Configuration File

Check that the new config was generated:

```bash
cat ~/codey/config.json | python3 -m json.tool
```

Should show the new multi-model structure:

```json
{
  "models": {
    "router": {
      "path": "functiongemma-270m-it-Q8_0.gguf",
      "context_size": 2048,
      "n_gpu_layers": 10,
      ...
    },
    "coder": {
      "path": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
      ...
    },
    "algorithm": {
      "path": "deepseek-coder-6.7b-instruct-q4_k_m.gguf",
      ...
    }
  },
  "memory_budget_mb": 6000,
  ...
}
```

---

## Troubleshooting

### Issue: Model Not Found

**Error:** `FileNotFoundError: Model file not found: ...`

**Solution:**
```bash
# Check model directory
ls ~/LLM_Models/

# Update config.json to point to correct model files
nano ~/codey/config.json
```

### Issue: Out of Memory

**Error:** Models fail to load or system becomes unresponsive

**Solution:**
```bash
# Reduce memory budget in config.json
nano ~/codey/config.json

# Change:
"memory_budget_mb": 4000  # Reduce from 6000
```

### Issue: llama-cpp-python Import Error

**Error:** `ModuleNotFoundError: No module named 'llama_cpp'`

**Solution:**
```bash
pip install llama-cpp-python

# If that fails, try:
pip install llama-cpp-python --no-cache-dir
```

### Issue: GPU Layer Warning

**Warning:** `GPU layers: 0` instead of expected 35

This is normal if:
- Not running on S24 Ultra or GPU-enabled device
- Models still work (CPU-only mode)

To fix on GPU-enabled device:
```bash
# Verify GPU support
python3 -c "from llama_cpp import Llama; print(Llama.supports_gpu_offload())"
```

---

## Success Criteria

Phase 1 is complete when:

- ✅ All 5 integration tests pass
- ✅ Router model loads and generates text
- ✅ Coder model loads and generates code
- ✅ Algorithm model loads and generates algorithms
- ✅ Models can be loaded/unloaded without errors
- ✅ Memory usage is tracked correctly
- ✅ Legacy ModelManager still works
- ✅ Config file has multi-model structure

---

## Next Steps

After Phase 1 passes:

1. **Commit changes to Git** (see Git commands below)
2. **Proceed to Phase 2** - Intent Router implementation
3. **Keep Phase 1 tests** - Run them before each new phase to ensure no regressions

---

## Performance Benchmarks

Expected timings on S24 Ultra (or similar):

| Operation | Expected Time |
|-----------|---------------|
| Load Router (270M) | ~1-2 seconds |
| Load Coder (7B) | ~4-6 seconds |
| Load Algorithm (6.7B) | ~4-6 seconds |
| Generate 50 tokens | ~2-5 seconds |
| Unload model | <1 second |

On lower-end hardware, times may be 2-3x longer.

---

## Memory Usage Benchmarks

Expected memory usage:

| Model | Approximate RAM |
|-------|-----------------|
| Router (FunctionGemma 270M Q8_0) | ~335 MB |
| Coder (Qwen2.5 7B Q4_K_M) | ~5.3 GB |
| Algorithm (DeepSeek 6.7B Q4_K_M) | ~5.0 GB |

With 6GB budget, you can have:
- Router + Coder loaded
- OR Router + Algorithm loaded
- NOT all three simultaneously (would exceed budget)

---

## Contact & Support

If tests fail or you encounter issues:

1. Check model files exist in `~/LLM_Models/`
2. Verify Python and llama-cpp-python are installed
3. Review error messages in test output
4. Check system RAM availability (`free -h`)
5. Consult REFACTORING_PLAN.md for architecture details
