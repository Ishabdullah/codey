# Executive Code Review & Roadmap

**Date:** December 18, 2025
**Project:** Codey
**Reviewer:** Codey AI Agent

## 📊 Status Overview

The Codey project is a functional prototype of a local AI coding assistant. The core architecture (Engine-Agent-Manager) is sound and operational. Key integrations (Git, Shell, File System) are working reliably. However, several critical components rely on naive implementations or placeholders that limit scalability and robustness.

## 🔴 Critical Issues & Incomplete Functionality

### 1. `DebugAgent` Incompleteness
*   **Location:** `agents/debug_agent.py`
*   **Issue:** The `_static_analysis` method contains `pass` placeholders for checks like "Unused imports". It currently relies on simple string matching (regex) rather than proper AST traversal for complex analysis.
*   **Impact:** False negatives in debugging; inability to provide deep code insights.

### 2. Inefficient File Editing
*   **Location:** `agents/coding_agent.py`
*   **Issue:** The `edit_file` method requests the LLM to regenerate the *entire* file content (`_build_edit_prompt`).
*   **Impact:** High token usage, slower performance on large files, and increased risk of hallucinations or unintended deletions in parts of the file that shouldn't change.

### 3. Brittle Command Parsing
*   **Location:** `core/parser.py`
*   **Issue:** `CommandParser` uses a fixed dictionary of regex patterns.
*   **Impact:** Fails to understand natural language variations (e.g., "Please whip up a script for..." might be missed if not in the pattern list).

### 4. Heuristic Plan Extraction
*   **Location:** `core/engine_v2.py`
*   **Issue:** `_extract_steps` logic is based on checking for numbered lists or specific keywords.
*   **Impact:** Complex, nested, or unformatted instructions from the user may be parsed incorrectly or ignored.

### 5. Hardware Hardcoding
*   **Location:** `models/manager.py`
*   **Issue:** Code contains specific optimizations for "S24 Ultra" (Snapdragon 8 Gen 3), including thread counts and GPU layer settings.
*   **Impact:** Suboptimal performance or configuration confusion on standard desktop/server hardware.

## 🛣️ Remediation Plan

### Phase 1: Robustness (Immediate)
1.  **Enhance `DebugAgent`**:
    *   Replace regex-based checks with Python's `ast` module.
    *   Implement real unused import detection using `ast.Import` and `ast.Name` nodes.
2.  **Generalize `ModelManager`**:
    *   Move hardware-specific constants (threads, GPU layers) entirely to `config.json`.
    *   Implement a hardware detection utility to set sensible defaults for Desktop vs. Mobile.

### Phase 2: Efficiency (Short Term)
1.  **Implement Diff-Based Editing**:
    *   Modify `CodingAgent` to ask the LLM for a *diff* or a *search-and-replace* block instead of the full file.
    *   Implement a patcher in `FileTools` to apply these changes safely.

### Phase 3: Intelligence (Medium Term)
1.  **LLM-Backed Parsing**:
    *   Update `CommandParser` to fall back to a lightweight LLM call (or the main model) to interpret intent when regex fails.
2.  **Semantic Plan Extraction**:
    *   Refactor `_extract_steps` in `engine_v2.py` to use the LLM to structure the plan into JSON format, ensuring more reliable multi-step execution.

## 📝 Action Items for Next Sprint

- [ ] Refactor `agents/debug_agent.py` to use `ast` for static analysis.
- [ ] Update `models/manager.py` to remove S24 Ultra hardcoding.
- [ ] Create a `patch_file` method in `core/tools.py`.
- [ ] Update `README.md` to reflect these planned improvements.
