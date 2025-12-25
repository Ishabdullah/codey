"""Diff Generator - Targeted code editing using diffs

This module handles diff-based editing, replacing full-file regeneration
with targeted edits to specific code blocks.

Part of Phase 5: Diff-Based Editing
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional
import re


@dataclass
class EditBlock:
    """Represents a single edit to a code block"""
    start_line: int
    end_line: int
    old_content: str
    new_content: str
    description: str

    def __post_init__(self):
        """Validate edit block"""
        if self.start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {self.start_line}")
        if self.end_line < self.start_line:
            raise ValueError(f"end_line {self.end_line} must be >= start_line {self.start_line}")


class DiffGenerator:
    """Generate and apply code diffs for targeted editing"""

    def __init__(self):
        """Initialize diff generator"""
        pass

    def generate_edit_prompt(self, filename: str, code: str, instructions: str) -> str:
        """Generate prompt that asks for edit blocks, not full file

        Args:
            filename: Name of file being edited
            code: Current file content
            instructions: User's edit instructions

        Returns:
            Prompt for model to generate edit blocks
        """
        # Number the lines for easy reference
        numbered_lines = []
        for i, line in enumerate(code.split('\n'), 1):
            numbered_lines.append(f"{i:4d} | {line}")

        numbered_code = '\n'.join(numbered_lines)

        prompt = f"""You are editing the file: {filename}

Current file content (with line numbers):
```
{numbered_code}
```

User instructions: {instructions}

Generate ONLY the specific edits needed. For each edit, specify:
1. The line range to modify (start_line to end_line)
2. The old content being replaced
3. The new content to insert
4. A brief description of the change

Format your response as:
EDIT 1:
Lines: <start>-<end>
Description: <what this edit does>
Old:
```
<old content>
```
New:
```
<new content>
```

EDIT 2:
...

