"""Primary Coder Model - Qwen2.5-Coder 7B Wrapper

This module provides a specialized wrapper for the Qwen2.5-Coder 7B model,
designed for code generation, editing, refactoring, and review tasks.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import re

from models.base import BaseModel


@dataclass
class CodingTask:
    """Represents a coding task for the Primary Coder"""
    task_type: str  # "create", "edit", "refactor", "fix", "explain", "review"
    target_files: List[str]
    instructions: str
    existing_code: Optional[Dict[str, str]] = None  # filename -> content
    language: str = "python"
    constraints: List[str] = field(default_factory=list)
    context: Optional[str] = None  # Additional context (e.g., project structure)


@dataclass
class CodeResult:
    """Result from code generation or modification"""
    success: bool
    code: Optional[Dict[str, str]] = None  # filename -> content
    explanation: Optional[str] = None
    needs_algorithm_specialist: bool = False
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PrimaryCoder(BaseModel):
    """Qwen2.5-Coder 7B wrapper for code generation and editing

    This model specializes in:
    - Code generation (new files, functions, classes)
    - Multi-file editing and refactoring
    - Code review and quality assessment
    - Bug fixing and optimization
    - Code explanation

    When to escalate to Algorithm Specialist:
    - Algorithm design (sorting, searching, graph algorithms)
    - Data structure implementation (trees, heaps, etc.)
    - Performance-critical optimization
    - Mathematical/computational problems
    """

    SYSTEM_PROMPT = """You are an expert coding assistant. Generate clean, working code.

Rules:
- Write complete, functional code
- Use proper syntax and best practices
- Add brief comments for complex logic
- Output code in markdown code blocks using ```python or ```language

