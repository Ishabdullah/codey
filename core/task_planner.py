"""Task Planner - Decomposes complex requests into executable steps

This module handles multi-step instruction planning, breaking down
complex user requests into sequential or parallel subtasks.

Enhanced in Phase 6 for:
- Full-stack application decomposition
- CPU-aware chunking with token budgets
- README auto-generation after completion

Part of Phase 4: Engine Decomposition (Enhanced Phase 6)
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import re


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
        import re

        steps = []

        # Try to split by common delimiters
        if any(keyword in user_input.lower() for keyword in self.multi_step_keywords):
            # Split by multi-step keywords
            parts = self._split_by_keywords(user_input, self.multi_step_keywords)
        elif re.search(r'\d+[\.\)]', user_input):
            # Split by numbered list (works for both inline and multi-line)
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
        # Updated to work with inline numbered lists (e.g., "1. foo 2. bar 3. baz")
        pattern = r'(?:^|\n|\s)\s*(\d+[\.\)]\s+|Step\s+\d+:\s*)'

        # Split and filter
        parts = re.split(pattern, text)

        # Filter out the captured number groups and empty strings
        result = []
        for part in parts:
            part = part.strip()
            # Skip if it's just a number marker (e.g., "1. ", "2) ")
            if part and not re.match(r'^\d+[\.\)]\s*$', part):
                result.append(part)

        return result if result else [text]

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

    # ============================================================
    # Phase 6 Enhancements: Full-stack App Decomposition
    # ============================================================

    def is_fullstack_app(self, user_input: str) -> bool:
        """Check if request is for a full-stack application

        Args:
            user_input: User's request

        Returns:
            True if full-stack app generation is needed
        """
        user_lower = user_input.lower()

        # Explicit full-stack keywords
        fullstack_keywords = [
            'full-stack', 'fullstack', 'full stack',
            'frontend and backend', 'backend and frontend',
            'web app', 'web application', 'complete app',
            'rest api with ui', 'api with frontend'
        ]

        if any(kw in user_lower for kw in fullstack_keywords):
            return True

        # Check for combination of backend + frontend indicators
        has_backend = any(kw in user_lower for kw in [
            'flask', 'fastapi', 'django', 'backend', 'api', 'server',
            'rest', 'endpoint', 'route'
        ])

        has_frontend = any(kw in user_lower for kw in [
            'html', 'frontend', 'ui', 'interface', 'webpage', 'page',
            'form', 'button', 'react', 'vue'
        ])

        return has_backend and has_frontend

    def decompose_fullstack(self, user_input: str) -> TaskPlan:
        """Decompose full-stack app request into manageable chunks

        This creates a plan with appropriately sized chunks to avoid
        timeout issues on CPU-only hardware.

        Args:
            user_input: User's request

        Returns:
            TaskPlan with chunked steps
        """
        steps = []
        user_lower = user_input.lower()

        # Detect features
        has_database = any(kw in user_lower for kw in [
            'database', 'sqlite', 'db', 'sql', 'crud', 'storage', 'persist'
        ])

        has_auth = any(kw in user_lower for kw in [
            'auth', 'login', 'user', 'password', 'session'
        ])

        # Step 1: Database schema (if needed)
        if has_database:
            steps.append(TaskStep(
                step_id=len(steps) + 1,
                task_type=TaskType.CODE_GEN,
                description="Create database models and schema (models.py)",
                params={'file': 'models.py', 'max_tokens': 256}
            ))

        # Step 2: Backend app initialization
        steps.append(TaskStep(
            step_id=len(steps) + 1,
            task_type=TaskType.CODE_GEN,
            description=f"Create backend app with routes (app.py) - {user_input[:50]}",
            params={'file': 'app.py', 'max_tokens': 384}
        ))

        # Step 3: Database init (if needed)
        if has_database:
            steps.append(TaskStep(
                step_id=len(steps) + 1,
                task_type=TaskType.CODE_GEN,
                description="Create database initialization script (init_db.py)",
                params={'file': 'init_db.py', 'max_tokens': 128},
                dependencies=[1]  # Depends on models
            ))

        # Step 4: Create directories for frontend
        steps.append(TaskStep(
            step_id=len(steps) + 1,
            task_type=TaskType.TOOL_CALL,
            description="Create templates and static directories",
            params={'tool': 'shell', 'command': 'mkdir -p templates static/css static/js'}
        ))

        # Step 5: HTML template
        steps.append(TaskStep(
            step_id=len(steps) + 1,
            task_type=TaskType.CODE_GEN,
            description="Create HTML template (templates/index.html)",
            params={'file': 'templates/index.html', 'max_tokens': 384}
        ))

        # Step 6: CSS styles
        steps.append(TaskStep(
            step_id=len(steps) + 1,
            task_type=TaskType.CODE_GEN,
            description="Create CSS styles (static/css/style.css)",
            params={'file': 'static/css/style.css', 'max_tokens': 256}
        ))

        # Step 7: JavaScript client
        steps.append(TaskStep(
            step_id=len(steps) + 1,
            task_type=TaskType.CODE_GEN,
            description="Create JavaScript client (static/js/app.js)",
            params={'file': 'static/js/app.js', 'max_tokens': 384}
        ))

        # Step 8: Requirements file
        steps.append(TaskStep(
            step_id=len(steps) + 1,
            task_type=TaskType.CODE_GEN,
            description="Create requirements.txt",
            params={'file': 'requirements.txt', 'max_tokens': 64}
        ))

        # Step 9: README
        steps.append(TaskStep(
            step_id=len(steps) + 1,
            task_type=TaskType.CODE_GEN,
            description="Generate README.md with setup instructions",
            params={'file': 'README.md', 'max_tokens': 256, 'is_readme': True}
        ))

        # Calculate execution order (respecting dependencies)
        execution_order = [step.step_id for step in steps]

        return TaskPlan(
            original_request=user_input,
            steps=steps,
            execution_order=execution_order,
            is_sequential=True,
            metadata={
                'is_fullstack': True,
                'has_database': has_database,
                'has_auth': has_auth,
                'total_chunks': len(steps),
                'estimated_tokens': sum(s.params.get('max_tokens', 256) for s in steps)
            }
        )

    def estimate_generation_time(self, plan: TaskPlan, tokens_per_second: float = 5.0) -> float:
        """Estimate total generation time for a plan

        Args:
            plan: TaskPlan to estimate
            tokens_per_second: Expected generation speed on CPU

        Returns:
            Estimated time in seconds
        """
        total_tokens = 0

        for step in plan.steps:
            if step.task_type == TaskType.CODE_GEN:
                total_tokens += step.params.get('max_tokens', 256)

        return total_tokens / tokens_per_second

    def get_generated_files(self, plan: TaskPlan) -> List[str]:
        """Get list of files that will be generated

        Args:
            plan: TaskPlan to inspect

        Returns:
            List of filenames
        """
        files = []
        for step in plan.steps:
            if step.task_type == TaskType.CODE_GEN:
                filename = step.params.get('file')
                if filename:
                    files.append(filename)
        return files

    def create_readme_step(self, plan: TaskPlan) -> TaskStep:
        """Create a README generation step based on completed plan

        Args:
            plan: Completed TaskPlan

        Returns:
            TaskStep for README generation
        """
        generated_files = self.get_generated_files(plan)
        completed = [s for s in plan.steps if s.status == StepStatus.COMPLETED]

        return TaskStep(
            step_id=len(plan.steps) + 1,
            task_type=TaskType.CODE_GEN,
            description=f"Generate README.md for: {plan.original_request[:30]}...",
            params={
                'file': 'README.md',
                'max_tokens': 256,
                'is_readme': True,
                'generated_files': generated_files,
                'task_summary': plan.original_request
            }
        )
