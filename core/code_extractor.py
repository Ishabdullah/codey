"""Code Extractor - Robust extraction of code from LLM responses

This module handles:
1. Extracting code from markdown code blocks
2. Stripping markdown wrappers
3. Handling FILE: markers
4. Validating content matches expected file type
5. Cleaning common LLM output artifacts

Part of Phase 6.1: Code Extraction Fixes
"""
import re
from typing import Optional, Tuple, List
from pathlib import Path


class CodeExtractor:
    """Robust code extraction from LLM responses"""

    # File type to expected content patterns
    FILE_TYPE_PATTERNS = {
        '.py': [
            r'^\s*(import |from |def |class |@|#|if __name__|""")',
            r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=',  # Variable assignment
        ],
        '.html': [
            r'<!DOCTYPE|<html|<head|<body|<div|<script|<link|<meta',
        ],
        '.css': [
            r'^\s*[a-zA-Z#.\[\*:@][^{]*\{',  # CSS selector
            r'^\s*(body|html|div|span|\.|\#|@media|@import)\s*[\{,]',
        ],
        '.js': [
            r'^\s*(function|const|let|var|class|import|export|async|document\.|window\.)',
            r'^\s*[a-zA-Z_$][a-zA-Z0-9_$]*\s*[=\(]',
        ],
        '.json': [
            r'^\s*[\{\[]',
        ],
        '.md': [
            r'^#\s+\w',  # Markdown heading
            r'^\*\*\w',  # Bold
        ],
        '.txt': [
            r'.',  # Any content
        ],
    }

    # Patterns that indicate wrong content type
    WRONG_TYPE_INDICATORS = {
        '.css': ['<!DOCTYPE', '<html', '<head', '<body', 'function ', 'const ', 'import '],
        '.js': ['<!DOCTYPE', '<html', '<head', '<body', 'body {', '.class {', '@media'],
        '.py': ['<!DOCTYPE', '<html', 'function ', 'const ', 'body {'],
        '.html': ['^body {', '^\.', '^#[a-z]'],  # CSS selectors at start
    }

    def __init__(self):
        pass

    def extract(self, response: str, filename: str) -> Tuple[Optional[str], str]:
        """Extract code from LLM response

        Args:
            response: Raw LLM response
            filename: Expected filename (for type detection)

        Returns:
            Tuple of (extracted_code, status_message)
        """
        if not response or response.startswith("✗") or response.startswith("Error"):
            return None, "Empty or error response"

        file_ext = Path(filename).suffix.lower()

        # Step 1: Try to extract from code blocks
        code = self._extract_from_code_blocks(response, filename)

        if code:
            # Step 2: Clean the extracted code
            code = self._clean_code(code, file_ext)

            # Step 3: Validate content type
            is_valid, validation_msg = self._validate_content_type(code, file_ext)

            if is_valid:
                return code, "Success"
            else:
                # Try to salvage by looking for the right content
                salvaged = self._try_salvage(response, file_ext)
                if salvaged:
                    return salvaged, "Salvaged from response"
                return code, f"Warning: {validation_msg}"

        # Step 4: Try direct extraction (no code blocks)
        code = self._extract_direct(response, file_ext)
        if code:
            code = self._clean_code(code, file_ext)
            return code, "Direct extraction"

        return None, "No code found"

    def _extract_from_code_blocks(self, response: str, filename: str) -> Optional[str]:
        """Extract code from markdown code blocks"""
        # Pattern 1: ```language\ncode\n```
        # Pattern 2: ```\ncode\n```
        # Pattern 3: # FILE: filename\ncode

        patterns = [
            # Standard code block with language
            r'```(?:python|py|html|css|javascript|js|json|markdown|md|txt|sql)?\s*\n(.*?)```',
            # Code block without language
            r'```\n(.*?)```',
            # FILE: marker
            r'#\s*FILE:\s*[^\n]+\n(.*?)(?:```|$)',
            # file: marker (lowercase)
            r'#\s*file:\s*[^\n]+\n(.*?)(?:```|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                # Return the longest match (most complete code block)
                best_match = max(matches, key=len)
                return best_match.strip()

        return None

    def _extract_direct(self, response: str, file_ext: str) -> Optional[str]:
        """Extract code directly without code blocks"""
        # Check if response looks like the target file type
        patterns = self.FILE_TYPE_PATTERNS.get(file_ext, [])

        for pattern in patterns:
            if re.search(pattern, response, re.MULTILINE):
                return response.strip()

        return None

    def _clean_code(self, code: str, file_ext: str) -> str:
        """Clean extracted code of common artifacts"""
        lines = code.split('\n')
        cleaned_lines = []

        for i, line in enumerate(lines):
            # Skip filename-only lines at the start
            if i == 0 and self._is_filename_line(line):
                continue

            # Skip markdown code block markers
            if line.strip().startswith('```'):
                continue

            # Skip "# FILE:" or "# file:" markers
            if re.match(r'^#\s*(?:FILE|file):\s*\S+', line):
                continue

            # Skip lines that are just the filename
            if i < 3 and line.strip() in [
                'app.py', 'index.html', 'style.css', 'script.js',
                'app.js', 'main.py', 'requirements.txt', 'README.md'
            ]:
                continue

            cleaned_lines.append(line)

        # Remove leading/trailing empty lines
        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        return '\n'.join(cleaned_lines)

    def _is_filename_line(self, line: str) -> bool:
        """Check if line is just a filename"""
        stripped = line.strip()
        # Common file patterns
        file_patterns = [
            r'^[a-zA-Z_][a-zA-Z0-9_]*\.(py|html|css|js|json|md|txt)$',
            r'^(templates|static)/[a-zA-Z_][a-zA-Z0-9_/]*\.(py|html|css|js)$',
        ]
        for pattern in file_patterns:
            if re.match(pattern, stripped):
                return True
        return False

    def _validate_content_type(self, code: str, file_ext: str) -> Tuple[bool, str]:
        """Validate that code matches expected file type"""
        # Check for wrong type indicators
        wrong_indicators = self.WRONG_TYPE_INDICATORS.get(file_ext, [])
        for indicator in wrong_indicators:
            if indicator.startswith('^'):
                # Regex pattern
                if re.search(indicator, code, re.MULTILINE):
                    return False, f"Contains wrong content type pattern: {indicator}"
            else:
                if indicator in code:
                    return False, f"Contains wrong content type: {indicator}"

        # Check for expected type indicators
        expected_patterns = self.FILE_TYPE_PATTERNS.get(file_ext, [])
        for pattern in expected_patterns:
            if re.search(pattern, code, re.MULTILINE):
                return True, "Content matches expected type"

        # If no patterns matched but no wrong indicators, accept it
        return True, "No validation patterns matched, accepting"

    def _try_salvage(self, response: str, file_ext: str) -> Optional[str]:
        """Try to find correct content in a misformatted response"""
        # Look for content blocks that match the expected type
        expected_patterns = self.FILE_TYPE_PATTERNS.get(file_ext, [])

        # For CSS, try to find CSS-only content
        if file_ext == '.css':
            # Find content between style tags or CSS-looking blocks
            css_match = re.search(r'((?:body|html|\.|\#|@)[^<]*\{[^}]+\}(?:\s*[^<]*\{[^}]+\})*)', response, re.DOTALL)
            if css_match:
                return css_match.group(1).strip()

        # For JS, try to find JS-only content
        if file_ext == '.js':
            # Find function definitions or document ready
            js_match = re.search(r'((?:function|const|let|var|document\.)[^<]+)', response, re.DOTALL)
            if js_match:
                return js_match.group(1).strip()

        return None


def extract_code(response: str, filename: str) -> Tuple[Optional[str], str]:
    """Convenience function for code extraction

    Args:
        response: LLM response
        filename: Target filename

    Returns:
        Tuple of (code, status_message)
    """
    extractor = CodeExtractor()
    return extractor.extract(response, filename)


def validate_file_content(content: str, filename: str) -> Tuple[bool, str]:
    """Validate that file content matches expected type

    Args:
        content: File content
        filename: Filename (for type detection)

    Returns:
        Tuple of (is_valid, message)
    """
    extractor = CodeExtractor()
    file_ext = Path(filename).suffix.lower()
    return extractor._validate_content_type(content, file_ext)
