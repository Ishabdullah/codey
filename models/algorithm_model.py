"""Algorithm Specialist Model - DeepSeek-Coder 6.7B Wrapper

This module provides a specialized wrapper for the DeepSeek-Coder 6.7B model,
designed for algorithmic problems, data structures, and performance-critical code.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import re

from models.base import GGUFModel


@dataclass
class AlgorithmTask:
    """Represents an algorithmic problem for the specialist"""
    problem_description: str
    constraints: List[str] = field(default_factory=list)
    expected_complexity: Optional[str] = None  # e.g., "O(n log n)", "O(1) space"
    language: str = "python"
    context_code: Optional[str] = None  # Surrounding code for integration
    test_cases: List[Dict[str, Any]] = field(default_factory=list)  # Optional test cases
    optimize_for: str = "time"  # "time", "space", or "both"


@dataclass
class AlgorithmResult:
    """Result from algorithm generation or optimization"""
    success: bool
    code: Optional[str] = None
    explanation: Optional[str] = None
    complexity_analysis: Optional[Dict[str, str]] = None  # {"time": "O(n)", "space": "O(1)"}
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    trade_offs: Optional[str] = None  # Explanation of design trade-offs
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlgorithmSpecialist(GGUFModel):
    """DeepSeek-Coder 6.7B wrapper for algorithmic problems

    This model specializes in:
    - Algorithm design (sorting, searching, graph algorithms)
    - Data structure implementation (trees, heaps, hash tables)
    - Performance optimization and complexity analysis
    - Mathematical and computational problems
    - Parser/lexer/state machine implementations

    Use this model when:
    - Implementing classical algorithms
    - Designing custom data structures
    - Optimizing for time/space complexity
    - Solving competitive programming problems
    - Building performance-critical components
    """

    SYSTEM_PROMPT = """You are an algorithm expert powered by DeepSeek-Coder. Generate efficient, correct algorithms with:

1. **Optimal complexity**: Choose the best time/space trade-off
2. **Correctness**: Handle all edge cases properly
3. **Clear analysis**: Always explain time and space complexity
4. **Well-commented**: Explain the approach and key insights
5. **Production-ready**: Include error handling and validation

Structure your response as:

## Approach
[Brief explanation of the algorithm/data structure]

## Complexity Analysis
- Time complexity: O(...)
- Space complexity: O(...)
[Explain why]

## Implementation
```python
[Your code here with comments]
```

## Edge Cases
[List edge cases handled]

Always prioritize correctness over cleverness. Explain trade-offs clearly."""

    def solve(self, task: AlgorithmTask) -> AlgorithmResult:
        """Solve algorithmic problem

        Args:
            task: AlgorithmTask describing the problem

        Returns:
            AlgorithmResult with solution and analysis
        """
        if not self._loaded:
            return AlgorithmResult(
                success=False,
                error="Model not loaded. Call load() first."
            )

        # Build prompt
        prompt = self._build_algorithm_prompt(task)

        try:
            # Generate solution
            response = self.generate(
                prompt,
                temperature=self.config.get("temperature", 0.2),
                max_tokens=self.config.get("max_tokens", 4096),
                stop=["</code>", "```\n\n\n", "## Next"]
            )

            # Parse response
            result = self._parse_algorithm_response(response, task)
            return result

        except Exception as e:
            return AlgorithmResult(
                success=False,
                error=f"Algorithm generation failed: {str(e)}"
            )

    def optimize(self, code: str, target_complexity: str, language: str = "python") -> AlgorithmResult:
        """Optimize existing code for performance

        Args:
            code: Code to optimize
            target_complexity: Target complexity (e.g., "O(n log n)")
            language: Programming language

        Returns:
            AlgorithmResult with optimized code
        """
        if not self._loaded:
            return AlgorithmResult(
                success=False,
                error="Model not loaded."
            )

        prompt = f"""{self.SYSTEM_PROMPT}

Optimize this {language} code to achieve {target_complexity} complexity:

```{language}
{code}
```

Target: {target_complexity}

Provide:
1. Current complexity analysis
2. Optimized implementation
3. Explanation of optimization techniques used
4. Verification that target complexity is achieved

