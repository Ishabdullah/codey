"""Progress Tracker - Real-time step reporting for multi-step tasks

This module provides comprehensive progress tracking for:
1. Multi-step task execution
2. Code generation phases
3. File operations
4. Model loading/switching

Part of Phase 6: CPU Optimization
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime
import time
import json
from pathlib import Path


class TaskPhase(Enum):
    """High-level phases of task execution"""
    PLANNING = "planning"
    MODEL_LOADING = "model_loading"
    GENERATION = "generation"
    FILE_OPERATIONS = "file_operations"
    VALIDATION = "validation"
    CLEANUP = "cleanup"
    COMPLETE = "complete"
    FAILED = "failed"


class StepType(Enum):
    """Types of steps within a phase"""
    ANALYZE = "analyze"
    DECOMPOSE = "decompose"
    LOAD_ROUTER = "load_router"
    LOAD_CODER = "load_coder"
    LOAD_ALGORITHM = "load_algorithm"
    UNLOAD_MODEL = "unload_model"
    GENERATE_CODE = "generate_code"
    GENERATE_CHUNK = "generate_chunk"
    WRITE_FILE = "write_file"
    CREATE_DIR = "create_dir"
    RUN_COMMAND = "run_command"
    VALIDATE = "validate"
    README_GENERATE = "readme_generate"


@dataclass
class StepProgress:
    """Progress information for a single step"""
    step_id: str
    step_type: StepType
    description: str
    status: str = "pending"  # pending, running, completed, failed, skipped
    progress_pct: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return 0.0


@dataclass
class PhaseProgress:
    """Progress information for a phase"""
    phase: TaskPhase
    steps: List[StepProgress] = field(default_factory=list)
    status: str = "pending"
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == "completed")

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def progress_pct(self) -> float:
        if not self.steps:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100


@dataclass
class TaskProgress:
    """Overall task progress"""
    task_id: str
    task_description: str
    phases: List[PhaseProgress] = field(default_factory=list)
    current_phase: Optional[TaskPhase] = None
    current_step: Optional[str] = None
    status: str = "pending"
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def overall_progress(self) -> float:
        if not self.phases:
            return 0.0
        total_steps = sum(p.total_steps for p in self.phases)
        completed = sum(p.completed_steps for p in self.phases)
        return (completed / total_steps * 100) if total_steps > 0 else 0.0


class ProgressCallback:
    """Abstract callback interface for progress events"""

    def on_task_start(self, task: TaskProgress):
        pass

    def on_phase_start(self, task: TaskProgress, phase: PhaseProgress):
        pass

    def on_phase_complete(self, task: TaskProgress, phase: PhaseProgress):
        pass

    def on_step_start(self, task: TaskProgress, step: StepProgress):
        pass

    def on_step_progress(self, task: TaskProgress, step: StepProgress, pct: float):
        pass

    def on_step_complete(self, task: TaskProgress, step: StepProgress):
        pass

    def on_step_failed(self, task: TaskProgress, step: StepProgress, error: str):
        pass

    def on_task_complete(self, task: TaskProgress):
        pass

    def on_task_failed(self, task: TaskProgress, error: str):
        pass


class ConsoleProgressCallback(ProgressCallback):
    """Progress callback that prints to console with nice formatting"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._phase_icons = {
            TaskPhase.PLANNING: "📋",
            TaskPhase.MODEL_LOADING: "📦",
            TaskPhase.GENERATION: "⚙️",
            TaskPhase.FILE_OPERATIONS: "💾",
            TaskPhase.VALIDATION: "✅",
            TaskPhase.CLEANUP: "🧹",
            TaskPhase.COMPLETE: "✓",
            TaskPhase.FAILED: "✗",
        }
        self._step_icons = {
            StepType.ANALYZE: "🔍",
            StepType.DECOMPOSE: "📊",
            StepType.LOAD_ROUTER: "🔌",
            StepType.LOAD_CODER: "🧠",
            StepType.LOAD_ALGORITHM: "🎯",
            StepType.UNLOAD_MODEL: "📤",
            StepType.GENERATE_CODE: "💻",
            StepType.GENERATE_CHUNK: "🧩",
            StepType.WRITE_FILE: "📝",
            StepType.CREATE_DIR: "📁",
            StepType.RUN_COMMAND: "🖥️",
            StepType.VALIDATE: "🔎",
            StepType.README_GENERATE: "📖",
        }

    def on_task_start(self, task: TaskProgress):
        print(f"\n{'='*60}")
        print(f"🚀 Starting: {task.task_description[:50]}...")
        print(f"   Task ID: {task.task_id}")
        print(f"{'='*60}")

    def on_phase_start(self, task: TaskProgress, phase: PhaseProgress):
        icon = self._phase_icons.get(phase.phase, "▶")
        print(f"\n{icon} Phase: {phase.phase.value.upper()}")
        if self.verbose and phase.steps:
            print(f"   Steps: {len(phase.steps)}")

    def on_phase_complete(self, task: TaskProgress, phase: PhaseProgress):
        duration = phase.end_time - phase.start_time if phase.end_time and phase.start_time else 0
        print(f"   ✓ Phase complete ({duration:.1f}s)")

    def on_step_start(self, task: TaskProgress, step: StepProgress):
        icon = self._step_icons.get(step.step_type, "•")
        print(f"   {icon} {step.description}...", end="", flush=True)

    def on_step_progress(self, task: TaskProgress, step: StepProgress, pct: float):
        if self.verbose:
            print(f" [{pct:.0f}%]", end="", flush=True)

    def on_step_complete(self, task: TaskProgress, step: StepProgress):
        print(f" ✓ ({step.duration:.1f}s)")

    def on_step_failed(self, task: TaskProgress, step: StepProgress, error: str):
        print(f" ✗ FAILED")
        print(f"      Error: {error[:100]}")

    def on_task_complete(self, task: TaskProgress):
        duration = task.end_time - task.start_time if task.end_time and task.start_time else 0
        print(f"\n{'='*60}")
        print(f"✓ Task completed successfully!")
        print(f"  Total time: {duration:.1f}s")
        print(f"  Progress: {task.overall_progress:.0f}%")
        print(f"{'='*60}\n")

    def on_task_failed(self, task: TaskProgress, error: str):
        print(f"\n{'='*60}")
        print(f"✗ Task failed!")
        print(f"  Error: {error}")
        print(f"{'='*60}\n")


