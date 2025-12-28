# Codey Engine V3: System Audit Report

**Date:** December 28, 2025
**Auditor:** Gemini CLI Agent
**Subject:** Codey Engine V3 (CPU-Only/Local Execution Focus)

---

## 1. Architectural Soundness

**Status:** **Strong Core, Fragile Edges**

The "Lightweight Main Loop" architecture (`engine_v3.py` + `Orchestrator`) is theoretically sound for a resource-constrained environment. Decomposing the system into specialized agents (Router, Coder, Algorithm Specialist) controlled by a central lifecycle manager is the correct approach for running large language models on limited hardware.

**Strengths:**
*   **Decomposition:** Separating the "Router" (FunctionGemma 270M) from the heavy lifters (Qwen/DeepSeek 7B) is excellent. It allows for instant responsiveness on basic queries.
*   **Lifecycle Management:** The `ModelLifecycleManager` is the MVP of this architecture. Explicit memory budgeting (default 6GB) and LRU unloading are essential for preventing system crashes on consumer hardware.
*   **Tool Abstraction:** `ToolExecutor` provides a clean interface for side effects (file/git/shell), separating logic from execution.

**Weaknesses:**
*   **Legacy Debt:** `models/manager.py` contains a confused mix of new lifecycle logic and "legacy single-model" code. This duplication is a bug magnet.
*   **Orchestrator Complexity:** The `Orchestrator` class is becoming a "God Object," handling routing, tool execution, model loading, and response formatting.
*   **Planner Naivety:** `TaskPlanner` relies on simple keyword matching ("then", "after"). It lacks true semantic understanding of dependencies, making it brittle for complex multi-step requests.

## 2. Performance & Latency (CPU-Only)

**Status:** **High Latency Risks, Good Throughput Optimization**

**The Reality of CPU Inference:**
On a CPU, loading a 4-bit quantized 7B model takes 2-10 seconds depending on disk speed, and inference runs at 2-10 tokens/second. Codey's architecture mitigates this by keeping the small router resident, but "Context Switching" between models is the primary latency killer.

**Bottlenecks:**
*   **Model Thrashing:** If a user session alternates between "write code" (Coder model) and "optimize this" (Algorithm model), the system will repeatedly unload/reload gigabytes of data. With a 6GB budget, you cannot keep both 7B models in memory.
*   **Router Warm-up:** Even the small router has a load time.
*   **Token limit enforcement:** The config defaults to 2048/4096 tokens. On CPU, generating 2048 tokens takes minutes. Users may perceive the system as "hanging."

**Optimizations Observed:**
*   **Llama.cpp integration:** Correct usage of `mmap` and thread configuration.
*   **Streaming absence:** The current implementation waits for full generation before returning. On CPU, this makes the system feel unresponsive. **Streaming is critical for CPU UX.**

## 3. Memory Management

**Status:** **Disciplined but Rigid**

**Analysis:**
The `ModelLifecycleManager` enforces a hard cap (default 6000MB). This is safer than OS-managed paging, which freezes the UI.

**Risks:**
*   **Budget vs. Model Size:** A Q4_K_M 7B model is ~4.5GB. The operating system overhead + Python runtime + context KV cache can easily push a 6GB budget to the limit. Two 7B models (9GB+) will never fit.
*   **Fragmentation:** Python's garbage collection (`gc.collect()` is called) doesn't always immediately release memory to the OS, potentially leading to OOM kills despite the manager's best efforts.

## 4. Model Strategy

**Status:** **Aggressive but Logical**

**Model Choices:**
*   **Router (FunctionGemma 270M):** Excellent choice for CPU. Fast enough to feel instant.
*   **Coder (Qwen2.5-Coder 7B):** State-of-the-art for its size. Good balance of speed/quality.
*   **Algorithm (DeepSeek-Coder 6.7B):** A redundant choice? Qwen2.5-Coder 7B outperforms DeepSeek-Coder 6.7B in many benchmarks. Having two distinct 7B models forces unnecessary unloading.
*   **Simple Answer:** The 270M router is used for "simple answers." This model is likely too small to provide coherent factual answers, leading to hallucinations or nonsense.

**Recommendation:**
Consolidate to a **single** 7B model (Qwen2.5-Coder) for *both* coding and algorithmic tasks. The "specialist" distinction adds architectural complexity and latency (loading/unloading) for marginal gain on CPU.

## 5. Reliability & Robustness

**Status:** **Moderate**

**Failure Modes:**
*   **Json Parsing:** The `IntentRouter` relies on LLM JSON output. While there is a regex fallback, 270M models are notoriously bad at adhering to JSON schemas.
*   **Broad Exception Handling:** `try...except Exception` blocks in the main loop mask specific errors (e.g., disk full, permission denied), making debugging difficult.
*   **Zombie Processes:** The `ShellManager` implementation (not deeply reviewed, but referenced) often leaks subprocesses if not carefully managed with timeouts and cleanup signals.

## 6. Developer Experience

**Status:** **Mixed**

*   **Readability:** The code is well-commented and uses type hints.
*   **Maintainability:** The "Phase" artifacts (engine_v3, etc.) clutter the root directory.
*   **Setup:** Dependencies (`llama-cpp-python`) are hardware-sensitive (compilation flags). The current setup assumes a lot about the user's environment.

## 7. Strategic Recommendations

### High Impact / Low Effort (Immediate)
1.  **Merge Coder & Algorithm Roles:** Drop DeepSeek-Coder. Use Qwen2.5-Coder 7B for both. This eliminates model reloading latency for 90% of complex workflows.
2.  **Enable Streaming:** Implement token streaming in `EngineV3.process` and `Orchestrator`. Waiting 60 seconds for a blank screen is unacceptable CPU UX.
3.  **Clean Root:** Move `engine_v3.py` to `core/engine.py` and archive old versions.

### Medium Term (Refactors)
1.  **Better Planner:** Replace keyword matching with a structured prompt to the Router or Coder model to generate a dependency graph.
2.  **Context Management:** Implement a sliding window or summary mechanism for conversation history to prevent hitting the context limit (which slows down CPU inference quadratically).
3.  **Unified Model Manager:** Delete the legacy `ModelManager` wrapper and use `ModelLifecycleManager` exclusively.

### Experimental
1.  **Speculative Decoding:** Use the 270M router to speculatively decode for the 7B model (advanced, might not pay off on RAM-bandwidth constrained CPUs).
