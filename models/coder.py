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

    SYSTEM_PROMPT = """You are an expert coding assistant powered by Qwen2.5-Coder. Generate clean, production-ready code with:

1. Clear structure and organization
2. Proper error handling
3. Type hints (Python) or type annotations
4. Docstrings/comments for complex logic
5. Following language best practices

When editing code:
- Output ONLY the modified sections, not the entire file
- Use clear markers: ```python\n# FILE: filename.py\n[code]\n```
- Preserve existing functionality unless explicitly asked to change

When you encounter algorithmic tasks requiring specialized knowledge (data structures, algorithms, performance optimization), indicate:
NEEDS_ALGORITHM_SPECIALIST: true

Always explain your reasoning briefly."""

    # Keywords that trigger algorithm specialist escalation
    ALGORITHM_KEYWORDS = [
        "binary search", "sorting", "graph", "tree", "heap", "hash table",
        "dynamic programming", "algorithm", "data structure", "complexity",
        "O(n)", "optimize performance", "parser", "lexer", "state machine",
        "automaton", "low-latency", "performance-critical"
    ]

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
            # Generate code
            response = self.generate(
                prompt,
                temperature=self.config.get("temperature", 0.3),
                max_tokens=self.config.get("max_tokens", 2048),
                stop=["</code>", "```\n\n\n"]
            )

            # Parse response
            result = self._parse_code_response(response, task)
            return result

        except Exception as e:
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
        prompt_parts = [self.SYSTEM_PROMPT, "\n\n"]

        # Task type specific instructions
        if task.task_type == "create":
            prompt_parts.append(f"Create new {task.language} file(s): {', '.join(task.target_files)}\n")
            prompt_parts.append(f"Requirements: {task.instructions}\n")

        elif task.task_type == "edit":
            prompt_parts.append(f"Edit {task.language} file(s): {', '.join(task.target_files)}\n")
            prompt_parts.append(f"Changes needed: {task.instructions}\n\n")

            # Include existing code
            if task.existing_code:
                for filename, content in task.existing_code.items():
                    prompt_parts.append(f"Current code in {filename}:\n```{task.language}\n{content}\n```\n\n")

        elif task.task_type == "refactor":
            prompt_parts.append(f"Refactor {task.language} code in: {', '.join(task.target_files)}\n")
            prompt_parts.append(f"Goal: {task.instructions}\n\n")

            if task.existing_code:
                for filename, content in task.existing_code.items():
                    prompt_parts.append(f"Code to refactor ({filename}):\n```{task.language}\n{content}\n```\n\n")

        elif task.task_type == "fix":
            prompt_parts.append(f"Fix issue in {task.language} file(s): {', '.join(task.target_files)}\n")
            prompt_parts.append(f"Issue: {task.instructions}\n\n")

            if task.existing_code:
                for filename, content in task.existing_code.items():
                    prompt_parts.append(f"Code with issue ({filename}):\n```{task.language}\n{content}\n```\n\n")

        # Add constraints if any
        if task.constraints:
            prompt_parts.append("Constraints:\n")
            for constraint in task.constraints:
                prompt_parts.append(f"- {constraint}\n")
            prompt_parts.append("\n")

        # Add context if provided
        if task.context:
            prompt_parts.append(f"Context: {task.context}\n\n")

        # Add generation instruction
        prompt_parts.append(f"Generate the {task.task_type} code:\n")

        return "".join(prompt_parts)

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
