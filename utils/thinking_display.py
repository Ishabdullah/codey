"""Thinking Display - Show LLM reasoning and processing steps

This module provides real-time feedback about what the system is doing,
similar to Perplexity's "Searching...", "Analyzing..." displays.
"""
import sys
import time
from contextlib import contextmanager
from enum import Enum
from typing import Optional


class ThinkingStep(Enum):
    """Types of thinking steps to display"""
    CLASSIFYING = "🔍 Classifying intent"
    ROUTING = "🧭 Routing request"
    LOADING_MODEL = "📦 Loading model"
    THINKING = "💭 Thinking"
    GENERATING_CODE = "⚙️  Generating code"
    PARSING_RESPONSE = "📝 Parsing response"
    EXECUTING_TOOL = "🔧 Executing tool"
    VALIDATING = "✓ Validating output"
    APPLYING_EDITS = "📄 Applying edits"
    CREATING_PLAN = "📋 Creating execution plan"
    ANALYZING = "🔬 Analyzing request"
    SEARCHING = "🔎 Searching codebase"
    COMPLETE = "✓ Complete"


class ThinkingDisplay:
    """Display system for showing LLM reasoning steps"""

    def __init__(self, enabled: bool = True, verbose: bool = False):
        """Initialize thinking display

        Args:
            enabled: Whether to show thinking steps
            verbose: Show detailed substeps and timing
        """
        self.enabled = enabled
        self.verbose = verbose
        self._current_step = None
        self._step_start_time = None
        self._spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_index = 0

    def step(self, step: ThinkingStep, detail: Optional[str] = None) -> None:
        """Show a thinking step

        Args:
            step: Type of step being performed
            detail: Optional detail about the step
        """
        if not self.enabled:
            return

        # Complete previous step if any
        if self._current_step:
            self._complete_step()

        # Start new step
        self._current_step = step
        self._step_start_time = time.time()

        # Display step
        message = step.value
        if detail:
            message += f": {detail}"

        print(f"\n{message}...", end="", flush=True)

    def substep(self, detail: str) -> None:
        """Show a substep detail (only if verbose)

        Args:
            detail: Detail about current substep
        """
        if not self.enabled or not self.verbose:
            return

        print(f"\n  → {detail}", end="", flush=True)

    def update(self, message: str) -> None:
        """Update current step with new info

        Args:
            message: Update message
        """
        if not self.enabled:
            return

        print(f" {message}", end="", flush=True)

    def spinner(self) -> None:
        """Show a spinner (for long operations)"""
        if not self.enabled:
            return

        char = self._spinner_chars[self._spinner_index]
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
        print(f"\r{char} {self._current_step.value}...", end="", flush=True)

    def _complete_step(self) -> None:
        """Mark current step as complete"""
        if not self._current_step:
            return

        elapsed = time.time() - self._step_start_time if self._step_start_time else 0

        if self.verbose and elapsed > 0.1:
            print(f" ✓ ({elapsed:.1f}s)", flush=True)
        else:
            print(" ✓", flush=True)

        self._current_step = None
        self._step_start_time = None

    def complete(self, message: Optional[str] = None) -> None:
        """Mark entire operation as complete

        Args:
            message: Optional completion message
        """
        if not self.enabled:
            return

        # Complete any pending step
        if self._current_step:
            self._complete_step()

        if message:
            print(f"\n✓ {message}")
        else:
            print(f"\n{ThinkingStep.COMPLETE.value}")

    def error(self, message: str) -> None:
        """Show an error

        Args:
            message: Error message
        """
        if not self.enabled:
            return

        print(f"\n✗ Error: {message}", file=sys.stderr)
        self._current_step = None

    def info(self, message: str) -> None:
        """Show informational message

        Args:
            message: Info message
        """
        if not self.enabled:
            return

        print(f"\nℹ {message}")

    @contextmanager
    def thinking(self, step: ThinkingStep, detail: Optional[str] = None):
        """Context manager for a thinking step

        Usage:
            with display.thinking(ThinkingStep.LOADING_MODEL, "Qwen2.5-Coder 7B"):
                # Load model
                model.load()

        Args:
            step: Type of step
            detail: Optional detail
        """
        self.step(step, detail)
        try:
            yield self
        finally:
            self._complete_step()


# Global instance for convenience
_global_display = ThinkingDisplay(enabled=True, verbose=False)


def get_display() -> ThinkingDisplay:
    """Get global thinking display instance"""
    return _global_display


def set_enabled(enabled: bool) -> None:
    """Enable/disable thinking display globally"""
    _global_display.enabled = enabled


def set_verbose(verbose: bool) -> None:
    """Enable/disable verbose mode globally"""
    _global_display.verbose = verbose


# Convenience functions for direct use
def step(thinking_step: ThinkingStep, detail: Optional[str] = None) -> None:
    """Show a thinking step"""
    _global_display.step(thinking_step, detail)


def substep(detail: str) -> None:
    """Show a substep"""
    _global_display.substep(detail)


def update(message: str) -> None:
    """Update current step"""
    _global_display.update(message)


def complete(message: Optional[str] = None) -> None:
    """Mark as complete"""
    _global_display.complete(message)


def error(message: str) -> None:
    """Show error"""
    _global_display.error(message)


def info(message: str) -> None:
    """Show info"""
    _global_display.info(message)


@contextmanager
def thinking(step: ThinkingStep, detail: Optional[str] = None):
    """Context manager for thinking step"""
    with _global_display.thinking(step, detail) as display:
        yield display