Optimized solution:"""

        try:
            response = self.generate(
                prompt,
                temperature=0.2,
                max_tokens=3072
            )

            result = self._parse_algorithm_response(response, None)
            return result

        except Exception as e:
            return AlgorithmResult(
                success=False,
                error=f"Optimization failed: {str(e)}"
            )

    def analyze_complexity(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Analyze time/space complexity of code

        Args:
            code: Code to analyze
            language: Programming language

        Returns:
            Dict with complexity analysis
        """
        if not self._loaded:
            return {"error": "Model not loaded"}

        prompt = f"""Analyze the time and space complexity of this {language} code:

```{language}
{code}
```

Provide analysis as JSON:
{{
  "time_complexity": "O(...)",
  "space_complexity": "O(...)",
  "explanation": "...",
  "bottlenecks": ["..."],
  "optimization_suggestions": ["..."]
}}

Analysis:"""

        try:
            response = self.generate(
                prompt,
                temperature=0.2,
                max_tokens=1024
            )

            # Try to parse JSON
            try:
                analysis = json.loads(response.strip())
                return analysis
            except json.JSONDecodeError:
                # Fallback: extract complexity manually
                return self._extract_complexity_from_text(response)

        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def _build_algorithm_prompt(self, task: AlgorithmTask) -> str:
        """Build prompt for algorithm generation

        Args:
            task: AlgorithmTask to build prompt for

        Returns:
            Formatted prompt string
        """
        prompt_parts = [self.SYSTEM_PROMPT, "\n\n"]

        # Problem description
        prompt_parts.append(f"## Problem\n{task.problem_description}\n\n")

        # Constraints
        if task.constraints:
            prompt_parts.append("## Constraints\n")
            for constraint in task.constraints:
                prompt_parts.append(f"- {constraint}\n")
            prompt_parts.append("\n")

        # Expected complexity
        if task.expected_complexity:
            prompt_parts.append(f"## Target Complexity\n{task.expected_complexity}\n\n")

        # Optimization goal
        if task.optimize_for:
            opt_str = {
                "time": "time complexity",
                "space": "space complexity",
                "both": "both time and space complexity"
            }.get(task.optimize_for, "efficiency")
            prompt_parts.append(f"Optimize for: {opt_str}\n\n")

        # Context code
        if task.context_code:
            prompt_parts.append(f"## Context\nIntegrate with this code:\n```{task.language}\n{task.context_code}\n```\n\n")

        # Test cases
        if task.test_cases:
            prompt_parts.append("## Example Test Cases\n")
            for i, test in enumerate(task.test_cases[:3], 1):  # Limit to 3 examples
                input_data = test.get('input', '')
                output_data = test.get('output', '')
                prompt_parts.append(f"Test {i}:\n  Input: {input_data}\n  Output: {output_data}\n")
            prompt_parts.append("\n")

        # Generation instruction
        prompt_parts.append(f"Provide a complete {task.language} solution:\n")

        return "".join(prompt_parts)

    def _parse_algorithm_response(self, response: str, task: Optional[AlgorithmTask]) -> AlgorithmResult:
        """Parse model response into AlgorithmResult

        Args:
            response: Raw model output
            task: Original AlgorithmTask (optional)

        Returns:
            AlgorithmResult with parsed solution
        """
        # Extract code blocks
        code_blocks = self._extract_code_blocks(response)

        if not code_blocks:
            return AlgorithmResult(
                success=False,
                error="No code found in response",
                explanation=response
            )

        # Use first code block as main solution
        code = code_blocks[0] if code_blocks else None

        # Extract complexity analysis
        complexity = self._extract_complexity(response)

        # Extract explanation
        explanation = self._extract_explanation_sections(response)

        # Extract trade-offs
        trade_offs = self._extract_trade_offs(response)

        return AlgorithmResult(
            success=True,
            code=code,
            explanation=explanation,
            complexity_analysis=complexity,
            trade_offs=trade_offs
        )

    def _extract_code_blocks(self, response: str) -> List[str]:
        """Extract code blocks from response

        Args:
            response: Model response text

        Returns:
            List of code blocks
        """
        code_blocks = []

        # Pattern: ```language\ncode\n```
        pattern = r'```\w*\s*\n(.*?)```'
        matches = re.finditer(pattern, response, re.DOTALL)

        for match in matches:
            code = match.group(1).strip()
            # Skip if it looks like JSON or other non-code
            if not code.startswith('{') or 'def ' in code or 'class ' in code:
                code_blocks.append(code)

        return code_blocks

    def _extract_complexity(self, response: str) -> Dict[str, str]:
        """Extract complexity analysis from response

        Args:
            response: Model response

        Returns:
            Dict with time and space complexity
        """
        complexity = {}

        # Pattern: Time complexity: O(...)
        time_pattern = r'[Tt]ime\s+[Cc]omplexity[:\s]+O\(([^)]+)\)'
        time_match = re.search(time_pattern, response)
        if time_match:
            complexity['time'] = f"O({time_match.group(1)})"

        # Pattern: Space complexity: O(...)
        space_pattern = r'[Ss]pace\s+[Cc]omplexity[:\s]+O\(([^)]+)\)'
        space_match = re.search(space_pattern, response)
        if space_match:
            complexity['space'] = f"O({space_match.group(1)})"

        # If not found, try to extract from structured sections
        if not complexity:
            complexity_section = re.search(
                r'##\s*Complexity\s*Analysis\s*\n(.*?)(?:##|```|$)',
                response,
                re.DOTALL | re.IGNORECASE
            )
            if complexity_section:
                section_text = complexity_section.group(1)
                time_match = re.search(r'O\(([^)]+)\)', section_text)
                if time_match:
                    complexity['time'] = f"O({time_match.group(1)})"

        return complexity if complexity else {"time": "Unknown", "space": "Unknown"}

    def _extract_explanation_sections(self, response: str) -> str:
        """Extract explanation text from response

        Args:
            response: Model response

        Returns:
            Explanation text
        """
        explanation_parts = []

        # Extract "Approach" section
        approach = re.search(
            r'##\s*Approach\s*\n(.*?)(?:##|```|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if approach:
            explanation_parts.append(f"Approach: {approach.group(1).strip()}")

        # Extract "Complexity Analysis" section
        complexity = re.search(
            r'##\s*Complexity\s*Analysis\s*\n(.*?)(?:##|```|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if complexity:
            explanation_parts.append(f"Complexity: {complexity.group(1).strip()}")

        # Extract "Edge Cases" section
        edge_cases = re.search(
            r'##\s*Edge\s*Cases\s*\n(.*?)(?:##|```|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if edge_cases:
            explanation_parts.append(f"Edge Cases: {edge_cases.group(1).strip()}")

        if explanation_parts:
            return "\n\n".join(explanation_parts)

        # Fallback: extract text before first code block
        first_code = re.search(r'```', response)
        if first_code:
            intro = response[:first_code.start()].strip()
            if len(intro) > 20:
                return intro

        return "See code for implementation details."

    def _extract_trade_offs(self, response: str) -> Optional[str]:
        """Extract trade-off explanations from response

        Args:
            response: Model response

        Returns:
            Trade-offs explanation or None
        """
        # Look for trade-offs section
        trade_offs = re.search(
            r'##\s*Trade[-\s]*[Oo]ffs?\s*\n(.*?)(?:##|```|$)',
            response,
            re.DOTALL
        )
        if trade_offs:
            return trade_offs.group(1).strip()

        # Look for mentions of trade-offs in text
        if 'trade-off' in response.lower() or 'tradeoff' in response.lower():
            # Extract sentence containing trade-off
            sentences = response.split('.')
            for sent in sentences:
                if 'trade' in sent.lower() and 'off' in sent.lower():
                    return sent.strip()

        return None

    def _extract_complexity_from_text(self, text: str) -> Dict[str, Any]:
        """Extract complexity from unstructured text

        Args:
            text: Response text

        Returns:
            Dict with complexity information
        """
        result = {
            "time_complexity": "Unknown",
            "space_complexity": "Unknown",
            "raw_analysis": text
        }

        # Try to find O(...) patterns
        o_patterns = re.findall(r'O\([^)]+\)', text)
        if o_patterns:
            # Assume first is time, second is space
            if len(o_patterns) >= 1:
                result["time_complexity"] = o_patterns[0]
            if len(o_patterns) >= 2:
                result["space_complexity"] = o_patterns[1]

        return result
