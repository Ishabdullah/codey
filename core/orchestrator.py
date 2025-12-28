"""Orchestrator - Central coordination between router, models, and tools"""
import logging
from typing import Optional, Dict, Any, List

from models.lifecycle import ModelLifecycleManager, ModelRole
from router.intent_router import IntentRouter, IntentResult
from executor.tool_executor import ToolExecutor, ToolResult
from models.coder import PrimaryCoder, CodingTask, CodeResult
from models.algorithm_model import AlgorithmSpecialist, AlgorithmTask, AlgorithmResult
from utils.thinking_display import ThinkingStep, thinking, step, substep, complete, error as display_error
from utils.performance import (
    start_request, end_request, time_operation, set_tokens, estimate_tokens
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """Central coordination between router, models, and tools

    This class implements the core routing logic:
    1. Router classifies user intent
    2. If tool_call → Execute directly via ToolExecutor
    3. If simple_answer → Router handles (or delegate to coder if complex)
    4. If coding_task → Escalate to Coder model
    5. If algorithm_task → Escalate to Algorithm specialist
    """

    def __init__(self, config, lifecycle_manager: ModelLifecycleManager, tool_executor: ToolExecutor):
        """Initialize orchestrator

        Args:
            config: Configuration object
            lifecycle_manager: ModelLifecycleManager instance
            tool_executor: ToolExecutor instance
        """
        self.config = config
        self.lifecycle = lifecycle_manager
        self.tools = tool_executor

        # Router will be loaded on first use
        self.router: Optional[IntentRouter] = None

    def process(self, user_input: str, context: Optional[Dict] = None) -> str:
        """Main entry point - process user request

        Args:
            user_input: User's request
            context: Optional context from previous interactions

        Returns:
            Response string
        """
        # Start performance tracking
        metrics = start_request()

        try:
            # Ensure router is loaded
            if self.router is None:
                with thinking(ThinkingStep.LOADING_MODEL, "Intent Router"):
                    with time_operation("router_load"):
                        self._load_router()

            # Classify intent
            with thinking(ThinkingStep.CLASSIFYING):
                try:
                    with time_operation("router_classify"):
                        intent_result = self.router.classify(user_input, context)
                    substep(f"Intent: {intent_result.intent}")
                    if intent_result.used_fallback:
                        substep("Using regex fallback")
                    substep(f"Confidence: {intent_result.confidence:.0%}")
                except Exception as e:
                    display_error(f"Classification failed: {e}")
                    return f"Error classifying intent: {e}"

            # Estimate input tokens
            set_tokens(input_tokens=estimate_tokens(user_input))

            # Route based on intent
            step(ThinkingStep.ROUTING, intent_result.intent)

            if intent_result.is_tool_call():
                return self._handle_tool_call(intent_result)

            elif intent_result.is_simple_answer():
                return self._handle_simple_answer(intent_result, user_input)

            elif intent_result.is_coding_task():
                return self._handle_coding_task(intent_result, user_input)

            elif intent_result.is_algorithm_task():
                return self._handle_algorithm_task(intent_result, user_input)

            else:
                return self._handle_unknown(intent_result, user_input)

        finally:
            # End performance tracking
            request_metrics = end_request()
            if request_metrics:
                substep(f"Performance: {request_metrics.summary()}")

    def _load_router(self) -> None:
        """Load the router model (always-resident)"""
        logger.info("Loading intent router...")
        router_model = self.lifecycle.ensure_loaded(ModelRole.ROUTER)

        # Convert to IntentRouter instance
        from router.intent_router import IntentRouter
        self.router = IntentRouter(router_model.model_path, router_model.config)
        self.router._model = router_model._model  # Reuse loaded model
        self.router._loaded = router_model._loaded

    def _handle_tool_call(self, intent: IntentResult) -> str:
        """Handle direct tool calls

        Args:
            intent: Intent classification result

        Returns:
            Formatted tool execution result
        """
        tool = intent.tool
        params = intent.params

        if not tool:
            return "Error: Tool call without tool specified"

        # Execute tool
        with thinking(ThinkingStep.EXECUTING_TOOL, f"{tool} {params.get('action', '')}".strip()):
            result = self.tools.execute(tool, params)

        if not result.success:
            display_error(f"{tool} failed: {result.error}")
            return f"✗ {tool} failed: {result.error}"

        complete()
        # Format output based on tool
        return self._format_tool_result(result)

    def _format_tool_result(self, result: ToolResult) -> str:
        """Format tool execution result for display

        Args:
            result: ToolResult from execution

        Returns:
            Formatted string
        """
        if result.tool == "git":
            return self._format_git_result(result)
        elif result.tool == "shell":
            return self._format_shell_result(result)
        elif result.tool == "file":
            return self._format_file_result(result)
        else:
            return f"✓ {result.tool} completed"

    def _format_git_result(self, result: ToolResult) -> str:
        """Format git operation result"""
        if not result.output:
            return f"✓ git {result.action} completed"

        output = result.output

        if result.action == "status":
            if output.get('clean'):
                return "✓ Working directory is clean"

            response = "Git status:\n"
            if output.get('staged'):
                response += f"\nStaged ({len(output['staged'])}):\n"
                for f in output['staged'][:10]:
                    response += f"  + {f}\n"
            if output.get('modified'):
                response += f"\nModified ({len(output['modified'])}):\n"
                for f in output['modified'][:10]:
                    response += f"  M {f}\n"
            if output.get('untracked'):
                response += f"\nUntracked ({len(output['untracked'])}):\n"
                for f in output['untracked'][:10]:
                    response += f"  ? {f}\n"
            return response

        elif result.action == "commit":
            files = output.get('files', [])
            return f"✓ Committed {len(files)} file(s)"

        elif result.action == "push":
            remote = output.get('remote', 'origin')
            branch = output.get('branch', 'main')
            return f"✓ Pushed to {remote}/{branch}"

        elif result.action == "pull":
            return f"✓ Pulled from remote\n{output.get('output', '')}"

        elif result.action == "clone":
            return f"✓ Cloned repository to {output.get('path', 'unknown')}"

        else:
            return f"✓ git {result.action} completed"

    def _format_shell_result(self, result: ToolResult) -> str:
        """Format shell command result"""
        if not result.output:
            return f"✓ {result.action} completed"

        output = result.output

        if result.action == "install":
            return f"✓ Installation completed"

        elif result.action == "mkdir":
            return output.get('message', '✓ Directory created')

        elif result.action == "run":
            stdout = output.get('stdout', '')
            stderr = output.get('stderr', '')
            response = f"✓ Executed\n"
            if stdout:
                response += f"\nOutput:\n{stdout}"
            if stderr:
                response += f"\nErrors:\n{stderr}"
            return response

        elif result.action == "execute":
            stdout = output.get('stdout', '')
            response = f"✓ Command executed"
            if stdout:
                response += f"\n\n{stdout}"
            return response

        else:
            return f"✓ {result.action} completed"

    def _format_file_result(self, result: ToolResult) -> str:
        """Format file operation result"""
        if result.action == "read":
            if isinstance(result.output, str):
                return f"File contents:\n\n{result.output}"
            else:
                return "✓ File read"

        elif result.action == "list":
            files = result.output
            if files:
                return "Files in workspace:\n" + "\n".join(f"  - {f}" for f in files)
            else:
                return "No files in workspace"

        elif result.action == "delete":
            return f"✓ File deleted"

        elif result.action == "check":
            exists = result.output.get('exists', False)
            return f"File {'exists' if exists else 'does not exist'}"

        else:
            return f"✓ File operation completed"

    def _handle_simple_answer(self, intent: IntentResult, user_input: str) -> str:
        """Handle simple questions

        For Phase 2, router attempts to answer. If confidence is low,
        can escalate to coder model (future enhancement).

        Args:
            intent: Intent classification result
            user_input: Original user input

        Returns:
            Answer string
        """
        # For now, use router model to generate answer
        if self.router and self.router.loaded:
            try:
                prompt = f"""Answer this question concisely (1-2 sentences):

Question: {user_input}

Answer:"""
                answer = self.router.generate(prompt, max_tokens=150, temperature=0.5)
                return answer
            except Exception as e:
                return f"Error generating answer: {e}"

        return "I can answer simple questions, but the router model is not available."

    def _handle_coding_task(self, intent: IntentResult, user_input: str) -> str:
        """Handle coding tasks - escalate to coder model

        Args:
            intent: Intent classification result
            user_input: Original user input

        Returns:
            Coding result
        """
        # Load primary coder model
        with thinking(ThinkingStep.LOADING_MODEL, "Qwen2.5-Coder 7B"):
            try:
                with time_operation("coder_model_load"):
                    coder_model = self.lifecycle.ensure_loaded(ModelRole.CODER)
            except Exception as e:
                display_error(f"Failed to load coder model: {e}")
                return f"✗ Failed to load coder model: {e}"

        # Create PrimaryCoder instance
        coder = PrimaryCoder(coder_model.model_path, coder_model.config)
        coder._model = coder_model._model
        coder._loaded = coder_model._loaded

        # Build coding task from intent
        with thinking(ThinkingStep.ANALYZING):
            task = self._build_coding_task_from_intent(intent, user_input)
            substep(f"Task type: {task.task_type}")
            if task.target_files:
                substep(f"Target: {', '.join(task.target_files)}")

        # Execute task
        with thinking(ThinkingStep.GENERATING_CODE):
            try:
                with time_operation("code_generation"):
                    result = coder.generate_code(task)

                # Track output tokens
                if result.code:
                    total_code = "".join(result.code.values())
                    set_tokens(output_tokens=estimate_tokens(total_code))

            except Exception as e:
                display_error(f"Code generation failed: {e}")
                return f"✗ Code generation failed: {e}"

        # Check for escalation to algorithm specialist
        if result.needs_algorithm_specialist:
            step(ThinkingStep.ROUTING, "algorithm specialist")
            return self._escalate_to_algorithm(task, user_input, result)

        # Save generated files to disk
        if result.success and result.code:
            with thinking(ThinkingStep.EXECUTING_TOOL, "Saving files"):
                for filename, content in result.code.items():
                    # Determine overwrite based on task type
                    overwrite = task.task_type in ['edit', 'fix', 'refactor']
                    
                    save_result = self.tools.execute("file", {
                        "action": "write",
                        "filename": filename,
                        "content": content,
                        "overwrite": overwrite
                    })
                    
                    if not save_result.success:
                        substep(f"Failed to save {filename}: {save_result.error}")
                        # Append error to result warnings
                        result.warnings.append(f"Failed to save {filename}: {save_result.error}")
                    else:
                        substep(f"Saved {filename}")

        complete("Code generated successfully")
        # Format and return result
        return self._format_code_result(result, task)

    def _build_coding_task_from_intent(self, intent: IntentResult, user_input: str) -> CodingTask:
        """Build CodingTask from intent classification

        Args:
            intent: Intent classification result
            user_input: Original user input

        Returns:
            CodingTask object
        """
        params = intent.params

        # Determine task type
        task_type = params.get('task_type', 'create')
        if 'create' in user_input.lower() or 'write' in user_input.lower() or 'generate' in user_input.lower():
            task_type = 'create'
        elif 'edit' in user_input.lower() or 'modify' in user_input.lower() or 'update' in user_input.lower():
            task_type = 'edit'
        elif 'refactor' in user_input.lower() or 'reorganize' in user_input.lower():
            task_type = 'refactor'
        elif 'fix' in user_input.lower() or 'debug' in user_input.lower() or 'bug' in user_input.lower():
            task_type = 'fix'
        elif 'explain' in user_input.lower():
            task_type = 'explain'

        # Extract target files
        target_files = params.get('files', [])
        if not target_files:
            # Try to infer filename from user input
            filename = self._extract_filename_from_input(user_input)
            if filename:
                target_files = [filename]
            else:
                # Generate smart filename based on output format detection
                filename, language = self._determine_output_format(user_input)
                target_files = [filename]

        # Get existing code if editing
        existing_code = None
        if task_type in ['edit', 'refactor', 'fix']:
            existing_code = self._get_existing_code(target_files)

        # Infer language from first target file
        language = self._infer_language(target_files[0]) if target_files else 'python'

        return CodingTask(
            task_type=task_type,
            target_files=target_files,
            instructions=user_input,
            existing_code=existing_code,
            language=language,
            constraints=[]
        )

    def _determine_output_format(self, user_input: str) -> tuple:
        """Determine output file format based on user input

        Default is Python. Only produce HTML/JS/etc if explicitly requested.

        Args:
            user_input: User's request

        Returns:
            Tuple of (filename, language)
        """
        import re
        user_lower = user_input.lower()

        # Extract a descriptive name from the request
        base_name = self._extract_base_name(user_input)

        # Check for explicit web/frontend keywords - must be explicit
        html_keywords = [
            'html', 'webpage', 'web page', 'website', 'web site',
            'html page', 'html file', 'html document'
        ]
        js_keywords = [
            'javascript', 'js file', 'node.js', 'nodejs',
            'react', 'vue', 'angular', 'frontend'
        ]
        ts_keywords = ['typescript', 'ts file', '.ts']
        css_keywords = ['css file', 'stylesheet', 'css stylesheet']
        shell_keywords = ['bash', 'shell script', 'sh file', '.sh']
        go_keywords = ['golang', 'go file', '.go', 'in go']
        rust_keywords = ['rust', '.rs', 'in rust']
        java_keywords = ['java', '.java', 'in java']
        cpp_keywords = ['c++', 'cpp', '.cpp', 'in c++']

        # Check explicit language requests (in order of specificity)
        if any(kw in user_lower for kw in html_keywords):
            return (f'{base_name}.html', 'html')

        if any(kw in user_lower for kw in ts_keywords):
            return (f'{base_name}.ts', 'typescript')

        if any(kw in user_lower for kw in js_keywords):
            return (f'{base_name}.js', 'javascript')

        if any(kw in user_lower for kw in css_keywords):
            return (f'{base_name}.css', 'css')

        if any(kw in user_lower for kw in shell_keywords):
            return (f'{base_name}.sh', 'bash')

        if any(kw in user_lower for kw in go_keywords):
            return (f'{base_name}.go', 'go')

        if any(kw in user_lower for kw in rust_keywords):
            return (f'{base_name}.rs', 'rust')

        if any(kw in user_lower for kw in java_keywords):
            return (f'{base_name}.java', 'java')

        if any(kw in user_lower for kw in cpp_keywords):
            return (f'{base_name}.cpp', 'cpp')

        # Default to Python - the safe default
        return (f'{base_name}.py', 'python')

    def _extract_base_name(self, user_input: str) -> str:
        """Extract a descriptive base filename from user input

        Args:
            user_input: User's request

        Returns:
            Base filename (without extension)
        """
        import re
        user_lower = user_input.lower()

        # Known key nouns to prioritize - check these first
        key_nouns = [
            'calculator', 'game', 'server', 'client', 'api', 'database', 'db',
            'parser', 'compiler', 'lexer', 'interpreter', 'scheduler',
            'handler', 'manager', 'controller', 'service', 'util', 'utils',
            'helper', 'test', 'config', 'settings', 'main', 'index',
            'todo', 'chat', 'login', 'auth', 'user', 'admin', 'dashboard',
            'timer', 'counter', 'converter', 'validator', 'generator'
        ]
        for noun in key_nouns:
            if noun in user_lower:
                return noun

        # Try to find descriptive noun for the file
        # Pattern: "create a/an [adjective]? X" or "write a/an X"
        # Skip articles and common adjectives
        skip_words = {
            'a', 'an', 'the', 'some', 'simple', 'basic', 'small', 'new',
            'file', 'code', 'script', 'program', 'app', 'application',
            'function', 'class', 'module', 'that', 'which', 'for', 'to'
        }

        # Find words after action verbs
        pattern = r'(?:create|write|make|build|generate|implement)\s+(.+?)(?:\s+(?:in|for|that|which|with)|$)'
        match = re.search(pattern, user_lower)
        if match:
            words = match.group(1).split()
            for word in words:
                word = re.sub(r'[^a-z]', '', word)  # Clean word
                if word and word not in skip_words and len(word) > 2:
                    return word

        # Default to generic name
        return 'generated_code'

    def _extract_filename_from_input(self, user_input: str) -> Optional[str]:
        """Extract filename from user input

        Args:
            user_input: User's request

        Returns:
            Filename if found, None otherwise
        """
        import re

        # Look for filename with extension
        match = re.search(r'([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)', user_input)
        if match:
            return match.group(1)

        # Look for quoted filename
        match = re.search(r'["\']([a-zA-Z0-9_.-]+)["\']', user_input)
        if match:
            return match.group(1)

        return None

    def _get_existing_code(self, files: List[str]) -> Optional[Dict[str, str]]:
        """Get existing code for files

        Args:
            files: List of filenames

        Returns:
            Dict mapping filename to content, or None
        """
        existing = {}

        for filename in files:
            # Try to read file using ToolExecutor
            result = self.tools.execute("file", {"action": "read", "filename": filename})
            if result.success and result.output:
                existing[filename] = result.output

        return existing if existing else None

    def _infer_language(self, filename: str) -> str:
        """Infer programming language from filename

        Args:
            filename: Name of file

        Returns:
            Language name
        """
        from pathlib import Path

        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
        }

        suffix = Path(filename).suffix.lower()
        return ext_map.get(suffix, 'python')

    def _format_code_result(self, result: CodeResult, task: CodingTask) -> str:
        """Format code generation result for display

        Args:
            result: CodeResult from coder
            task: Original CodingTask

        Returns:
            Formatted string
        """
        if not result.success:
            return f"✗ Code generation failed: {result.error}"

        response = f"✓ {task.task_type.capitalize()} completed\n\n"

        # Show explanation if present
        if result.explanation:
            response += f"{result.explanation}\n\n"

        # Show generated code
        if result.code:
            for filename, code in result.code.items():
                response += f"File: {filename}\n```{task.language}\n{code}\n```\n\n"

        # Show warnings if any
        if result.warnings:
            response += "Warnings:\n"
            for warning in result.warnings:
                response += f"  ⚠️  {warning}\n"

        return response.strip()

    def _escalate_to_algorithm(self, coding_task: CodingTask, user_input: str, partial_result: CodeResult) -> str:
        """Escalate coding task to algorithm specialist

        Args:
            coding_task: Original coding task
            user_input: User's request
            partial_result: Partial result from coder

        Returns:
            Algorithm specialist result
        """
        # Unload coder to free memory
        logger.info("Unloading coder model to free memory...")
        self.lifecycle.unload_model(ModelRole.CODER)

        # Load algorithm specialist
        logger.info("Loading DeepSeek-Coder 6.7B (Algorithm Specialist)...")
        try:
            algo_model = self.lifecycle.ensure_loaded(ModelRole.ALGORITHM)
        except Exception as e:
            return f"✗ Failed to load algorithm specialist: {e}"

        # Create AlgorithmSpecialist instance
        specialist = AlgorithmSpecialist(algo_model.model_path, algo_model.config)
        specialist._model = algo_model._model
        specialist._loaded = algo_model._loaded

        # Build algorithm task
        task = AlgorithmTask(
            problem_description=user_input,
            language=coding_task.language,
            constraints=coding_task.constraints,
            context_code=partial_result.explanation if partial_result.explanation else None
        )

        # Execute
        try:
            result = specialist.solve(task)
        except Exception as e:
            return f"✗ Algorithm generation failed: {e}"

        # Format result
        return self._format_algorithm_result(result, task)

    def _handle_algorithm_task(self, intent: IntentResult, user_input: str) -> str:
        """Handle algorithm tasks - escalate to algorithm specialist

        Args:
            intent: Intent classification result
            user_input: Original user input

        Returns:
            Algorithm result
        """
        logger.info("Loading DeepSeek-Coder 6.7B (Algorithm Specialist)...")

        # Load algorithm specialist
        try:
            algo_model = self.lifecycle.ensure_loaded(ModelRole.ALGORITHM)
        except Exception as e:
            return f"✗ Failed to load algorithm specialist: {e}"

        # Create AlgorithmSpecialist instance
        specialist = AlgorithmSpecialist(algo_model.model_path, algo_model.config)
        specialist._model = algo_model._model
        specialist._loaded = algo_model._loaded

        # Build algorithm task from intent
        task = self._build_algorithm_task_from_intent(intent, user_input)

        # Execute
        try:
            result = specialist.solve(task)
        except Exception as e:
            return f"✗ Algorithm generation failed: {e}"

        # Format and return result
        return self._format_algorithm_result(result, task)

    def _build_algorithm_task_from_intent(self, intent: IntentResult, user_input: str) -> AlgorithmTask:
        """Build AlgorithmTask from intent classification

        Args:
            intent: Intent classification result
            user_input: Original user input

        Returns:
            AlgorithmTask object
        """
        params = intent.params

        # Extract constraints from params or user input
        constraints = params.get('constraints', [])

        # Extract expected complexity if mentioned
        expected_complexity = None
        import re
        complexity_match = re.search(r'O\(([^)]+)\)', user_input)
        if complexity_match:
            expected_complexity = f"O({complexity_match.group(1)})"

        # Determine optimization goal
        optimize_for = "time"  # Default
        if 'space' in user_input.lower() and 'complex' in user_input.lower():
            optimize_for = "space"
        elif 'memory' in user_input.lower():
            optimize_for = "space"
        elif 'both' in user_input.lower():
            optimize_for = "both"

        # Infer language
        language = 'python'  # Default
        if 'java' in user_input.lower():
            language = 'java'
        elif 'c++' in user_input.lower() or 'cpp' in user_input.lower():
            language = 'cpp'
        elif 'javascript' in user_input.lower() or 'js' in user_input.lower():
            language = 'javascript'

        return AlgorithmTask(
            problem_description=user_input,
            constraints=constraints,
            expected_complexity=expected_complexity,
            language=language,
            optimize_for=optimize_for
        )

    def _format_algorithm_result(self, result: AlgorithmResult, task: AlgorithmTask) -> str:
        """Format algorithm result for display

        Args:
            result: AlgorithmResult from specialist
            task: Original AlgorithmTask

        Returns:
            Formatted string
        """
        if not result.success:
            return f"✗ Algorithm generation failed: {result.error}"

        response = "✓ Algorithm solution generated\n\n"

        # Show complexity analysis
        if result.complexity_analysis:
            response += "Complexity Analysis:\n"
            if 'time' in result.complexity_analysis:
                response += f"  Time: {result.complexity_analysis['time']}\n"
            if 'space' in result.complexity_analysis:
                response += f"  Space: {result.complexity_analysis['space']}\n"
            response += "\n"

        # Show explanation
        if result.explanation:
            response += f"{result.explanation}\n\n"

        # Show code
        if result.code:
            response += f"Implementation:\n```{task.language}\n{result.code}\n```\n\n"

        # Show trade-offs if present
        if result.trade_offs:
            response += f"Trade-offs: {result.trade_offs}\n\n"

        # Show warnings
        if result.warnings:
            response += "Warnings:\n"
            for warning in result.warnings:
                response += f"  ⚠️  {warning}\n"

        return response.strip()

    def _handle_unknown(self, intent: IntentResult, user_input: str) -> str:
        """Handle unknown or low-confidence intents

        Args:
            intent: Intent classification result
            user_input: Original user input

        Returns:
            Help message
        """
        if intent.confidence < 0.5:
            return (
                f"I'm not sure what you mean (confidence: {intent.confidence:.2f}).\n\n"
                f"Could you rephrase or try:\n"
                f"  • git status\n"
                f"  • create a file test.py\n"
                f"  • list files\n"
                f"  • implement quicksort"
            )

        return f"Intent: {intent.intent}, but no handler implemented yet."

    def shutdown(self) -> None:
        """Clean shutdown - unload models"""
        if self.lifecycle:
            self.lifecycle.unload_all()
