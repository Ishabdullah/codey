"""Orchestrator - Central coordination between router, models, and tools"""
from typing import Optional, Dict, Any

from models.lifecycle import ModelLifecycleManager, ModelRole
from router.intent_router import IntentRouter, IntentResult
from executor.tool_executor import ToolExecutor, ToolResult


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
        # Ensure router is loaded
        if self.router is None:
            self._load_router()

        # Classify intent
        try:
            intent_result = self.router.classify(user_input, context)
        except Exception as e:
            return f"Error classifying intent: {e}"

        # Route based on intent
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

    def _load_router(self) -> None:
        """Load the router model (always-resident)"""
        print("Loading intent router...")
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
        result = self.tools.execute(tool, params)

        if not result.success:
            return f"✗ {tool} failed: {result.error}"

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
            Coding result or placeholder
        """
        # Phase 2: Placeholder for Phase 3 implementation
        return (
            f"🔄 Coding task detected (confidence: {intent.confidence:.2f})\n\n"
            f"This will be handled by Qwen2.5-Coder 7B in Phase 3.\n"
            f"For now, you can use the legacy engine via 'core/engine_v2.py'.\n\n"
            f"Task: {user_input}"
        )

    def _handle_algorithm_task(self, intent: IntentResult, user_input: str) -> str:
        """Handle algorithm tasks - escalate to algorithm specialist

        Args:
            intent: Intent classification result
            user_input: Original user input

        Returns:
            Algorithm result or placeholder
        """
        # Phase 2: Placeholder for Phase 3 implementation
        return (
            f"🔄 Algorithm task detected (confidence: {intent.confidence:.2f})\n\n"
            f"This will be handled by DeepSeek-Coder 6.7B in Phase 3.\n\n"
            f"Task: {user_input}"
        )

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
