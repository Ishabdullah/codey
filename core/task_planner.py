"""Task Planner - Decomposes complex requests into executable steps

This module handles multi-step instruction planning, breaking down
complex user requests into sequential or parallel subtasks.

Part of Phase 4: Engine Decomposition
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class TaskType(Enum):
    """Type of task step"""
    TOOL_CALL = "tool_call"          # Execute tool directly
    CODE_GEN = "code_generation"     # Generate/edit code
    ALGORITHM = "algorithm"          # Algorithm design
    RESEARCH = "research"            # Information lookup
    SEQUENTIAL = "sequential"        # Multiple steps in order
    PARALLEL = "parallel"            # Multiple steps simultaneously


class StepStatus(Enum):
    """Execution status of a step"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskStep:
    """Represents a single step in a multi-step task"""
    step_id: int
    task_type: TaskType
    description: str
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[int] = field(default_factory=list)  # Step IDs that must complete first
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class TaskPlan:
    """Complete plan for a multi-step task"""
    original_request: str
    steps: List[TaskStep]
    execution_order: List[int]  # Step IDs in execution order
    is_sequential: bool = True   # True if steps must run in order
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskPlanner:
    """Decomposes complex requests into executable task plans"""

    def __init__(self):
        """Initialize task planner"""
        # Keywords that indicate multi-step tasks
        self.multi_step_keywords = [
            "then", "after", "next", "also", "and then", "followed by",
            "first", "second", "third", "finally", "lastly"
        ]

        # Keywords indicating parallel tasks
        self.parallel_keywords = [
            "and", "also", "both", "simultaneously", "at the same time"
        ]

    def needs_planning(self, user_input: str) -> bool:
        """Check if request needs multi-step planning

        Args:
            user_input: User's request

        Returns:
            True if multi-step planning needed
        """
        user_lower = user_input.lower()

        # Check for multi-step indicators
        if any(keyword in user_lower for keyword in self.multi_step_keywords):
            return True

        # Check for parallel indicators
        if any(keyword in user_lower for keyword in self.parallel_keywords):
            # But not simple "create file x and y" (single task with multiple files)
            if user_lower.count(' and ') == 1 and 'file' in user_lower:
                return False
            return True

        # Check for numbered steps
        if any(f"{i}." in user_input or f"{i})" in user_input for i in range(1, 6)):
            return True

        return False

    def create_plan(self, user_input: str) -> TaskPlan:
        """Create execution plan from user request

        Args:
            user_input: User's multi-step request

        Returns:
            TaskPlan with decomposed steps
        """
        # Simple implementation - can be enhanced with model-based planning
        steps = self._decompose_request(user_input)
        is_sequential = self._is_sequential(user_input)
        execution_order = self._determine_execution_order(steps, is_sequential)

        return TaskPlan(
            original_request=user_input,
            steps=steps,
            execution_order=execution_order,
            is_sequential=is_sequential
        )

    def _decompose_request(self, user_input: str) -> List[TaskStep]:
        """Decompose request into individual steps

        Args:
            user_input: User's request

        Returns:
            List of TaskStep objects
        """
        steps = []

        # Try to split by common delimiters
        if any(keyword in user_input.lower() for keyword in self.multi_step_keywords):
            # Split by multi-step keywords
            parts = self._split_by_keywords(user_input, self.multi_step_keywords)
        elif '\n' in user_input and any(c.isdigit() for c in user_input):
            # Split by numbered list
            parts = self._split_numbered_list(user_input)
        else:
            # Single step
            parts = [user_input]

        # Convert parts to TaskSteps
        for i, part in enumerate(parts):
            step = self._classify_step(i + 1, part.strip())
            steps.append(step)

        return steps

    def _split_by_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Split text by multi-step keywords

        Args:
            text: Input text
            keywords: Keywords to split on

        Returns:
            List of text parts
        """
        import re

        # Build regex pattern from keywords
        pattern = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'

        # Split and filter empty parts
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        result = []

        for part in parts:
            part = part.strip()
            if part and part.lower() not in keywords:
                result.append(part)

        return result if result else [text]

    def _split_numbered_list(self, text: str) -> List[str]:
        """Split numbered list into steps

        Args:
            text: Text with numbered list

        Returns:
            List of step descriptions
        """
        import re

        # Match patterns like "1.", "1)", "Step 1:", etc.
        pattern = r'(?:^|\n)\s*(?:\d+[\.\)]\s*|Step\s+\d+:\s*)'

        parts = re.split(pattern, text)
        return [p.strip() for p in parts if p.strip()]

    def _classify_step(self, step_id: int, description: str) -> TaskStep:
        """Classify a step based on its description

        Args:
            step_id: Step ID
            description: Step description

        Returns:
            Classified TaskStep
        """
        desc_lower = description.lower()

        # Determine task type
        if any(word in desc_lower for word in ['git', 'commit', 'push', 'pull', 'clone']):
            task_type = TaskType.TOOL_CALL
            params = {'tool': 'git'}
        elif any(word in desc_lower for word in ['run', 'execute', 'command', 'install']):
            task_type = TaskType.TOOL_CALL
            params = {'tool': 'shell'}
        elif any(word in desc_lower for word in ['create', 'edit', 'modify', 'update', 'delete', 'file']):
            task_type = TaskType.CODE_GEN
            params = {}
        elif any(word in desc_lower for word in ['algorithm', 'sort', 'search', 'optimize', 'complexity']):
            task_type = TaskType.ALGORITHM
            params = {}
        else:
            # Default to code generation
            task_type = TaskType.CODE_GEN
            params = {}

        return TaskStep(
            step_id=step_id,
            task_type=task_type,
            description=description,
            params=params
        )

    def _is_sequential(self, user_input: str) -> bool:
        """Determine if steps must be sequential

        Args:
            user_input: User's request

        Returns:
            True if steps must run in order
        """
        user_lower = user_input.lower()

        # Sequential indicators
        if any(keyword in user_lower for keyword in self.multi_step_keywords):
            return True

        # Parallel indicators
        if any(keyword in user_lower for keyword in self.parallel_keywords):
            # Check context - "and then" is sequential, "and also" can be parallel
            if 'and then' in user_lower or 'then' in user_lower:
                return True
            return False

        # Default to sequential
        return True

    def _determine_execution_order(self, steps: List[TaskStep], is_sequential: bool) -> List[int]:
        """Determine execution order for steps

        Args:
            steps: List of TaskStep objects
            is_sequential: Whether steps must run sequentially

        Returns:
            List of step IDs in execution order
        """
        if is_sequential:
            # Simple sequential order
            return [step.step_id for step in steps]
        else:
            # For parallel, still return order but execution can be parallel
            # Dependencies would need to be resolved in actual execution
            return [step.step_id for step in steps]

    def update_step_status(self, plan: TaskPlan, step_id: int, status: StepStatus, result: Any = None, error: str = None) -> None:
        """Update status of a step in the plan

        Args:
            plan: TaskPlan to update
            step_id: Step ID to update
            status: New status
            result: Optional result data
            error: Optional error message
        """
        for step in plan.steps:
            if step.step_id == step_id:
                step.status = status
                step.result = result
                step.error = error
                break

    def get_next_pending_step(self, plan: TaskPlan) -> Optional[TaskStep]:
        """Get next pending step that's ready to execute

        Args:
            plan: TaskPlan to check

        Returns:
            Next TaskStep to execute, or None if all complete
        """
        for step_id in plan.execution_order:
            step = next((s for s in plan.steps if s.step_id == step_id), None)
            if not step:
                continue

            # Skip if not pending
            if step.status != StepStatus.PENDING:
                continue

            # Check dependencies
            if step.dependencies:
                all_deps_met = True
                for dep_id in step.dependencies:
                    dep_step = next((s for s in plan.steps if s.step_id == dep_id), None)
                    if not dep_step or dep_step.status != StepStatus.COMPLETED:
                        all_deps_met = False
                        break

                if not all_deps_met:
                    continue

            return step

        return None

    def is_plan_complete(self, plan: TaskPlan) -> bool:
        """Check if all steps in plan are complete

        Args:
            plan: TaskPlan to check

        Returns:
            True if all steps complete or failed
        """
        return all(
            step.status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED]
            for step in plan.steps
        )

    def get_plan_summary(self, plan: TaskPlan) -> str:
        """Get summary of plan status

        Args:
            plan: TaskPlan to summarize

        Returns:
            Summary string
        """
        total = len(plan.steps)
        completed = sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in plan.steps if s.status == StepStatus.FAILED)
        pending = sum(1 for s in plan.steps if s.status == StepStatus.PENDING)

        summary = f"Task Plan: {total} steps\n"
        summary += f"  ✓ Completed: {completed}\n"
        if failed > 0:
            summary += f"  ✗ Failed: {failed}\n"
        if pending > 0:
            summary += f"  ⏳ Pending: {pending}\n"

        return summary
