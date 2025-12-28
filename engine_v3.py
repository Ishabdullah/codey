"""Engine V3 - Lightweight Main Loop

Clean, decomposed architecture using:
- Orchestrator (routing & execution)
- ResponseHandler (formatting)
- TaskPlanner (multi-step decomposition)

Phase 6 Enhancements:
- ChunkedTaskExecutor for CPU-friendly generation
- ProgressTracker for real-time reporting
- Smart model caching and preloading
- README auto-generation after multi-step tasks

Part of Phase 4: Engine Decomposition (Enhanced Phase 6)
"""
from typing import Optional
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from models.lifecycle import ModelLifecycleManager
from executor.tool_executor import ToolExecutor
from core.orchestrator import Orchestrator
from core.response_handler import ResponseHandler
from core.task_planner import TaskPlanner, StepStatus, TaskType
from core.progress_tracker import ProgressTracker, TaskPhase, StepType
from core.readme_generator import ReadmeGenerator
from core.code_extractor import CodeExtractor, extract_code, validate_file_content


class EngineV3:
    """Lightweight main loop with decomposed architecture

    Phase 6 Features:
    - Chunked task execution for CPU-friendly generation
    - Progress tracking with real-time reporting
    - Smart model caching and preloading
    - Automatic README generation
    """

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
        from core.tools import FileTools, SQLiteTools

        permission_manager = PermissionManager(config)
        git_manager = GitManager(permission_manager, config.workspace_dir)
        shell_manager = ShellManager(permission_manager, config.workspace_dir, config)
        file_tools = FileTools(config)
        sqlite_tools = SQLiteTools(config)

        self.tool_executor = ToolExecutor(git_manager, shell_manager, file_tools, permission_manager, sqlite_tools)
        self.file_tools = file_tools  # Keep reference for README generation

        # Phase 2+3: Orchestrator (routing & model execution)
        self.orchestrator = Orchestrator(config, self.lifecycle, self.tool_executor)

        # Phase 4: Response formatter
        self.response_handler = ResponseHandler()

        # Phase 4: Task planner for multi-step instructions
        self.planner = TaskPlanner()

        # Phase 6: Progress tracker and README generator
        self.progress_tracker = ProgressTracker()
        self.readme_generator = ReadmeGenerator(config.workspace_dir)

        # Phase 6: Configuration for CPU optimization
        self.cpu_mode = getattr(config, 'cpu_mode', True)
        self.auto_readme = getattr(config, 'auto_readme', True)

        print("✓ Engine V3 initialized (Phase 6: CPU Optimized)")

    def process(self, user_input: str, context: Optional[dict] = None) -> str:
        """Process user request

        Args:
            user_input: User's request
            context: Optional conversation context

        Returns:
            Response string
        """
        # Phase 6: Check for full-stack app generation (special handling)
        if self.planner.is_fullstack_app(user_input):
            return self._execute_fullstack(user_input, context)

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

    # ============================================================
    # Phase 6: Full-stack App Generation with Chunking
    # ============================================================

    def _execute_fullstack(self, user_input: str, context: Optional[dict] = None) -> str:
        """Execute full-stack app generation with CPU-friendly chunking

        This method:
        1. Decomposes the request into manageable chunks
        2. Generates each chunk with appropriate token limits
        3. Tracks progress throughout
        4. Auto-generates README on completion

        Args:
            user_input: User's full-stack app request
            context: Optional context

        Returns:
            Response string with all generated files
        """
        # Start progress tracking
        self.progress_tracker.start_task(f"Full-stack: {user_input[:50]}...")

        # Phase: Planning
        self.progress_tracker.start_phase(TaskPhase.PLANNING)
        self.progress_tracker.start_step("analyze", StepType.ANALYZE, "Analyzing request")

        # Create chunked plan
        plan = self.planner.decompose_fullstack(user_input)

        self.progress_tracker.complete_step("analyze", {
            'chunks': len(plan.steps),
            'estimated_tokens': plan.metadata.get('estimated_tokens', 0)
        })

        # Show plan summary
        estimated_time = self.planner.estimate_generation_time(plan)
        print(f"\n📋 Full-stack generation plan:")
        print(f"   Chunks: {len(plan.steps)}")
        print(f"   Estimated tokens: {plan.metadata.get('estimated_tokens', 0)}")
        print(f"   Estimated time: {estimated_time:.0f}s")
        print(f"   Database: {'Yes' if plan.metadata.get('has_database') else 'No'}")
        print("-" * 50)

        self.progress_tracker.complete_phase()

        # Phase: Generation
        self.progress_tracker.start_phase(TaskPhase.GENERATION)

        responses = []
        generated_files = []

        for step in plan.steps:
            step_id = f"step_{step.step_id}"

            # Determine step type for progress
            if step.task_type == TaskType.TOOL_CALL:
                step_type = StepType.RUN_COMMAND
            elif step.params.get('is_readme'):
                step_type = StepType.README_GENERATE
            else:
                step_type = StepType.GENERATE_CHUNK

            self.progress_tracker.start_step(step_id, step_type, step.description)

            # Update step status
            self.planner.update_step_status(plan, step.step_id, StepStatus.IN_PROGRESS)

            try:
                start_time = time.time()

                if step.task_type == TaskType.TOOL_CALL:
                    # Execute tool directly
                    response = self._execute_tool_step(step)
                else:
                    # Generate code with chunked approach
                    response = self._generate_chunk(step, plan.original_request, context)

                    # Track generated file
                    if step.params.get('file'):
                        generated_files.append(step.params['file'])

                elapsed = time.time() - start_time

                # Mark complete
                self.planner.update_step_status(
                    plan, step.step_id, StepStatus.COMPLETED,
                    result=response
                )

                self.progress_tracker.complete_step(step_id, {'elapsed': elapsed})
                responses.append(f"**Step {step.step_id}:** {step.description}\n{response}")

            except Exception as e:
                error_msg = str(e)
                self.planner.update_step_status(
                    plan, step.step_id, StepStatus.FAILED,
                    error=error_msg
                )
                self.progress_tracker.fail_step(step_id, error_msg)

                responses.append(
                    f"**Step {step.step_id} FAILED:** {step.description}\n"
                    f"Error: {error_msg}"
                )

                # Continue to next step (don't stop on error for full-stack)
                print(f"   ⚠️  Step {step.step_id} failed, continuing...")

        self.progress_tracker.complete_phase()

        # Phase: README Generation (if auto_readme enabled and not already generated)
        if self.auto_readme and 'README.md' not in generated_files:
            self.progress_tracker.start_phase(TaskPhase.FILE_OPERATIONS)
            self.progress_tracker.start_step("readme", StepType.README_GENERATE, "Generating README")

            try:
                readme_content = self.readme_generator.generate(
                    task_description=plan.original_request,
                    generated_files=generated_files,
                    extra_context=plan.metadata
                )

                # Save README
                self.file_tools.write_file('README.md', readme_content, overwrite=True)
                generated_files.append('README.md')

                self.progress_tracker.complete_step("readme")
                responses.append(f"**README:** Generated README.md with documentation")

            except Exception as e:
                self.progress_tracker.fail_step("readme", str(e))

            self.progress_tracker.complete_phase()

        # Complete task
        self.progress_tracker.complete_task({
            'generated_files': generated_files,
            'total_steps': len(plan.steps)
        })

        # Format final response
        summary = self.planner.get_plan_summary(plan)
        final_response = summary + "\n" + "\n\n---\n\n".join(responses)

        # Add file listing
        if generated_files:
            final_response += "\n\n📁 **Generated Files:**\n"
            for f in generated_files:
                final_response += f"  - {f}\n"

        return final_response

    def _execute_tool_step(self, step) -> str:
        """Execute a tool step

        Args:
            step: TaskStep with tool information

        Returns:
            Result string
        """
        tool = step.params.get('tool', 'shell')
        command = step.params.get('command', '')

        if tool == 'shell' and command:
            result = self.tool_executor.execute_safe('shell', {'command': command})
            if result.success:
                return f"✓ Command executed: {command}"
            else:
                return f"✗ Command failed: {result.error}"

        return "✓ Tool step completed"

    def _generate_chunk(self, step, task_description: str, context: Optional[dict]) -> str:
        """Generate code for a single chunk

        Args:
            step: TaskStep with generation information
            task_description: Overall task description
            context: Optional context

        Returns:
            Generated code or result
        """
        filename = step.params.get('file', 'output.py')
        max_tokens = step.params.get('max_tokens', 256)

        # Build chunk-specific prompt
        chunk_prompt = self._build_chunk_prompt(step, task_description)

        # Handle template-based generation (no LLM needed)
        if chunk_prompt == "__TEMPLATE_REQUIREMENTS__":
            code = self._generate_requirements_template(task_description)
            self.file_tools.write_file(filename, code, overwrite=True)
            return f"✓ Created {filename} (template)\n```\n{code}\n```"

        if chunk_prompt == "__TEMPLATE_README__":
            code = self._generate_readme_template(task_description, context)
            self.file_tools.write_file(filename, code, overwrite=True)
            return f"✓ Created {filename} (template)\n```\n{code[:500]}...\n```"

        # Use orchestrator for LLM-based generation with retry on wrong content type
        max_retries = 2
        file_ext = Path(filename).suffix.lower()

        # Prepare context with max_tokens for budget enforcement
        gen_context = context.copy() if context else {}
        gen_context['max_tokens'] = max_tokens

        print(f"   📄 Generating {filename}...")  # Better progress display

        for attempt in range(max_retries + 1):
            response = self.orchestrator.process(chunk_prompt, gen_context)

            # Save file if generation succeeded
            if response and not response.startswith("✗"):
                # Extract code from response if wrapped
                code = self._extract_code_from_response(response, filename)

                if code:
                    # Validate content type
                    is_valid, validation_msg = validate_file_content(code, filename)

                    if not is_valid and attempt < max_retries:
                        # Retry with more explicit prompt
                        print(f"   ⚠️  Wrong content type (attempt {attempt + 1}), retrying...")
                        chunk_prompt = self._get_retry_prompt(filename, file_ext, validation_msg)
                        continue

                    # Ensure directories exist (silently - batch permission already granted)
                    file_path = Path(filename)
                    if file_path.parent and str(file_path.parent) != '.':
                        parent_dir = self.config.workspace_dir / file_path.parent
                        parent_dir.mkdir(parents=True, exist_ok=True)

                    # Write file
                    self.file_tools.write_file(filename, code, overwrite=True)
                    return f"✓ Created {filename}\n```\n{code[:500]}{'...' if len(code) > 500 else ''}\n```"

            break  # Don't retry on empty response

        return response

    def _get_retry_prompt(self, filename: str, file_ext: str, error_msg: str) -> str:
        """Get a clarified retry prompt after content type mismatch

        Args:
            filename: Target filename
            file_ext: File extension
            error_msg: What went wrong

        Returns:
            Clarified prompt
        """
        prompts = {
            '.css': f"""IMPORTANT: Output ONLY CSS code for {filename}.

DO NOT output HTML. DO NOT output JavaScript.
Start with CSS selectors like:

* {{
    box-sizing: border-box;
}}

body {{
    font-family: Arial, sans-serif;
}}

Output ONLY valid CSS. No markdown, no explanation.""",

            '.js': f"""IMPORTANT: Output ONLY JavaScript code for {filename}.

DO NOT output HTML. DO NOT output CSS.
Start with JavaScript like:

document.addEventListener('DOMContentLoaded', function() {{
    // Your code here
}});

Output ONLY valid JavaScript. No markdown, no explanation.""",

            '.py': f"""IMPORTANT: Output ONLY Python code for {filename}.

Start with imports like:

from flask import Flask, request, jsonify

Output ONLY valid Python. No markdown, no explanation.""",
        }

        return prompts.get(file_ext, f"Output ONLY the content for {filename}. No markdown, no explanation.")

    def _generate_requirements_template(self, task_description: str) -> str:
        """Generate requirements.txt from template (no LLM needed)

        Args:
            task_description: Task description for detecting dependencies

        Returns:
            requirements.txt content
        """
        task_lower = task_description.lower()

        # Base Flask requirements
        requirements = ["Flask>=2.0.0"]

        # Add based on task
        if 'database' in task_lower or 'sqlite' in task_lower or 'sql' in task_lower:
            requirements.append("Flask-SQLAlchemy>=3.0.0")

        if 'form' in task_lower or 'wtf' in task_lower:
            requirements.append("Flask-WTF>=1.0.0")

        if 'auth' in task_lower or 'login' in task_lower:
            requirements.append("Flask-Login>=0.6.0")

        if 'api' in task_lower or 'rest' in task_lower:
            requirements.append("flask-restful>=0.3.9")

        if 'cors' in task_lower:
            requirements.append("flask-cors>=3.0.0")

        # Common utilities
        requirements.append("python-dotenv>=0.19.0")

        return '\n'.join(requirements) + '\n'

    def _generate_readme_template(self, task_description: str, context: Optional[dict]) -> str:
        """Generate README.md using ReadmeGenerator (no LLM needed)

        Args:
            task_description: Task description
            context: Context with generated files info

        Returns:
            README.md content
        """
        # Get list of generated files from context or scan workspace
        generated_files = []
        if context and 'generated_files' in context:
            generated_files = context['generated_files']
        else:
            # Scan workspace for common files
            workspace = self.config.workspace_dir
            for pattern in ['*.py', '*.html', '*.css', '*.js', 'templates/*.html', 'static/**/*']:
                generated_files.extend([str(f.relative_to(workspace)) for f in workspace.glob(pattern) if f.is_file()])

        # Use ReadmeGenerator
        readme_gen = ReadmeGenerator(self.config.workspace_dir)
        extra_context = {
            'is_fullstack': True,
            'has_database': 'database' in task_description.lower() or 'sqlite' in task_description.lower()
        }

        return readme_gen.generate(
            task_description=task_description,
            generated_files=generated_files,
            extra_context=extra_context
        )

    def _build_chunk_prompt(self, step, task_description: str) -> str:
        """Build prompt for a specific chunk with explicit output format instructions

        Args:
            step: TaskStep with chunk info
            task_description: Overall task description

        Returns:
            Prompt string with clear format instructions
        """
        filename = step.params.get('file', 'output.py')
        file_type = Path(filename).suffix.lower()

        # Common instruction suffix
        format_instruction = "\n\nIMPORTANT: Output ONLY the file content. No explanations, no markdown, no ```."

        # Type-specific prompts with explicit format requirements
        if file_type == '.py':
            if 'model' in filename.lower():
                base = f"""Write Python code for {filename} with SQLite models.
Task: {task_description}

Requirements:
- SQLAlchemy or sqlite3 models
- Include docstrings
- No markdown formatting"""
            elif 'init_db' in filename.lower():
                base = f"""Write Python code for {filename} to initialize the SQLite database.
- Create tables
- Add any seed data
- No markdown formatting"""
            elif 'app' in filename.lower():
                base = f"""Write Python Flask application code for {filename}.
Task: {task_description}

Requirements:
- Flask app with routes
- CRUD endpoints if needed
- Error handling
- No markdown formatting, just Python code"""
            else:
                base = f"""Write Python code for {filename}.
Task: {step.description}
No markdown formatting, just Python code."""
            return base + format_instruction

        elif file_type == '.html':
            return f"""Write HTML code for {filename}.
Task: {task_description}

Requirements:
- Valid HTML5 structure
- Link to /static/css/style.css
- Link to /static/js/app.js or script.js
- No markdown formatting, just HTML code""" + format_instruction

        elif file_type == '.css':
            return f"""Write CSS code for {filename}.
Task: Create modern, clean styles for the application.

Requirements:
- Body, form, button, input styles
- Responsive design basics
- OUTPUT ONLY CSS - no HTML, no JavaScript, no markdown
- Start directly with CSS selectors like 'body {{' or '* {{'""" + format_instruction

        elif file_type == '.js':
            return f"""Write JavaScript code for {filename}.
Task: {task_description}

Requirements:
- Fetch API for backend communication
- DOM manipulation
- Event handlers
- OUTPUT ONLY JavaScript - no HTML, no CSS, no markdown
- Start directly with 'document.' or 'const ' or 'function '""" + format_instruction

        elif file_type == '.txt' and 'requirements' in filename.lower():
            # Don't use LLM for requirements.txt - use template
            return "__TEMPLATE_REQUIREMENTS__"

        elif file_type == '.md':
            # Don't use LLM for README - use ReadmeGenerator
            return "__TEMPLATE_README__"

        return f"""Write code for {filename}.
Task: {step.description}
No markdown formatting, just the file content.""" + format_instruction

    def _extract_code_from_response(self, response: str, filename: str) -> Optional[str]:
        """Extract code from orchestrator response using robust CodeExtractor

        Args:
            response: Response from orchestrator
            filename: Expected filename for language detection

        Returns:
            Extracted code or None
        """
        # Use the new robust code extractor
        code, status = extract_code(response, filename)

        if code:
            # Validate content type matches filename
            is_valid, validation_msg = validate_file_content(code, filename)

            if not is_valid:
                print(f"   ⚠️  Content type mismatch for {filename}: {validation_msg}")
                # Still return the code, but log warning

            return code

        return None


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

                # Filter out llama.cpp log noise that might get captured
                if (user_input.startswith("llama_") or 
                    user_input.startswith("ggml_") or
                    user_input.startswith("main:") or 
                    "n_ctx" in user_input):
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