class ProgressTracker:
    """Tracks and reports progress for multi-step tasks

    Usage:
        tracker = ProgressTracker()
        tracker.start_task("Generate full-stack app")

        tracker.start_phase(TaskPhase.PLANNING)
        tracker.start_step("analyze", StepType.ANALYZE, "Analyzing request")
        # ... do work ...
        tracker.complete_step("analyze")
        tracker.complete_phase()

        tracker.complete_task()
    """

    def __init__(self, callback: Optional[ProgressCallback] = None):
        """Initialize tracker

        Args:
            callback: Optional callback for progress events
        """
        self.callback = callback or ConsoleProgressCallback()
        self._task: Optional[TaskProgress] = None
        self._current_phase: Optional[PhaseProgress] = None
        self._step_counter = 0

    @property
    def current_task(self) -> Optional[TaskProgress]:
        return self._task

    def start_task(self, description: str, task_id: Optional[str] = None) -> TaskProgress:
        """Start tracking a new task

        Args:
            description: Task description
            task_id: Optional task ID (auto-generated if not provided)

        Returns:
            TaskProgress instance
        """
        self._step_counter = 0
        task_id = task_id or f"task_{int(time.time() * 1000)}"

        self._task = TaskProgress(
            task_id=task_id,
            task_description=description,
            status="running",
            start_time=time.time()
        )

        self.callback.on_task_start(self._task)
        return self._task

    def start_phase(self, phase: TaskPhase) -> PhaseProgress:
        """Start a new phase

        Args:
            phase: TaskPhase to start

        Returns:
            PhaseProgress instance
        """
        if not self._task:
            raise RuntimeError("No task started. Call start_task() first.")

        # Complete previous phase if any
        if self._current_phase and self._current_phase.status == "running":
            self.complete_phase()

        phase_progress = PhaseProgress(
            phase=phase,
            status="running",
            start_time=time.time()
        )

        self._task.phases.append(phase_progress)
        self._task.current_phase = phase
        self._current_phase = phase_progress

        self.callback.on_phase_start(self._task, phase_progress)
        return phase_progress

    def complete_phase(self):
        """Complete current phase"""
        if self._current_phase:
            self._current_phase.status = "completed"
            self._current_phase.end_time = time.time()
            self.callback.on_phase_complete(self._task, self._current_phase)
            self._current_phase = None

    def start_step(
        self,
        step_id: str,
        step_type: StepType,
        description: str,
        details: Optional[Dict[str, Any]] = None
    ) -> StepProgress:
        """Start a new step within current phase

        Args:
            step_id: Unique step identifier
            step_type: Type of step
            description: Human-readable description
            details: Optional additional details

        Returns:
            StepProgress instance
        """
        if not self._current_phase:
            raise RuntimeError("No phase started. Call start_phase() first.")

        self._step_counter += 1
        step = StepProgress(
            step_id=step_id,
            step_type=step_type,
            description=description,
            status="running",
            start_time=time.time(),
            details=details or {}
        )

        self._current_phase.steps.append(step)
        self._task.current_step = step_id

        self.callback.on_step_start(self._task, step)
        return step

    def update_step_progress(self, step_id: str, progress_pct: float, details: Optional[Dict[str, Any]] = None):
        """Update progress for a step

        Args:
            step_id: Step identifier
            progress_pct: Progress percentage (0-100)
            details: Optional updated details
        """
        step = self._find_step(step_id)
        if step:
            step.progress_pct = progress_pct
            if details:
                step.details.update(details)
            self.callback.on_step_progress(self._task, step, progress_pct)

    def complete_step(self, step_id: str, details: Optional[Dict[str, Any]] = None):
        """Complete a step

        Args:
            step_id: Step identifier
            details: Optional final details
        """
        step = self._find_step(step_id)
        if step:
            step.status = "completed"
            step.progress_pct = 100.0
            step.end_time = time.time()
            if details:
                step.details.update(details)
            self.callback.on_step_complete(self._task, step)

    def fail_step(self, step_id: str, error: str):
        """Mark a step as failed

        Args:
            step_id: Step identifier
            error: Error message
        """
        step = self._find_step(step_id)
        if step:
            step.status = "failed"
            step.error = error
            step.end_time = time.time()
            self.callback.on_step_failed(self._task, step, error)

    def skip_step(self, step_id: str, reason: str = ""):
        """Skip a step

        Args:
            step_id: Step identifier
            reason: Optional reason for skipping
        """
        step = self._find_step(step_id)
        if step:
            step.status = "skipped"
            step.details['skip_reason'] = reason
            step.end_time = time.time()

    def complete_task(self, metadata: Optional[Dict[str, Any]] = None) -> TaskProgress:
        """Complete the current task

        Args:
            metadata: Optional final metadata

        Returns:
            Final TaskProgress
        """
        if not self._task:
            raise RuntimeError("No task to complete")

        # Complete current phase if any
        if self._current_phase and self._current_phase.status == "running":
            self.complete_phase()

        self._task.status = "completed"
        self._task.end_time = time.time()
        self._task.current_phase = TaskPhase.COMPLETE
        if metadata:
            self._task.metadata.update(metadata)

        self.callback.on_task_complete(self._task)
        return self._task

    def fail_task(self, error: str) -> TaskProgress:
        """Mark task as failed

        Args:
            error: Error message

        Returns:
            Final TaskProgress
        """
        if not self._task:
            raise RuntimeError("No task to fail")

        self._task.status = "failed"
        self._task.end_time = time.time()
        self._task.current_phase = TaskPhase.FAILED
        self._task.metadata['error'] = error

        self.callback.on_task_failed(self._task, error)
        return self._task

    def _find_step(self, step_id: str) -> Optional[StepProgress]:
        """Find a step by ID"""
        for phase in self._task.phases:
            for step in phase.steps:
                if step.step_id == step_id:
                    return step
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get task summary

        Returns:
            Summary dictionary
        """
        if not self._task:
            return {}

        return {
            'task_id': self._task.task_id,
            'description': self._task.task_description,
            'status': self._task.status,
            'progress': self._task.overall_progress,
            'duration': (self._task.end_time or time.time()) - self._task.start_time if self._task.start_time else 0,
            'phases': [
                {
                    'phase': p.phase.value,
                    'status': p.status,
                    'steps': p.total_steps,
                    'completed': p.completed_steps
                }
                for p in self._task.phases
            ]
        }

    def export_log(self, filepath: str):
        """Export progress log to JSON file

        Args:
            filepath: Path to output file
        """
        if not self._task:
            return

        log_data = {
            'task_id': self._task.task_id,
            'description': self._task.task_description,
            'status': self._task.status,
            'start_time': datetime.fromtimestamp(self._task.start_time).isoformat() if self._task.start_time else None,
            'end_time': datetime.fromtimestamp(self._task.end_time).isoformat() if self._task.end_time else None,
            'metadata': self._task.metadata,
            'phases': []
        }

        for phase in self._task.phases:
            phase_data = {
                'phase': phase.phase.value,
                'status': phase.status,
                'start_time': datetime.fromtimestamp(phase.start_time).isoformat() if phase.start_time else None,
                'end_time': datetime.fromtimestamp(phase.end_time).isoformat() if phase.end_time else None,
                'steps': []
            }

            for step in phase.steps:
                step_data = {
                    'step_id': step.step_id,
                    'step_type': step.step_type.value,
                    'description': step.description,
                    'status': step.status,
                    'duration': step.duration,
                    'details': step.details,
                    'error': step.error
                }
                phase_data['steps'].append(step_data)

            log_data['phases'].append(phase_data)

        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2)


# Convenience function for quick progress tracking
_global_tracker: Optional[ProgressTracker] = None


def get_tracker() -> ProgressTracker:
    """Get or create global progress tracker"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ProgressTracker()
    return _global_tracker


def track_step(step_type: StepType, description: str):
    """Decorator for tracking function execution as a step

    Usage:
        @track_step(StepType.GENERATE_CODE, "Generating calculator")
        def generate_calculator():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracker = get_tracker()
            step_id = f"{func.__name__}_{int(time.time() * 1000)}"

            tracker.start_step(step_id, step_type, description)
            try:
                result = func(*args, **kwargs)
                tracker.complete_step(step_id)
                return result
            except Exception as e:
                tracker.fail_step(step_id, str(e))
                raise

        return wrapper
    return decorator
