"""Engine V3 - Lightweight Main Loop

Clean, decomposed architecture using:
- Orchestrator (routing & execution)
- ResponseHandler (formatting)
- TaskPlanner (multi-step decomposition)

Part of Phase 4: Engine Decomposition (~170 lines)
"""
from typing import Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from models.lifecycle import ModelLifecycleManager
from executor.tool_executor import ToolExecutor
from core.orchestrator import Orchestrator
from core.response_handler import ResponseHandler
from core.task_planner import TaskPlanner, StepStatus


class EngineV3:
    """Lightweight main loop with decomposed architecture"""

    def __init__(self, config: Config):
        """Initialize engine with configuration

        Args:
            config: Configuration object
        """
        self.config = config

        # Initialize components
        print("Initializing Engine V3...")

        # Phase 1: Model lifecycle
        self.lifecycle = ModelLifecycleManager(config)

        # Phase 2: Tool executor (requires manager instances)
        from core.permission_manager import PermissionManager
        from core.git_manager import GitManager
        from core.shell_manager import ShellManager
        from core.tools import FileTools

        permission_manager = PermissionManager(config)
        git_manager = GitManager(permission_manager, config.workspace_dir)
        shell_manager = ShellManager(permission_manager, config.workspace_dir, config)
        file_tools = FileTools(config)

        self.tool_executor = ToolExecutor(git_manager, shell_manager, file_tools, permission_manager)

        # Phase 2+3: Orchestrator (routing & model execution)
        self.orchestrator = Orchestrator(config, self.lifecycle, self.tool_executor)

        # Phase 4: Response formatter
        self.response_handler = ResponseHandler()

        # Phase 4: Task planner for multi-step instructions
        self.planner = TaskPlanner()

        print("✓ Engine V3 initialized")

    def process(self, user_input: str, context: Optional[dict] = None) -> str:
        """Process user request

        Args:
            user_input: User's request
            context: Optional conversation context

        Returns:
            Response string
        """
        # Check if multi-step planning needed
        if self.planner.needs_planning(user_input):
            return self._execute_multi_step(user_input, context)
        else:
            return self._execute_single_step(user_input, context)

    def _execute_single_step(self, user_input: str, context: Optional[dict] = None) -> str:
        """Execute single-step request

        Args:
            user_input: User's request
            context: Optional context

        Returns:
            Response string
        """
        try:
            # Delegate to orchestrator (handles routing, execution, formatting)
            return self.orchestrator.process(user_input, context)

        except Exception as e:
            return self.response_handler.format_error(
                "Request processing failed",
                str(e)
            )

    def _execute_multi_step(self, user_input: str, context: Optional[dict] = None) -> str:
        """Execute multi-step request

        Args:
            user_input: User's multi-step request
            context: Optional context

        Returns:
            Combined response from all steps
        """
        # Create execution plan
        plan = self.planner.create_plan(user_input)

        print(f"\n📋 Multi-step task detected ({len(plan.steps)} steps)")
        print(f"   Execution: {'Sequential' if plan.is_sequential else 'Parallel'}\n")

        responses = []

        # Execute steps in order
        while not self.planner.is_plan_complete(plan):
            step = self.planner.get_next_pending_step(plan)

            if step is None:
                break  # No more pending steps ready

            # Update status
            self.planner.update_step_status(plan, step.step_id, StepStatus.IN_PROGRESS)

            print(f"[Step {step.step_id}/{len(plan.steps)}] {step.description}")

            try:
                # Execute via orchestrator
                response = self.orchestrator.process(step.description, context)

                # Mark complete
                self.planner.update_step_status(
                    plan, step.step_id, StepStatus.COMPLETED,
                    result=response
                )

                responses.append(f"**Step {step.step_id}:** {step.description}\n{response}")

            except Exception as e:
                # Mark failed
                error_msg = str(e)
                self.planner.update_step_status(
                    plan, step.step_id, StepStatus.FAILED,
                    error=error_msg
                )

                responses.append(
                    f"**Step {step.step_id} FAILED:** {step.description}\n"
                    f"Error: {error_msg}"
                )

                # Decide whether to continue or stop
                if plan.is_sequential:
                    print(f"✗ Step {step.step_id} failed - stopping sequential execution")
                    break

        # Format final response
        summary = self.planner.get_plan_summary(plan)
        final_response = summary + "\n" + "\n\n---\n\n".join(responses)

        return final_response

    def shutdown(self) -> None:
        """Clean shutdown"""
        print("\nShutting down Engine V3...")
        self.orchestrator.shutdown()
        print("✓ Shutdown complete")


def main():
    """Main entry point"""
    import sys

    # Load configuration
    try:
        config = Config()
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return 1

    # Initialize engine
    try:
        engine = EngineV3(config)
    except Exception as e:
        print(f"✗ Failed to initialize engine: {e}")
        return 1

    # Interactive mode
    print("\n" + "=" * 60)
    print("  CODEY Engine V3 - Lightweight Multi-Model Assistant")
    print("=" * 60)
    print("\nType 'exit' or 'quit' to exit")
    print("Type 'help' for usage examples\n")

    try:
        while True:
            try:
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit']:
                    break

                if user_input.lower() == 'help':
                    print("""
Usage Examples:

Single-step commands:
  • git status
  • create a file calculator.py with basic math functions
  • implement binary search algorithm
  • list files in workspace

Multi-step commands:
  • create test.py then run it
  • git status and then commit all changes
  • first create utils.py, then create main.py that imports it
  • 1. create database.py 2. create api.py 3. run tests

The engine will automatically detect and plan multi-step requests!
                    """)
                    continue

                # Process request
                response = engine.process(user_input)
                print(f"\n{response}\n")

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break

            except Exception as e:
                print(f"\n✗ Error: {e}\n")

    finally:
        engine.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
