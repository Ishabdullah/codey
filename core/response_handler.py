"""Response Handler - Formats model outputs for user display

This module extracts all formatting logic from the Orchestrator,
providing a clean interface for converting model results into
human-readable responses.

Part of Phase 4: Engine Decomposition
"""
from typing import Dict, Any
from executor.tool_executor import ToolResult
from models.coder import CodeResult, CodingTask
from models.algorithm_model import AlgorithmResult, AlgorithmTask


class ResponseHandler:
    """Formats responses from tools, models, and router for display"""

    @staticmethod
    def format_tool_result(result: ToolResult) -> str:
        """Format tool execution result for display

        Args:
            result: ToolResult from execution

        Returns:
            Formatted string
        """
        if result.tool == "git":
            return ResponseHandler._format_git_result(result)
        elif result.tool == "shell":
            return ResponseHandler._format_shell_result(result)
        elif result.tool == "file":
            return ResponseHandler._format_file_result(result)
        else:
            return f"✓ {result.tool} completed"

    @staticmethod
    def _format_git_result(result: ToolResult) -> str:
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

    @staticmethod
    def _format_shell_result(result: ToolResult) -> str:
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

    @staticmethod
    def _format_file_result(result: ToolResult) -> str:
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

    @staticmethod
    def format_code_result(result: CodeResult, task: CodingTask) -> str:
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

    @staticmethod
    def format_algorithm_result(result: AlgorithmResult, task: AlgorithmTask) -> str:
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

    @staticmethod
    def format_simple_answer(answer: str) -> str:
        """Format simple answer from router

        Args:
            answer: Answer text

        Returns:
            Formatted string
        """
        return answer.strip()

    @staticmethod
    def format_error(error_msg: str, details: str = None) -> str:
        """Format error message

        Args:
            error_msg: Main error message
            details: Optional error details

        Returns:
            Formatted error string
        """
        response = f"✗ Error: {error_msg}"
        if details:
            response += f"\n\nDetails: {details}"
        return response

    @staticmethod
    def format_unknown_intent(intent: str, confidence: float, suggestions: list = None) -> str:
        """Format unknown intent message

        Args:
            intent: Detected intent
            confidence: Confidence score
            suggestions: Optional list of suggestions

        Returns:
            Formatted help message
        """
        if confidence < 0.5:
            response = (
                f"I'm not sure what you mean (confidence: {confidence:.2f}).\n\n"
                f"Could you rephrase or try:\n"
            )

            if suggestions:
                for suggestion in suggestions:
                    response += f"  • {suggestion}\n"
            else:
                response += (
                    f"  • git status\n"
                    f"  • create a file test.py\n"
                    f"  • list files\n"
                    f"  • implement quicksort"
                )

            return response

        return f"Intent: {intent}, but no handler implemented yet."
