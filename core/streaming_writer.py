"""Streaming File Writer - Write files in real-time during generation

This module enables real-time file creation as tokens are streamed
from the LLM, providing immediate feedback and avoiding memory buildup.

Part of Phase 6: CPU Optimization
"""
from typing import Optional, Callable, Dict, List
from pathlib import Path
import re
import time


class StreamingFileWriter:
    """Writes files incrementally as code blocks are detected in stream

    This class buffers incoming tokens and detects complete code blocks,
    writing files as soon as each block is complete. This provides:
    - Real-time file creation feedback
    - Reduced memory usage for large generations
    - Better UX showing progress
    """

    def __init__(
        self,
        workspace_dir: Path,
        file_tools,
        on_file_start: Optional[Callable[[str], None]] = None,
        on_file_complete: Optional[Callable[[str, int], None]] = None,
        on_file_progress: Optional[Callable[[str, int], None]] = None
    ):
        """Initialize streaming writer

        Args:
            workspace_dir: Base directory for file operations
            file_tools: FileTools instance for writing files
            on_file_start: Callback when file write starts (filename)
            on_file_complete: Callback when file done (filename, bytes)
            on_file_progress: Callback for progress (filename, bytes so far)
        """
        self.workspace_dir = workspace_dir
        self.file_tools = file_tools
        self.on_file_start = on_file_start
        self.on_file_complete = on_file_complete
        self.on_file_progress = on_file_progress

        # Buffer for accumulating tokens
        self._buffer = ""

        # Current code block state
        self._in_code_block = False
        self._current_language = ""
        self._current_filename = ""
        self._code_content = ""

        # Track written files
        self._written_files: Dict[str, int] = {}  # filename -> bytes

        # Pattern for detecting file marker in code block
        self._file_pattern = re.compile(
            r'^#\s*(?:FILE|file|File):\s*([^\n]+)',
            re.MULTILINE
        )

    def process_token(self, token: str, target_filename: Optional[str] = None) -> None:
        """Process a single token from the stream

        Args:
            token: Token string from LLM
            target_filename: Optional target filename if known in advance
        """
        self._buffer += token

        # Check for code block start
        if not self._in_code_block:
            # Look for opening ```
            if '```' in self._buffer:
                parts = self._buffer.split('```', 1)
                if len(parts) == 2:
                    # Found start of code block
                    after_marker = parts[1]

                    # Extract language from first line
                    if '\n' in after_marker:
                        lang_line, rest = after_marker.split('\n', 1)
                        self._current_language = lang_line.strip()
                        self._code_content = rest
                    else:
                        # Haven't seen newline yet, buffer continues
                        return

                    self._in_code_block = True
                    self._buffer = ""

                    # Check for file marker in content
                    file_match = self._file_pattern.search(self._code_content)
                    if file_match:
                        self._current_filename = file_match.group(1).strip()
                        # Remove the file marker from content
                        self._code_content = self._file_pattern.sub('', self._code_content).lstrip('\n')
                    elif target_filename:
                        self._current_filename = target_filename
                    else:
                        # Infer filename from language
                        self._current_filename = self._infer_filename(self._current_language)

                    # Notify start
                    if self.on_file_start and self._current_filename:
                        self.on_file_start(self._current_filename)
        else:
            # Inside code block, look for closing ```
            self._code_content += token

            if '```' in self._code_content:
                # Found end of code block
                code_end_idx = self._code_content.rfind('```')
                complete_code = self._code_content[:code_end_idx].rstrip()

                # Write the file
                if self._current_filename and complete_code:
                    self._write_file(self._current_filename, complete_code)

                # Reset state
                remainder = self._code_content[code_end_idx + 3:]
                self._in_code_block = False
                self._current_language = ""
                self._current_filename = ""
                self._code_content = ""
                self._buffer = remainder
            else:
                # Still accumulating, notify progress
                if self.on_file_progress and self._current_filename:
                    self.on_file_progress(self._current_filename, len(self._code_content))

    def _infer_filename(self, language: str) -> str:
        """Infer filename from language identifier

        Args:
            language: Code block language (python, html, etc.)

        Returns:
            Suggested filename
        """
        ext_map = {
            'python': '.py',
            'py': '.py',
            'javascript': '.js',
            'js': '.js',
            'typescript': '.ts',
            'ts': '.ts',
            'html': '.html',
            'css': '.css',
            'json': '.json',
            'yaml': '.yaml',
            'yml': '.yml',
            'sql': '.sql',
            'bash': '.sh',
            'shell': '.sh',
            'sh': '.sh',
            'markdown': '.md',
            'md': '.md',
        }

        lang_lower = language.lower()
        ext = ext_map.get(lang_lower, '.txt')

        # Generate unique filename
        count = len([f for f in self._written_files if f.endswith(ext)]) + 1
        if count == 1:
            return f"output{ext}"
        return f"output_{count}{ext}"

    def _write_file(self, filename: str, content: str) -> bool:
        """Write file to workspace

        Args:
            filename: Target filename
            content: File content

        Returns:
            True if successful
        """
        try:
            file_path = Path(filename)

            # Ensure parent directories exist
            if file_path.parent and str(file_path.parent) != '.':
                parent_dir = self.workspace_dir / file_path.parent
                parent_dir.mkdir(parents=True, exist_ok=True)

            # Write file
            result = self.file_tools.write_file(filename, content, overwrite=True)

            if result.get('success', False):
                self._written_files[filename] = len(content)

                # Notify completion
                if self.on_file_complete:
                    self.on_file_complete(filename, len(content))

                return True
            else:
                print(f"   ⚠️  Failed to write {filename}: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"   ⚠️  Error writing {filename}: {e}")
            return False

    def flush(self, target_filename: Optional[str] = None) -> Optional[str]:
        """Flush any remaining buffered content

        Call this at the end of streaming to handle any incomplete
        code blocks or content that wasn't written.

        Args:
            target_filename: Filename to use if buffer has content

        Returns:
            Any remaining content that wasn't in code blocks
        """
        remaining = ""

        # If still in a code block, write what we have
        if self._in_code_block and self._code_content:
            # Remove any partial closing marker
            content = self._code_content.rstrip('`').rstrip()
            if content:
                filename = self._current_filename or target_filename or "incomplete_output.txt"
                self._write_file(filename, content)

        # Return any non-code content
        if self._buffer:
            remaining = self._buffer

        # Reset state
        self._reset()

        return remaining

    def _reset(self) -> None:
        """Reset internal state"""
        self._buffer = ""
        self._in_code_block = False
        self._current_language = ""
        self._current_filename = ""
        self._code_content = ""

    def get_written_files(self) -> Dict[str, int]:
        """Get dictionary of written files and their sizes

        Returns:
            Dict mapping filename to bytes written
        """
        return self._written_files.copy()

    def get_total_bytes_written(self) -> int:
        """Get total bytes written across all files

        Returns:
            Total bytes
        """
        return sum(self._written_files.values())


class StreamingCodeGenerator:
    """Wrapper for LLM that streams and writes files in real-time

    Integrates streaming generation with file writing for immediate
    feedback during code generation.
    """

    def __init__(
        self,
        model,
        workspace_dir: Path,
        file_tools,
        show_progress: bool = True
    ):
        """Initialize streaming generator

        Args:
            model: LLM model with streaming support
            workspace_dir: Workspace directory
            file_tools: FileTools instance
            show_progress: Whether to show progress messages
        """
        self.model = model
        self.workspace_dir = workspace_dir
        self.file_tools = file_tools
        self.show_progress = show_progress

    def generate_and_write(
        self,
        prompt: str,
        target_filename: Optional[str] = None,
        max_tokens: int = 256,
        temperature: float = 0.3,
        timeout_seconds: int = 300
    ) -> Dict:
        """Generate code and write files in real-time

        Args:
            prompt: Generation prompt
            target_filename: Expected filename (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            timeout_seconds: Generation timeout

        Returns:
            Dict with results: files_written, total_bytes, elapsed_time, full_output
        """
        start_time = time.time()
        token_count = 0
        full_output = ""

        # Set up streaming writer with callbacks
        def on_start(filename):
            if self.show_progress:
                print(f"\n   📝 Writing {filename}...", end="", flush=True)

        def on_complete(filename, bytes_written):
            if self.show_progress:
                print(f" ✓ ({bytes_written} bytes)")

        def on_progress(filename, bytes_so_far):
            if self.show_progress and bytes_so_far % 500 == 0:  # Update every 500 bytes
                print(f"\r   📝 Writing {filename}... {bytes_so_far} bytes", end="", flush=True)

        writer = StreamingFileWriter(
            workspace_dir=self.workspace_dir,
            file_tools=self.file_tools,
            on_file_start=on_start,
            on_file_complete=on_complete,
            on_file_progress=on_progress
        )

        try:
            # Stream from model
            stream = self.model(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=[],
                echo=False,
                stream=True
            )

            last_progress = start_time

            for chunk in stream:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    break

                # Extract token
                if 'choices' in chunk and chunk['choices']:
                    token_text = chunk['choices'][0].get('text', '')
                    if token_text:
                        full_output += token_text
                        token_count += 1

                        # Process through streaming writer
                        writer.process_token(token_text, target_filename)

                        # Show general progress every 3 seconds
                        current = time.time()
                        if self.show_progress and current - last_progress >= 3.0:
                            tps = token_count / (current - start_time)
                            print(f"\r   → {token_count} tokens ({tps:.1f} tok/s)", end="", flush=True)
                            last_progress = current

            # Flush any remaining content
            remaining = writer.flush(target_filename)

            elapsed = time.time() - start_time

            # Final summary
            if self.show_progress:
                files = writer.get_written_files()
                if files:
                    print(f"\n   ✓ Generated {len(files)} file(s) in {elapsed:.1f}s")

            return {
                'files_written': writer.get_written_files(),
                'total_bytes': writer.get_total_bytes_written(),
                'elapsed_time': elapsed,
                'token_count': token_count,
                'full_output': full_output,
                'remaining_text': remaining
            }

        except Exception as e:
            # Try to flush on error
            writer.flush(target_filename)

            return {
                'files_written': writer.get_written_files(),
                'total_bytes': writer.get_total_bytes_written(),
                'elapsed_time': time.time() - start_time,
                'token_count': token_count,
                'full_output': full_output,
                'error': str(e)
            }
