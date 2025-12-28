"""Incremental Generator - Streaming-like token generation for CPU

This module provides streaming-like output for llama.cpp models by:
1. Using the model's streaming API when available
2. Implementing chunk-based generation with intermediate output
3. Providing progress callbacks during long generations

Part of Phase 6: CPU Optimization
"""
from typing import Generator, Optional, Callable, Dict, Any, List
from dataclasses import dataclass
import time
import threading
import queue


@dataclass
class GenerationProgress:
    """Progress information during generation"""
    tokens_generated: int
    estimated_total: int
    elapsed_time: float
    tokens_per_second: float
    current_text: str
    is_complete: bool = False
    error: Optional[str] = None


class IncrementalGenerator:
    """Provides streaming-like generation for CPU inference

    On CPU, token generation is slow (~5-10 tokens/sec). This class
    provides mechanisms to:
    1. Stream tokens as they're generated (reduces perceived latency)
    2. Show progress during long generations
    3. Allow early termination if output looks complete
    4. Chunk large generations into smaller pieces
    """

    def __init__(self, model=None):
        """Initialize generator

        Args:
            model: llama-cpp-python model instance
        """
        self.model = model
        self._stop_generation = False
        self._generation_queue = queue.Queue()

    def set_model(self, model):
        """Set or update the model"""
        self.model = model

    def generate_streaming(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stop: Optional[List[str]] = None,
        on_token: Optional[Callable[[str, GenerationProgress], None]] = None,
        on_complete: Optional[Callable[[str, GenerationProgress], None]] = None
    ) -> Generator[str, None, str]:
        """Generate text with streaming output

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop: Stop sequences
            on_token: Callback for each token (token, progress)
            on_complete: Callback when generation completes

        Yields:
            Generated text chunks

        Returns:
            Complete generated text
        """
        if not self.model:
            raise RuntimeError("Model not set. Call set_model() first.")

        self._stop_generation = False
        start_time = time.time()
        generated_text = ""
        tokens_generated = 0

        try:
            # Use llama-cpp's streaming API
            stream = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or [],
                echo=False,
                stream=True  # Enable streaming
            )

            for chunk in stream:
                if self._stop_generation:
                    break

                # Extract token text from chunk
                if 'choices' in chunk and chunk['choices']:
                    token_text = chunk['choices'][0].get('text', '')
                    if token_text:
                        generated_text += token_text
                        tokens_generated += 1

                        # Calculate progress
                        elapsed = time.time() - start_time
                        tps = tokens_generated / elapsed if elapsed > 0 else 0

                        progress = GenerationProgress(
                            tokens_generated=tokens_generated,
                            estimated_total=max_tokens,
                            elapsed_time=elapsed,
                            tokens_per_second=tps,
                            current_text=generated_text,
                            is_complete=False
                        )

                        # Invoke callback
                        if on_token:
                            on_token(token_text, progress)

                        yield token_text

            # Mark complete
            elapsed = time.time() - start_time
            tps = tokens_generated / elapsed if elapsed > 0 else 0

            final_progress = GenerationProgress(
                tokens_generated=tokens_generated,
                estimated_total=tokens_generated,  # Actual count
                elapsed_time=elapsed,
                tokens_per_second=tps,
                current_text=generated_text,
                is_complete=True
            )

            if on_complete:
                on_complete(generated_text, final_progress)

            return generated_text

        except Exception as e:
            error_progress = GenerationProgress(
                tokens_generated=tokens_generated,
                estimated_total=max_tokens,
                elapsed_time=time.time() - start_time,
                tokens_per_second=0,
                current_text=generated_text,
                is_complete=True,
                error=str(e)
            )

            if on_complete:
                on_complete(generated_text, error_progress)

            raise

    def generate_with_progress(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stop: Optional[List[str]] = None,
        progress_interval: float = 1.0
    ) -> tuple[str, GenerationProgress]:
        """Generate with periodic progress updates

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop: Stop sequences
            progress_interval: Seconds between progress updates

        Returns:
            Tuple of (generated_text, final_progress)
        """
        if not self.model:
            raise RuntimeError("Model not set. Call set_model() first.")

        start_time = time.time()
        last_progress_time = start_time

        def show_progress(token: str, progress: GenerationProgress):
            nonlocal last_progress_time
            current_time = time.time()

            if current_time - last_progress_time >= progress_interval:
                pct = (progress.tokens_generated / progress.estimated_total) * 100
                print(f"\r   Progress: {progress.tokens_generated}/{progress.estimated_total} tokens "
                      f"({pct:.0f}%) | {progress.tokens_per_second:.1f} tok/s | "
                      f"{progress.elapsed_time:.1f}s elapsed", end="", flush=True)
                last_progress_time = current_time

        # Collect all tokens
        full_text = ""
        final_progress = None

        def on_complete(text: str, progress: GenerationProgress):
            nonlocal final_progress
            final_progress = progress
            print()  # Newline after progress

        for _ in self.generate_streaming(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
            on_token=show_progress,
            on_complete=on_complete
        ):
            pass

        # The generator already set final_progress via on_complete
        # Return the result
        return full_text, final_progress

    def generate_chunked(
        self,
        prompt: str,
        max_tokens: int = 512,
        chunk_size: int = 100,
        temperature: float = 0.3,
        stop: Optional[List[str]] = None,
        on_chunk: Optional[Callable[[str, int], None]] = None
    ) -> str:
        """Generate in chunks, returning partial results

        This is useful for very long generations where you want
        to process/display partial output before completion.

        Args:
            prompt: Input prompt
            max_tokens: Maximum total tokens
            chunk_size: Tokens per chunk
            temperature: Sampling temperature
            stop: Stop sequences
            on_chunk: Callback for each chunk (chunk_text, chunk_number)

        Returns:
            Complete generated text
        """
        if not self.model:
            raise RuntimeError("Model not set. Call set_model() first.")

        full_text = ""
        chunk_num = 0
        remaining_tokens = max_tokens
        current_prompt = prompt

        while remaining_tokens > 0:
            # Generate one chunk
            chunk_tokens = min(chunk_size, remaining_tokens)

            try:
                response = self.model(
                    current_prompt,
                    max_tokens=chunk_tokens,
                    temperature=temperature,
                    stop=stop or [],
                    echo=False
                )

                chunk_text = response['choices'][0]['text'] if response.get('choices') else ""

                if not chunk_text:
                    break  # Model stopped generating

                full_text += chunk_text
                chunk_num += 1
                remaining_tokens -= chunk_tokens

                # Callback
                if on_chunk:
                    on_chunk(chunk_text, chunk_num)

                # Check for stop sequences in output
                if stop:
                    for seq in stop:
                        if seq in chunk_text:
                            # Found stop sequence, trim and finish
                            idx = full_text.find(seq)
                            if idx != -1:
                                full_text = full_text[:idx]
                            remaining_tokens = 0
                            break

                # Update prompt for continuation
                current_prompt = prompt + full_text

            except Exception as e:
                print(f"\n   ⚠️  Chunk {chunk_num} generation failed: {e}")
                break

        return full_text

    def stop(self):
        """Stop ongoing generation"""
        self._stop_generation = True


