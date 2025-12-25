"""Tool Executor Package

This package contains the tool execution system that handles direct operations
without needing model inference (git, shell, file operations).
"""

from executor.tool_executor import ToolExecutor, ToolResult

__all__ = ['ToolExecutor', 'ToolResult']
