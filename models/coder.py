"""Primary Coder Model - Qwen2.5-Coder 7B Wrapper

This module provides a specialized wrapper for the Qwen2.5-Coder 7B model,
designed for code generation, editing, refactoring, and review tasks.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import re

from models.base import BaseModel

logger = logging.getLogger(__name__)


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

    SYSTEM_PROMPT = """You are an expert code generator. Your ONLY job is to write code.

OUTPUT FORMAT:
- Output ONLY code in markdown code blocks using ```language
- Do NOT include explanations, greetings, or conversation
- Do NOT say "Here is the code" or similar phrases
- Start directly with the code block

CODE QUALITY:
- Write complete, functional, runnable code
- Use proper syntax and language-specific best practices
- Add brief inline comments for complex logic only
- Use descriptive variable and function names

RESTRICTIONS:
- Output code ONLY - no prose, no explanations
- Do not ask clarifying questions
- Do not suggest alternatives unless asked"""

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
            **kwargs: Generation parameters (temperature, max_tokens, stop, stream, etc.)

        Returns:
            Generated text
        """
        if not self._loaded or not self._model:
            raise RuntimeError("Model not loaded. Cannot generate.")

        # Extract parameters - reduced defaults for CPU
        temperature = kwargs.get('temperature', 0.3)
        max_tokens = kwargs.get('max_tokens', 256)  # Reduced from 2048 for CPU
        stop = kwargs.get('stop', None)
        stream = kwargs.get('stream', True)  # Enable streaming by default
        timeout_seconds = kwargs.get('timeout', 300)  # 5 minutes default

        # Debug logging
        logger.debug("Starting generation...")
        logger.debug(f"Temperature: {temperature}, Max tokens: {max_tokens}, Stream: {stream}")
        logger.debug(f"Stop sequences: {stop}")
        logger.debug(f"Prompt length: {len(prompt)} characters")

        import time
        start_time = time.time()

        try:
            if stream:
                # Streaming generation - shows progress and avoids timeout issues
                return self._generate_streaming(
                    prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop,
                    timeout_seconds=timeout_seconds
                )
            else:
                # Non-streaming with timeout
                import signal
                from contextlib import contextmanager

                @contextmanager
                def timeout(seconds):
                    def timeout_handler(signum, frame):
                        raise TimeoutError(f"Generation exceeded {seconds} second timeout")
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(seconds)
                    try:
                        yield
                    finally:
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)

                with timeout(timeout_seconds):
                    response = self._model(
                        prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stop=stop,
                        echo=False
                    )

                elapsed = time.time() - start_time
                logger.debug(f"Generation completed in {elapsed:.2f} seconds")

                if isinstance(response, dict) and 'choices' in response:
                    result = response['choices'][0]['text']
                    logger.debug(f"Generated {len(result)} characters")
                    return result

                return str(response)

        except TimeoutError as e:
            logger.error(str(e))
            raise RuntimeError(f"Generation timeout after {timeout_seconds} seconds - check CPU performance")

    def _generate_streaming(self, prompt: str, temperature: float = 0.3,
                           max_tokens: int = 256, stop: list = None,
                           timeout_seconds: int = 300,
                           target_filename: str = None,
                           file_tools = None,
                           workspace_dir = None) -> str:
        """Generate with streaming for progress feedback and real-time file writing

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            timeout_seconds: Maximum generation time
            target_filename: Optional target filename for streaming write
            file_tools: Optional FileTools for real-time file writing
            workspace_dir: Optional workspace directory

        Returns:
            Complete generated text
        """
        import time
        import sys
        from pathlib import Path

        start_time = time.time()
        generated_text = ""
        token_count = 0
        last_progress_time = start_time

        # Set up streaming file writer if tools provided
        streaming_writer = None
        if file_tools and workspace_dir:
            try:
                from core.streaming_writer import StreamingFileWriter

                def on_file_start(filename):
                    print(f"\n   📝 Writing {filename}...", end="", flush=True)

                def on_file_complete(filename, bytes_written):
                    print(f" ✓ ({bytes_written} bytes)")

                streaming_writer = StreamingFileWriter(
                    workspace_dir=Path(workspace_dir),
                    file_tools=file_tools,
                    on_file_start=on_file_start,
                    on_file_complete=on_file_complete
                )
            except ImportError:
                logger.debug("StreamingFileWriter not available, using standard streaming")

        try:
            # Use llama-cpp streaming API
            stream = self._model(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop or [],
                echo=False,
                stream=True
            )

            for chunk in stream:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    logger.warning(f"Streaming timeout after {elapsed:.1f}s with {token_count} tokens")
                    break

                # Extract token from chunk
                if 'choices' in chunk and chunk['choices']:
                    token_text = chunk['choices'][0].get('text', '')
                    if token_text:
                        generated_text += token_text
                        token_count += 1

                        # Process through streaming writer for real-time file writing
                        if streaming_writer:
                            streaming_writer.process_token(token_text, target_filename)

                        # Show progress every 2 seconds
                        current_time = time.time()
                        if current_time - last_progress_time >= 2.0:
                            tps = token_count / (current_time - start_time)
                            print(f"\r   → {token_count} tokens ({tps:.1f} tok/s)", end="", flush=True)
                            last_progress_time = current_time

            # Flush streaming writer
            if streaming_writer:
                streaming_writer.flush(target_filename)

            # Final stats
            elapsed = time.time() - start_time
            if token_count > 0:
                tps = token_count / elapsed
                print(f"\r   → {token_count} tokens in {elapsed:.1f}s ({tps:.1f} tok/s)   ")

            logger.debug(f"Streaming complete: {token_count} tokens in {elapsed:.1f}s")
            return generated_text

        except Exception as e:
            logger.error(f"Streaming generation error: {e}")
            # Flush writer on error
            if streaming_writer:
                streaming_writer.flush(target_filename)
            # Return whatever we generated so far
            if generated_text:
                logger.info(f"Returning partial result: {len(generated_text)} chars")
                return generated_text
            raise

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
            logger.debug(f"Generating code for task type: {task.task_type}")

            response = self.generate(
                prompt,
                temperature=self.config.get("temperature", 0.3),
                max_tokens=512,  # Reasonable size for code generation
                stop=["</s>", "\n\n\n", "User:", "Human:", "<|im_end|>"]  # Proper stop sequences
            )

            # Parse response
            logger.debug("Parsing response...")
            result = self._parse_code_response(response, task)
            logger.debug(f"Parse result: success={result.success}, needs_algo={result.needs_algorithm_specialist}")
            return result

        except Exception as e:
            logger.error(f"Code generation failed: {str(e)}", exc_info=True)
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

    def _sanitize_instructions(self, instructions: str) -> str:
        """Sanitize user instructions to remove router artifacts

        Removes any classification metadata or router-specific content
        that might have leaked through.

        Args:
            instructions: Raw instructions string

        Returns:
            Cleaned instructions
        """
        import re

        # Remove any JSON-like classification artifacts
        # e.g., {"intent": "coding_task", ...}
        cleaned = re.sub(r'\{["\']?intent["\']?\s*:', '', instructions)
        cleaned = re.sub(r'\{["\']?confidence["\']?\s*:', '', cleaned)

        # Remove router-specific phrases
        router_phrases = [
            r'intent:\s*\w+',
            r'confidence:\s*[\d.]+',
            r'escalate:\s*\w+',
            r'tool:\s*\w+',
            r'classification:',
            r'routing to:',
        ]
        for phrase in router_phrases:
            cleaned = re.sub(phrase, '', cleaned, flags=re.IGNORECASE)

        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned

    def _build_coding_prompt(self, task: CodingTask) -> str:
        """Build prompt for code generation

        Args:
            task: CodingTask to build prompt for

        Returns:
            Formatted prompt string
        """
        # Sanitize instructions to remove any router artifacts
        instructions = self._sanitize_instructions(task.instructions)

        # Detect web application context
        is_web_app = any(kw in instructions.lower() for kw in ['flask', 'django', 'fastapi', 'html', 'css', 'javascript', 'frontend', 'backend', 'web app'])
        
        web_instructions = ""
        if is_web_app:
            web_instructions = """
WEB DEVELOPMENT REQUIREMENTS:
1. Frontend: Generate separate files for HTML, CSS, and JavaScript. 
   - Use standard structure: templates/index.html, static/css/style.css, static/js/script.js
   - Include forms, buttons, and client-side logic (fetch/axios) to interact with the backend.
2. Backend: Include proper error handling (try/except) and input validation.
   - Validate JSON data in routes.
   - Return appropriate HTTP status codes (400 for bad input, 500 for server errors).
3. Database: If using SQLite, include schema creation and CRUD operations.
4. README: Generate a README.md with setup and running instructions.
"""

        # Ultra-simplified prompt format
        if task.task_type == "create":
            # Very simple and direct prompt
            prompt = f"Write {task.language} code for: {instructions}\n{web_instructions}\nCode:"
            return prompt

        elif task.task_type == "edit":
            prompt_parts = [f"Edit {task.language} code: {instructions}\n{web_instructions}\n"]

            if task.existing_code:
                for filename, content in task.existing_code.items():
                    prompt_parts.append(f"Current {filename}:\n```{task.language}\n{content}\n```\n\n")

            prompt_parts.append(f"Output the modified code:\n```{task.language}\n")
            return "".join(prompt_parts)

        elif task.task_type == "refactor":
            prompt_parts = [f"Refactor {task.language} code: {instructions}\n{web_instructions}\n"]

            if task.existing_code:
                for filename, content in task.existing_code.items():
                    prompt_parts.append(f"```{task.language}\n{content}\n```\n\n")

            prompt_parts.append(f"Output refactored code:\n```{task.language}\n")
            return "".join(prompt_parts)

        elif task.task_type == "fix":
            prompt_parts = [f"Fix this {task.language} code: {instructions}\n{web_instructions}\n"]

            if task.existing_code:
                for filename, content in task.existing_code.items():
                    prompt_parts.append(f"```{task.language}\n{content}\n```\n\n")

            prompt_parts.append(f"Output fixed code:\n```{task.language}\n")
            return "".join(prompt_parts)

        # Fallback
        return f"Write {task.language} code: {instructions}\n{web_instructions}\n```{task.language}\n"

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
            logger.debug(f"Generating diff edits for: {filename}")

            response = self.generate(
                prompt,
                temperature=self.config.get("temperature", 0.3),
                max_tokens=1024,  # Diffs typically need more tokens than regular code
                stop=["</s>", "\n\n\n", "User:", "Human:", "<|im_end|>"]
            )

            # Parse edit blocks
            logger.debug("Parsing edit blocks from response...")
            edit_blocks = diff_gen.parse_edit_blocks(response)

            if not edit_blocks:
                logger.debug("No edit blocks found, falling back to full file generation")
                return self.generate_code(task)

            # Validate edits
            errors = diff_gen.validate_edits(original_code, edit_blocks)
            if errors:
                logger.warning(f"Edit validation failed: {errors}")
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
            logger.error(f"Diff generation failed: {str(e)}")
            logger.debug("Falling back to full file generation")
            return self.generate_code(task)