class ProgressDisplay:
    """Utility for displaying generation progress"""

    def __init__(self, show_tokens: bool = True, show_speed: bool = True):
        self.show_tokens = show_tokens
        self.show_speed = show_speed
        self._spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self._spinner_idx = 0

    def format_progress(self, progress: GenerationProgress) -> str:
        """Format progress for display"""
        parts = []

        # Spinner
        spinner = self._spinner_chars[self._spinner_idx % len(self._spinner_chars)]
        self._spinner_idx += 1
        parts.append(spinner)

        # Tokens
        if self.show_tokens:
            pct = (progress.tokens_generated / progress.estimated_total * 100) if progress.estimated_total > 0 else 0
            parts.append(f"{progress.tokens_generated}/{progress.estimated_total} ({pct:.0f}%)")

        # Speed
        if self.show_speed:
            parts.append(f"{progress.tokens_per_second:.1f} tok/s")

        # Time
        parts.append(f"{progress.elapsed_time:.1f}s")

        return " | ".join(parts)

    def print_progress(self, progress: GenerationProgress):
        """Print progress to console"""
        line = self.format_progress(progress)
        print(f"\r   {line}", end="", flush=True)

    def print_complete(self, progress: GenerationProgress):
        """Print completion message"""
        print(f"\n   ✓ Generated {progress.tokens_generated} tokens in {progress.elapsed_time:.1f}s "
              f"({progress.tokens_per_second:.1f} tok/s)")


class TimeoutGenerator:
    """Generator with built-in timeout handling"""

    def __init__(self, generator: IncrementalGenerator, timeout_seconds: int = 120):
        """Initialize timeout generator

        Args:
            generator: IncrementalGenerator instance
            timeout_seconds: Maximum generation time
        """
        self.generator = generator
        self.timeout = timeout_seconds
        self._result = None
        self._error = None

    def generate_with_timeout(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stop: Optional[List[str]] = None
    ) -> tuple[str, bool]:
        """Generate with timeout, returns partial result if timeout

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            stop: Stop sequences

        Returns:
            Tuple of (text, completed) where completed is False if timed out
        """
        start_time = time.time()
        generated_text = ""
        completed = True

        def on_token(token: str, progress: GenerationProgress):
            nonlocal generated_text
            generated_text = progress.current_text

            # Check timeout
            if progress.elapsed_time > self.timeout:
                self.generator.stop()

        try:
            for _ in self.generator.generate_streaming(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
                on_token=on_token
            ):
                if time.time() - start_time > self.timeout:
                    completed = False
                    break

        except Exception as e:
            completed = False
            print(f"\n   ⚠️  Generation error: {e}")

        return generated_text, completed


def create_progress_bar(width: int = 40) -> Callable[[GenerationProgress], str]:
    """Create a progress bar formatter

    Args:
        width: Width of progress bar in characters

    Returns:
        Function that formats GenerationProgress as progress bar
    """
    def format_bar(progress: GenerationProgress) -> str:
        pct = progress.tokens_generated / progress.estimated_total if progress.estimated_total > 0 else 0
        filled = int(width * pct)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {pct*100:.0f}% | {progress.tokens_per_second:.1f} tok/s"

    return format_bar