Be concise and direct."""

    # Keywords that trigger algorithm specialist escalation
    ALGORITHM_KEYWORDS = [
        "binary search", "sorting", "graph", "tree", "heap", "hash table",
        "dynamic programming", "algorithm", "data structure", "complexity",
        "O(n)", "optimize performance", "parser", "lexer", "state machine",
        "automaton", "low-latency", "performance-critical"
    ]

    def load(self) -> None:
        """Load model into memory

        Note: In Phase 3, models are loaded by ModelLifecycleManager.
        This method exists to satisfy BaseModel interface.
        """
        if self._loaded:
            return

        # Model should already be loaded by lifecycle manager
        # This is just a placeholder to satisfy abstract method
        self._loaded = True

    def unload(self) -> None:
        """Unload model from memory

        Note: In Phase 3, models are unloaded by ModelLifecycleManager.
        This method exists to satisfy BaseModel interface.
        """
        self._model = None
        self._loaded = False

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt

        Args:
            prompt: Input prompt
            **kwargs: Generation parameters (temperature, max_tokens, stop, etc.)

        Returns:
            Generated text
        """
        if not self._loaded or not self._model:
            raise RuntimeError("Model not loaded. Cannot generate.")

        # Extract parameters
        temperature = kwargs.get('temperature', 0.3)
        max_tokens = kwargs.get('max_tokens', 2048)
        stop = kwargs.get('stop', None)

        # Debug logging
        print(f"\n[DEBUG] Starting generation...")
        print(f"[DEBUG] Temperature: {temperature}, Max tokens: {max_tokens}")
        print(f"[DEBUG] Stop sequences: {stop}")
        print(f"[DEBUG] Prompt preview (first 500 chars):")
        print(f"{prompt[:500]}")
        print(f"[DEBUG] Prompt length: {len(prompt)} characters")
        print(f"[DEBUG] Calling model inference...")

        # Generate using llama-cpp-python with timeout protection
        import time
        import signal
        from contextlib import contextmanager

        @contextmanager
        def timeout(seconds):
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Generation exceeded {seconds} second timeout")

            # Set signal handler (Unix only)
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                yield
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        start_time = time.time()

        try:
            with timeout(120):  # 120 second timeout (CPU inference is slow ~5 tokens/sec)
                response = self._model(
                    prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop,
                    echo=False
                )
        except TimeoutError as e:
            print(f"[ERROR] {e}")
            raise RuntimeError(f"Generation timeout after 120 seconds - check CPU performance")

        elapsed = time.time() - start_time
        print(f"[DEBUG] Generation completed in {elapsed:.2f} seconds")

        # Extract generated text
        if isinstance(response, dict) and 'choices' in response:
            result = response['choices'][0]['text']
            print(f"[DEBUG] Generated {len(result)} characters")
            print(f"[DEBUG] Response preview (first 200 chars): {result[:200]}")
            return result

        return str(response)

    def generate_code(self, task: CodingTask) -> CodeResult:
        """Generate or modify code based on task

        Args:
            task: CodingTask describing what to generate

        Returns:
            CodeResult with generated code or error
        """
        if not self._loaded:
            return CodeResult(
                success=False,
                error="Model not loaded. Call load() first."
            )

        # Check if task should be escalated
        if self._should_escalate(task):
            return CodeResult(
                success=True,
                needs_algorithm_specialist=True,
                explanation="This task involves algorithmic complexity that would benefit from the algorithm specialist."
            )

        # Build prompt based on task type
        prompt = self._build_coding_prompt(task)

        try:
            # Generate code with proper stop sequences
            # Use common markdown and code delimiters
            print(f"[DEBUG] Generating code for task type: {task.task_type}")

            response = self.generate(
                prompt,
                temperature=self.config.get("temperature", 0.3),
                max_tokens=512,  # Reasonable size for code generation
                stop=["</s>", "\n\n\n", "User:", "Human:", "<|im_end|>"]  # Proper stop sequences
            )

            # Parse response
            print(f"[DEBUG] Parsing response...")
            result = self._parse_code_response(response, task)
            print(f"[DEBUG] Parse result: success={result.success}, needs_algo={result.needs_algorithm_specialist}")
            return result

        except Exception as e:
            print(f"[ERROR] Code generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return CodeResult(
                success=False,
                error=f"Code generation failed: {str(e)}"
            )

    def explain_code(self, code: str, filename: str, context: Optional[str] = None) -> str:
        """Explain what code does

        Args:
            code: Code to explain
            filename: Name of file (for language detection)
            context: Optional context about the codebase

        Returns:
            Explanation string
        """
        if not self._loaded:
            return "Error: Model not loaded."

        language = self._infer_language(filename)

        prompt = f"""Explain this {language} code clearly and concisely:

File: {filename}
{f'Context: {context}' if context else ''}

```{language}
{code}
```

Provide a clear explanation covering:
1. What it does (high-level purpose)
2. How it works (key logic)
3. Important details (edge cases, assumptions)

Explanation:"""

        try:
            response = self.generate(
                prompt,
                temperature=0.2,
                max_tokens=512
            )
            return response.strip()
        except Exception as e:
            return f"Error explaining code: {str(e)}"

    def review_code(self, code: str, filename: str, criteria: List[str]) -> Dict[str, Any]:
        """Review code against criteria

        Args:
            code: Code to review
            filename: Filename for context
            criteria: List of review criteria

        Returns:
            Dict with review results
        """
        if not self._loaded:
            return {"error": "Model not loaded"}

        language = self._infer_language(filename)
        criteria_str = "\n".join(f"- {c}" for c in criteria)

        prompt = f"""Review this {language} code against the following criteria:

{criteria_str}

File: {filename}
```{language}
{code}
```

Provide a structured review as JSON:
{{
  "overall_quality": "excellent|good|fair|poor",
  "issues": [
    {{"type": "error|warning|suggestion", "description": "...", "line": null|number}}
  ],
  "strengths": ["..."],
  "recommendations": ["..."]
}}

Review:"""

        try:
            response = self.generate(
                prompt,
                temperature=0.2,
                max_tokens=1024
            )

            # Try to parse JSON response
            try:
                review = json.loads(response.strip())
                return review
            except json.JSONDecodeError:
                # Fallback: return raw response
                return {
                    "overall_quality": "unknown",
                    "raw_review": response.strip()
                }

        except Exception as e:
            return {"error": f"Review failed: {str(e)}"}

    def _should_escalate(self, task: CodingTask) -> bool:
        """Determine if task needs algorithm specialist

        Args:
            task: CodingTask to evaluate

        Returns:
            True if should escalate to algorithm specialist
        """
        # Check task instructions for algorithm keywords
        instructions_lower = task.instructions.lower()

        for keyword in self.ALGORITHM_KEYWORDS:
            if keyword in instructions_lower:
                return True

        # Check constraints
        for constraint in task.constraints:
            constraint_lower = constraint.lower()
            for keyword in self.ALGORITHM_KEYWORDS:
                if keyword in constraint_lower:
                    return True

        return False

    def _build_coding_prompt(self, task: CodingTask) -> str:
        """Build prompt for code generation

        Args:
            task: CodingTask to build prompt for

        Returns:
            Formatted prompt string
        """
        # Ultra-simplified prompt format
        if task.task_type == "create":
            # Very simple and direct prompt
            prompt = f"Write {task.language} code for: {task.instructions}\n\nCode:"
            return prompt

        elif task.task_type == "edit":
            prompt_parts = [f"Edit {task.language} code: {task.instructions}\n\n"]

            if task.existing_code:
                for filename, content in task.existing_code.items():
                    prompt_parts.append(f"Current {filename}:\n```{task.language}\n{content}\n```\n\n")

            prompt_parts.append(f"Output the modified code:\n```{task.language}\n")
            return "".join(prompt_parts)

        elif task.task_type == "refactor":
            prompt_parts = [f"Refactor {task.language} code: {task.instructions}\n\n"]

            if task.existing_code:
                for filename, content in task.existing_code.items():
                    prompt_parts.append(f"```{task.language}\n{content}\n```\n\n")

            prompt_parts.append(f"Output refactored code:\n```{task.language}\n")
            return "".join(prompt_parts)

        elif task.task_type == "fix":
            prompt_parts = [f"Fix this {task.language} code: {task.instructions}\n\n"]

            if task.existing_code:
                for filename, content in task.existing_code.items():
                    prompt_parts.append(f"```{task.language}\n{content}\n```\n\n")

            prompt_parts.append(f"Output fixed code:\n```{task.language}\n")
            return "".join(prompt_parts)

        # Fallback
        return f"Write {task.language} code: {task.instructions}\n\n```{task.language}\n"

    def _parse_code_response(self, response: str, task: CodingTask) -> CodeResult:
        """Parse model response into CodeResult

        Args:
            response: Raw model output
            task: Original CodingTask

        Returns:
            CodeResult with parsed code
        """
        # Check for escalation marker
        if "NEEDS_ALGORITHM_SPECIALIST" in response and "true" in response.lower():
            return CodeResult(
                success=True,
                needs_algorithm_specialist=True,
                explanation="Model identified this as requiring algorithm specialist."
            )

        # Extract code blocks
        code_blocks = self._extract_code_blocks(response)

        if not code_blocks:
            # No code blocks found, treat entire response as code if it looks like code
            if task.task_type in ["create", "edit", "refactor", "fix"]:
                # Assume response is the code
                code_blocks = {task.target_files[0]: response.strip()}
            else:
                return CodeResult(
                    success=False,
                    error="No code blocks found in response",
                    explanation=response
                )

        # Extract explanation (text before or after code blocks)
        explanation = self._extract_explanation(response, code_blocks)

        return CodeResult(
            success=True,
            code=code_blocks,
            explanation=explanation,
            needs_algorithm_specialist=False
        )

    def _extract_code_blocks(self, response: str) -> Dict[str, str]:
        """Extract code blocks from response

        Args:
            response: Model response text

        Returns:
            Dict mapping filename to code content
        """
        code_blocks = {}

        # Pattern 1: ```language\n# FILE: filename\ncode\n```
        pattern1 = r'```\w+\s*\n#\s*FILE:\s*([^\n]+)\n(.*?)```'
        matches1 = re.finditer(pattern1, response, re.DOTALL)

        for match in matches1:
            filename = match.group(1).strip()
            code = match.group(2).strip()
            code_blocks[filename] = code

        # Pattern 2: Standard code blocks ```language\ncode\n```
        if not code_blocks:
            pattern2 = r'```\w*\s*\n(.*?)```'
            matches2 = re.finditer(pattern2, response, re.DOTALL)

            for i, match in enumerate(matches2):
                code = match.group(1).strip()
                # Use target filename if available
                if i < len(task.target_files if 'task' in locals() else []):
                    filename = task.target_files[i]
                else:
                    filename = f"code_block_{i}.py"
                code_blocks[filename] = code

        return code_blocks

    def _extract_explanation(self, response: str, code_blocks: Dict[str, str]) -> Optional[str]:
        """Extract explanation text from response

        Args:
            response: Model response
            code_blocks: Extracted code blocks

        Returns:
            Explanation text or None
        """
        # Remove code blocks from response
        text = response
        for code in code_blocks.values():
            text = text.replace(code, "")

        # Remove markdown code block markers
        text = re.sub(r'```\w*\s*\n', '', text)
        text = re.sub(r'```', '', text)
        text = re.sub(r'#\s*FILE:\s*[^\n]+', '', text)

        # Clean up
        text = text.strip()

        # Return if substantial text remains
        if len(text) > 20:
            return text

        return None

    def _infer_language(self, filename: str) -> str:
        """Infer programming language from filename

        Args:
            filename: Name of file

        Returns:
            Language name
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.sh': 'bash',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }

        suffix = Path(filename).suffix.lower()
        return ext_map.get(suffix, 'python')

    def generate_diff_edits(self, task: CodingTask, use_diff: bool = True):
        """Generate diff-based edits instead of full file regeneration (Phase 5)

        This method uses the DiffGenerator to create targeted edits,
        which can reduce token usage by ~10x for large files.

        Args:
            task: CodingTask with task_type="edit" or "fix"
            use_diff: If True, generate diffs; if False, fall back to full file

        Returns:
            CodeResult with edit blocks instead of full code (if use_diff=True)
        """
        from core.diff_generator import DiffGenerator

        if not self._loaded:
            return CodeResult(
                success=False,
                error="Model not loaded. Call load() first."
            )

        # Only use diff mode for edit/fix tasks with existing code
        if task.task_type not in ["edit", "fix"] or not task.existing_code or not use_diff:
            # Fall back to regular code generation
            return self.generate_code(task)

        # Get the file to edit
        if len(task.target_files) != 1 or len(task.existing_code) != 1:
            # Diff mode works best with single file edits
            return self.generate_code(task)

        filename = task.target_files[0]
        original_code = task.existing_code[filename]

        # Build diff-specific prompt
        diff_gen = DiffGenerator()
        prompt = diff_gen.generate_edit_prompt(filename, original_code, task.instructions)

        try:
            print(f"[DEBUG] Generating diff edits for: {filename}")

            response = self.generate(
                prompt,
                temperature=self.config.get("temperature", 0.3),
                max_tokens=1024,  # Diffs typically need more tokens than regular code
                stop=["</s>", "\n\n\n", "User:", "Human:", "<|im_end|>"]
            )

            # Parse edit blocks
            print(f"[DEBUG] Parsing edit blocks from response...")
            edit_blocks = diff_gen.parse_edit_blocks(response)

            if not edit_blocks:
                print(f"[DEBUG] No edit blocks found, falling back to full file generation")
                return self.generate_code(task)

            # Validate edits
            errors = diff_gen.validate_edits(original_code, edit_blocks)
            if errors:
                print(f"[WARNING] Edit validation failed: {errors}")
                return CodeResult(
                    success=False,
                    error=f"Generated edits failed validation:\n" + "\n".join(errors)
                )

            # Store edit blocks in metadata
            return CodeResult(
                success=True,
                code=None,  # No full code, just edits
                explanation=f"Generated {len(edit_blocks)} targeted edits",
                metadata={
                    "edit_blocks": edit_blocks,
                    "filename": filename,
                    "original_code": original_code,
                    "diff_mode": True
                }
            )

        except Exception as e:
            print(f"[ERROR] Diff generation failed: {str(e)}")
            print(f"[DEBUG] Falling back to full file generation")
            return self.generate_code(task)