Do NOT regenerate the entire file. Only specify the blocks that need to change.
"""
        return prompt

    def parse_edit_blocks(self, model_response: str) -> List[EditBlock]:
        """Parse model output into edit blocks

        Args:
            model_response: Model's response with edit blocks

        Returns:
            List of parsed EditBlock objects
        """
        edits = []

        # Split response into individual edits
        edit_sections = re.split(r'EDIT\s+\d+:', model_response)

        for section in edit_sections[1:]:  # Skip first empty split
            try:
                edit = self._parse_single_edit(section)
                if edit:
                    edits.append(edit)
            except Exception as e:
                # Log parsing error but continue
                print(f"Warning: Failed to parse edit block: {e}")
                continue

        return edits

    def _parse_single_edit(self, section: str) -> Optional[EditBlock]:
        """Parse a single EDIT section

        Args:
            section: Text for one EDIT block

        Returns:
            Parsed EditBlock or None if parsing fails
        """
        # Extract line range
        lines_match = re.search(r'Lines?:\s*(\d+)(?:\s*-\s*(\d+))?', section)
        if not lines_match:
            return None

        start_line = int(lines_match.group(1))
        end_line = int(lines_match.group(2)) if lines_match.group(2) else start_line

        # Extract description
        desc_match = re.search(r'Description:\s*([^\n]+)', section)
        description = desc_match.group(1).strip() if desc_match else "No description"

        # Extract old content
        old_match = re.search(r'Old:\s*```[^\n]*\n(.*?)```', section, re.DOTALL)
        old_content = old_match.group(1).strip() if old_match else ""

        # Extract new content
        new_match = re.search(r'New:\s*```[^\n]*\n(.*?)```', section, re.DOTALL)
        new_content = new_match.group(1).strip() if new_match else ""

        return EditBlock(
            start_line=start_line,
            end_line=end_line,
            old_content=old_content,
            new_content=new_content,
            description=description
        )

    def apply_edits(self, original: str, edits: List[EditBlock]) -> str:
        """Apply edit blocks to original code

        Args:
            original: Original file content
            edits: List of EditBlock objects to apply

        Returns:
            Modified file content
        """
        if not edits:
            return original

        # Sort edits by start_line (descending) to apply from bottom to top
        # This prevents line number shifts from affecting later edits
        sorted_edits = sorted(edits, key=lambda e: e.start_line, reverse=True)

        lines = original.split('\n')

        for edit in sorted_edits:
            # Validate line numbers
            if edit.start_line < 1 or edit.end_line > len(lines):
                print(f"Warning: Edit lines {edit.start_line}-{edit.end_line} out of range (file has {len(lines)} lines)")
                continue

            # Apply edit (convert to 0-based indexing)
            start_idx = edit.start_line - 1
            end_idx = edit.end_line

            # Replace the lines
            new_lines = edit.new_content.split('\n') if edit.new_content else []
            lines[start_idx:end_idx] = new_lines

        return '\n'.join(lines)

    def validate_edits(self, original: str, edits: List[EditBlock]) -> List[str]:
        """Validate edits won't break the file

        Args:
            original: Original file content
            edits: List of EditBlock objects

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        lines = original.split('\n')
        num_lines = len(lines)

        for i, edit in enumerate(edits):
            # Check line numbers
            if edit.start_line < 1:
                errors.append(f"Edit {i+1}: start_line {edit.start_line} must be >= 1")

            if edit.end_line > num_lines:
                errors.append(f"Edit {i+1}: end_line {edit.end_line} exceeds file length {num_lines}")

            if edit.start_line > edit.end_line:
                errors.append(f"Edit {i+1}: start_line {edit.start_line} > end_line {edit.end_line}")

            # Check old content matches (optional but recommended)
            if edit.old_content:
                actual_lines = lines[edit.start_line-1:edit.end_line]
                actual_content = '\n'.join(actual_lines).strip()
                expected_content = edit.old_content.strip()

                if actual_content != expected_content:
                    errors.append(
                        f"Edit {i+1}: old content mismatch at lines {edit.start_line}-{edit.end_line}\n"
                        f"Expected: {expected_content[:50]}...\n"
                        f"Actual: {actual_content[:50]}..."
                    )

        # Check for overlapping edits
        edit_ranges = [(e.start_line, e.end_line) for e in edits]
        for i, (start1, end1) in enumerate(edit_ranges):
            for j, (start2, end2) in enumerate(edit_ranges[i+1:], start=i+1):
                if self._ranges_overlap(start1, end1, start2, end2):
                    errors.append(f"Edit {i+1} and Edit {j+1} have overlapping line ranges")

        return errors

    def _ranges_overlap(self, start1: int, end1: int, start2: int, end2: int) -> bool:
        """Check if two line ranges overlap

        Args:
            start1, end1: First range
            start2, end2: Second range

        Returns:
            True if ranges overlap
        """
        return not (end1 < start2 or end2 < start1)

    def generate_unified_diff(self, original: str, modified: str, filename: str = "file") -> str:
        """Generate unified diff format for display

        Args:
            original: Original file content
            modified: Modified file content
            filename: Name of file (for diff header)

        Returns:
            Unified diff string
        """
        import difflib

        original_lines = original.split('\n')
        modified_lines = modified.split('\n')

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"{filename} (original)",
            tofile=f"{filename} (modified)",
            lineterm=''
        )

        return '\n'.join(diff)

    def estimate_token_savings(self, original: str, edits: List[EditBlock]) -> dict:
        """Estimate token savings from using diffs vs full file regeneration

        Args:
            original: Original file content
            edits: List of edits

        Returns:
            Dict with token estimates
        """
        # Rough estimate: 1 token ≈ 4 characters
        original_chars = len(original)
        original_tokens = original_chars // 4

        # Calculate edit chars (old + new content)
        edit_chars = sum(len(e.old_content) + len(e.new_content) for e in edits)
        edit_tokens = edit_chars // 4

        # Add overhead for edit format (line numbers, descriptions, etc.)
        format_overhead = len(edits) * 50  # ~50 tokens per edit for formatting

        total_edit_tokens = edit_tokens + format_overhead

        savings_tokens = original_tokens - total_edit_tokens
        savings_percent = (savings_tokens / original_tokens * 100) if original_tokens > 0 else 0

        return {
            "full_file_tokens": original_tokens,
            "diff_tokens": total_edit_tokens,
            "savings_tokens": savings_tokens,
            "savings_percent": savings_percent,
            "num_edits": len(edits)
        }
