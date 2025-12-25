"""Tool Executor - Execute tools without model inference"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class ToolResult:
    """Result of tool execution

    Attributes:
        success: Whether the operation succeeded
        output: Output data from the tool
        error: Error message if operation failed
        tool: Which tool was executed
        action: Specific action performed
    """
    success: bool
    output: Any = None
    error: Optional[str] = None
    tool: Optional[str] = None
    action: Optional[str] = None


class ToolExecutor:
    """Executes tools without needing model inference

    This class provides direct execution of:
    - Git operations (status, commit, push, pull, clone)
    - Shell commands (mkdir, run, install, execute)
    - File operations (read, write, delete, list)

    No model loading required - all operations are direct system calls.
    """

    def __init__(self, git_manager, shell_manager, file_tools, permission_manager):
        """Initialize tool executor

        Args:
            git_manager: GitManager instance for git operations
            shell_manager: ShellManager instance for shell commands
            file_tools: FileTools instance for file operations
            permission_manager: PermissionManager for user consent
        """
        self.git = git_manager
        self.shell = shell_manager
        self.files = file_tools
        self.permissions = permission_manager

        # Map tool names to handler methods
        self._tool_handlers = {
            "git": self._handle_git,
            "shell": self._handle_shell,
            "file": self._handle_file,
        }

    def execute(self, tool: str, params: Dict[str, Any]) -> ToolResult:
        """Execute tool based on router's classification

        Args:
            tool: Tool type ("git", "shell", "file")
            params: Extracted parameters from intent router

        Returns:
            ToolResult with execution status and output
        """
        # Validate tool
        if tool not in self._tool_handlers:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool}",
                tool=tool
            )

        # Execute
        handler = self._tool_handlers[tool]
        try:
            return handler(params)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                tool=tool
            )

    def _handle_git(self, params: Dict[str, Any]) -> ToolResult:
        """Handle git operations

        Args:
            params: Git parameters (action, etc.)

        Returns:
            ToolResult with git operation output
        """
        action = params.get('action', 'status')

        # Map actions to git manager methods
        if action == 'status':
            result = self.git.git_status()
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="git",
                action="status"
            )

        elif action == 'commit':
            message = params.get('message', 'Update')
            result = self.git.git_commit(message)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="git",
                action="commit"
            )

        elif action == 'push':
            remote = params.get('remote', 'origin')
            branch = params.get('branch', None)
            result = self.git.git_push(remote, branch)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="git",
                action="push"
            )

        elif action == 'pull':
            remote = params.get('remote', 'origin')
            branch = params.get('branch', None)
            result = self.git.git_pull(remote, branch)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="git",
                action="pull"
            )

        elif action == 'clone':
            url = params.get('url')
            destination = params.get('destination')
            if not url:
                return ToolResult(
                    success=False,
                    error="No repository URL provided",
                    tool="git",
                    action="clone"
                )
            result = self.git.clone_repository(url, destination)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="git",
                action="clone"
            )

        elif action == 'init':
            result = self.git.git_init()
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="git",
                action="init"
            )

        elif action == 'add':
            files = params.get('files', '.')
            result = self.git.git_add(files)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="git",
                action="add"
            )

        else:
            return ToolResult(
                success=False,
                error=f"Unknown git action: {action}",
                tool="git"
            )

    def _handle_shell(self, params: Dict[str, Any]) -> ToolResult:
        """Handle shell commands

        Args:
            params: Shell parameters (command, etc.)

        Returns:
            ToolResult with command output
        """
        command = params.get('command', '')
        if not command:
            return ToolResult(
                success=False,
                error="No command provided",
                tool="shell"
            )

        # Check for special command patterns
        cmd_lower = command.lower()

        # Install dependencies
        if cmd_lower.startswith('install '):
            if 'requirements' in cmd_lower:
                result = self.shell.install_requirements()
            else:
                package = command.split('install ', 1)[1].strip()
                result = self.shell.install_package(package)

            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="shell",
                action="install"
            )

        # Create directory
        elif cmd_lower.startswith('mkdir '):
            directory = command.split('mkdir ', 1)[1].strip()
            result = self.shell.create_directory(directory)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="shell",
                action="mkdir"
            )

        # Run Python file
        elif cmd_lower.startswith('run '):
            filename = command.split('run ', 1)[1].strip()
            result = self.shell.run_python_file(filename)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="shell",
                action="run"
            )

        # Execute arbitrary shell command
        elif cmd_lower.startswith('execute '):
            shell_cmd = command.split('execute ', 1)[1].strip()
            result = self.shell.execute_command(shell_cmd)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="shell",
                action="execute"
            )

        # Default: execute as-is
        else:
            result = self.shell.execute_command(command)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="shell",
                action="execute"
            )

    def _handle_file(self, params: Dict[str, Any]) -> ToolResult:
        """Handle file operations

        Args:
            params: File parameters (filename, action, etc.)

        Returns:
            ToolResult with file operation result
        """
        raw_input = params.get('raw_input', '')
        filename = params.get('filename')

        # Determine action from raw input
        raw_lower = raw_input.lower()

        # Read file
        if any(word in raw_lower for word in ['read', 'show', 'display', 'cat', 'view']):
            if not filename:
                return ToolResult(
                    success=False,
                    error="No filename provided",
                    tool="file",
                    action="read"
                )

            result = self.files.read_file(filename)
            return ToolResult(
                success=result.get('success', False),
                output=result.get('content'),
                tool="file",
                action="read"
            )

        # List files
        elif any(word in raw_lower for word in ['list', 'ls']):
            result = self.files.list_files()
            return ToolResult(
                success=result.get('success', False),
                output=result.get('files', []),
                tool="file",
                action="list"
            )

        # Delete file
        elif any(word in raw_lower for word in ['delete', 'remove', 'rm']):
            if not filename:
                return ToolResult(
                    success=False,
                    error="No filename provided",
                    tool="file",
                    action="delete"
                )

            # Request permission
            if not self.permissions.request_file_deletion(filename):
                return ToolResult(
                    success=False,
                    error="Permission denied by user",
                    tool="file",
                    action="delete"
                )

            result = self.files.delete_file(filename)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="file",
                action="delete"
            )

        # Default: file exists check
        else:
            if not filename:
                return ToolResult(
                    success=False,
                    error="No filename provided",
                    tool="file"
                )

            result = self.files.file_exists(filename)
            return ToolResult(
                success=True,
                output={"exists": result.get('exists', False)},
                tool="file",
                action="check"
            )

    def can_handle_directly(self, tool: str) -> bool:
        """Check if this tool can be handled without model inference

        Args:
            tool: Tool name

        Returns:
            True if tool can be executed directly
        """
        return tool in self._tool_handlers
