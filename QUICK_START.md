# Codey Phase 1 - Quick Start Guide

## 🎉 Phase 1 Complete!

Multi-model architecture with lifecycle management is now implemented and ready for testing.

---

## Quick Test (5 minutes)

```bash
cd ~/codey
python3 test_phase1.py
```

Expected output: **5/5 tests passing** ✅

---

## What Changed?

### New Multi-Model Architecture

Codey now supports 3 specialized models:

| Model | Role | Size | Usage |
|-------|------|------|-------|
| FunctionGemma 270M | Intent Router | ~335MB | Always-on |
| Qwen2.5-Coder 7B | Primary Coder | ~5.3GB | On-demand |
| DeepSeek-Coder 6.7B | Algorithm Specialist | ~5.0GB | Cold-loaded |

### Smart Memory Management

- **Memory Budget**: 6000MB (configurable)
- **LRU Unloading**: Automatically unloads least-used models
- **Always-Resident**: Router stays loaded for fast responses

---

## Testing

### 1. Integration Test (Recommended)

```bash
cd ~/codey
python3 test_phase1.py
```

Tests:
- ✓ Router model loads and generates
- ✓ Coder model loads and generates
- ✓ Algorithm model loads and generates
- ✓ Model swapping works correctly
- ✓ Legacy code still works

### 2. Unit Tests (Optional)

```bash
pip install pytest  # if not installed
pytest tests/test_lifecycle.py -v
```

### 3. Interactive Test

```python
cd ~/codey
python3

from models.lifecycle import ModelLifecycleManager, ModelRole
from utils.config import Config

config = Config()
lifecycle = ModelLifecycleManager(config)

# Load and test router
router = lifecycle.load_model(ModelRole.ROUTER)
print(router.generate("Hello", max_tokens=20))

# Check memory usage
print(lifecycle.get_memory_usage())

# Cleanup
lifecycle.unload_all()
```

---

## Configuration

Config file: `~/codey/config.json`

Generated automatically on first run. Points to `~/LLM_Models/`:

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
      "context_size": 8192
    },
    "algorithm": {
      "path": "deepseek-coder-6.7b-instruct-q4_k_m.gguf",
      "context_size": 8192
    }
  },
  "memory_budget_mb": 6000
}
```

---

## Documentation

- **PHASE1_TESTING.md** - Complete testing guide
- **PHASE1_COMPLETE.md** - Implementation summary
- **REFACTORING_PLAN.md** - Full architecture plan

---

## Files Added

```
models/
├── base.py              # Abstract model interface
└── lifecycle.py         # Multi-model manager

tests/
├── __init__.py
└── test_lifecycle.py    # Unit tests

test_phase1.py           # Integration test
PHASE1_TESTING.md        # Testing guide
PHASE1_COMPLETE.md       # Summary
```

---

## Backward Compatibility

**Existing code works unchanged!**

```python
# Old code still works
from models.manager import ModelManager
manager = ModelManager(config)
manager.load_model()
response = manager.generate("Hello", max_tokens=50)
```

Behind the scenes, `ModelManager` now delegates to `ModelLifecycleManager`.

---

## Troubleshooting

### Models Not Found

```bash
ls ~/LLM_Models/*.gguf
```

Should show:
- `functiongemma-270m-it-Q8_0.gguf`
- `qwen2.5-coder-7b-instruct-q4_k_m.gguf`
- `deepseek-coder-6.7b-instruct-q4_k_m.gguf`

### Import Errors

```bash
pip install llama-cpp-python
```

### Out of Memory

Edit `config.json`:
```json
"memory_budget_mb": 4000
```

---

## Next Steps

1. ✅ **Test Phase 1** - `python3 test_phase1.py`
2. ⏳ **Phase 2** - Intent Router (TBD)
3. ⏳ **Phase 3** - Specialized model wrappers (TBD)
4. ⏳ **Phase 4** - Engine decomposition (TBD)
5. ⏳ **Phase 5** - Diff-based editing (TBD)

---

## Git Status

✅ **Committed**: Commit `1bcdd0f`
✅ **Pushed**: GitHub updated

View on GitHub:
```
https://github.com/Ishabdullah/codey
```

---

## Questions?

See documentation:
- Testing issues → `PHASE1_TESTING.md`
- Architecture questions → `REFACTORING_PLAN.md`
- Implementation details → `PHASE1_COMPLETE.md`

---

**Status: Phase 1 Complete ✅**

Run `python3 test_phase1.py` to verify everything works!
