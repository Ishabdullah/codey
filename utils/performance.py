"""Performance utilities - timing and metrics tracking"""
import time
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class TimingResult:
    """Result of a timing operation"""
    operation: str
    duration_ms: float
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return f"{self.operation}: {self.duration_ms:.1f}ms [{status}]"


@dataclass
class RequestMetrics:
    """Metrics for a complete request"""
    request_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    timings: List[TimingResult] = field(default_factory=list)

    # Token counts
    input_tokens: int = 0
    output_tokens: int = 0

    # Component timings (for quick access)
    router_ms: Optional[float] = None
    model_load_ms: Optional[float] = None
    generation_ms: Optional[float] = None

    @property
    def total_duration_ms(self) -> float:
        """Total request duration in milliseconds"""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    @property
    def tokens_per_second(self) -> float:
        """Output tokens per second (generation speed)"""
        if self.generation_ms and self.generation_ms > 0 and self.output_tokens > 0:
            return self.output_tokens / (self.generation_ms / 1000)
        return 0.0

    def add_timing(self, timing: TimingResult) -> None:
        """Add a timing result to this request"""
        self.timings.append(timing)

        # Update component shortcuts
        if 'router' in timing.operation.lower():
            self.router_ms = timing.duration_ms
        elif 'load' in timing.operation.lower():
            self.model_load_ms = timing.duration_ms
        elif 'generat' in timing.operation.lower():
            self.generation_ms = timing.duration_ms

    def complete(self) -> None:
        """Mark request as complete"""
        self.end_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'request_id': self.request_id,
            'total_duration_ms': round(self.total_duration_ms, 1),
            'router_ms': round(self.router_ms, 1) if self.router_ms else None,
            'model_load_ms': round(self.model_load_ms, 1) if self.model_load_ms else None,
            'generation_ms': round(self.generation_ms, 1) if self.generation_ms else None,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'tokens_per_second': round(self.tokens_per_second, 1) if self.tokens_per_second else None,
            'timings': [str(t) for t in self.timings]
        }

    def summary(self) -> str:
        """Generate summary string for display"""
        parts = []
        parts.append(f"Total: {self.total_duration_ms:.0f}ms")

        if self.router_ms:
            parts.append(f"Router: {self.router_ms:.0f}ms")

        if self.model_load_ms:
            parts.append(f"Load: {self.model_load_ms:.0f}ms")

        if self.generation_ms:
            parts.append(f"Generate: {self.generation_ms:.0f}ms")

        if self.output_tokens > 0:
            parts.append(f"Tokens: {self.output_tokens}")
            if self.tokens_per_second > 0:
                parts.append(f"Speed: {self.tokens_per_second:.1f} tok/s")

        return " | ".join(parts)


class PerformanceTracker:
    """Track performance metrics for requests"""

    def __init__(self, enabled: bool = True):
        """Initialize performance tracker

        Args:
            enabled: Whether to track performance
        """
        self.enabled = enabled
        self._current_request: Optional[RequestMetrics] = None
        self._request_counter = 0
        self._history: List[RequestMetrics] = []
        self._max_history = 100  # Keep last N requests

    def start_request(self) -> RequestMetrics:
        """Start tracking a new request"""
        self._request_counter += 1
        self._current_request = RequestMetrics(
            request_id=f"req_{self._request_counter:04d}"
        )
        return self._current_request

    def end_request(self) -> Optional[RequestMetrics]:
        """End current request tracking"""
        if self._current_request:
            self._current_request.complete()

            # Store in history
            self._history.append(self._current_request)
            if len(self._history) > self._max_history:
                self._history.pop(0)

            # Log summary
            if self.enabled:
                logger.info(f"[PERF] {self._current_request.summary()}")

            result = self._current_request
            self._current_request = None
            return result
        return None

    def add_timing(self, operation: str, duration_ms: float,
                   success: bool = True, **metadata) -> None:
        """Add a timing result to current request"""
        if not self._current_request:
            return

        timing = TimingResult(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata
        )
        self._current_request.add_timing(timing)

        if self.enabled:
            logger.debug(f"[PERF] {timing}")

    def set_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Set token counts for current request"""
        if self._current_request:
            self._current_request.input_tokens = input_tokens
            self._current_request.output_tokens = output_tokens

    @contextmanager
    def time_operation(self, operation: str, **metadata):
        """Context manager for timing an operation

        Usage:
            with tracker.time_operation("router_classify"):
                result = router.classify(input)
        """
        start = time.time()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration_ms = (time.time() - start) * 1000
            self.add_timing(operation, duration_ms, success, **metadata)

    def get_average_stats(self) -> Dict[str, float]:
        """Get average statistics from history"""
        if not self._history:
            return {}

        total_count = len(self._history)
        avg_total = sum(r.total_duration_ms for r in self._history) / total_count

        router_times = [r.router_ms for r in self._history if r.router_ms]
        avg_router = sum(router_times) / len(router_times) if router_times else 0

        load_times = [r.model_load_ms for r in self._history if r.model_load_ms]
        avg_load = sum(load_times) / len(load_times) if load_times else 0

        gen_times = [r.generation_ms for r in self._history if r.generation_ms]
        avg_gen = sum(gen_times) / len(gen_times) if gen_times else 0

        output_tokens = [r.output_tokens for r in self._history if r.output_tokens]
        avg_tokens = sum(output_tokens) / len(output_tokens) if output_tokens else 0

        return {
            'requests': total_count,
            'avg_total_ms': round(avg_total, 1),
            'avg_router_ms': round(avg_router, 1),
            'avg_load_ms': round(avg_load, 1),
            'avg_generation_ms': round(avg_gen, 1),
            'avg_output_tokens': round(avg_tokens, 0)
        }


# Global instance for convenience
_global_tracker = PerformanceTracker(enabled=True)


def get_tracker() -> PerformanceTracker:
    """Get global performance tracker"""
    return _global_tracker


def start_request() -> RequestMetrics:
    """Start tracking a new request"""
    return _global_tracker.start_request()


def end_request() -> Optional[RequestMetrics]:
    """End current request tracking"""
    return _global_tracker.end_request()


def add_timing(operation: str, duration_ms: float,
               success: bool = True, **metadata) -> None:
    """Add a timing result"""
    _global_tracker.add_timing(operation, duration_ms, success, **metadata)


def set_tokens(input_tokens: int = 0, output_tokens: int = 0) -> None:
    """Set token counts"""
    _global_tracker.set_tokens(input_tokens, output_tokens)


@contextmanager
def time_operation(operation: str, **metadata):
    """Context manager for timing an operation"""
    with _global_tracker.time_operation(operation, **metadata):
        yield


def timed(operation_name: str = None):
    """Decorator for timing functions

    Usage:
        @timed("router_classify")
        def classify(self, input):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            with time_operation(op_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def estimate_tokens(text: str) -> int:
    """Estimate token count for text

    Uses a simple heuristic: ~4 characters per token
    This is approximate and works for most English text.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    # Roughly 4 characters per token for English
    # This is a common approximation used by many systems
    return max(1, len(text) // 4)
