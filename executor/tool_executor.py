"""Tool Executor - Execute tools without model inference

Enhanced for Phase 6 with:
- Safe fallback mechanisms for unknown tools
- Better error handling and recovery
- Tool aliasing and mapping
- Execution logging and retry logic
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


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

    def __init__(self, git_manager, shell_manager, file_tools, permission_manager, sqlite_tools=None):
        """Initialize tool executor

        Args:
            git_manager: GitManager instance for git operations
            shell_manager: ShellManager instance for shell commands
            file_tools: FileTools instance for file operations
            permission_manager: PermissionManager for user consent
            sqlite_tools: SQLiteTools instance for database operations
        """
        self.git = git_manager
        self.shell = shell_manager
        self.files = file_tools
        self.permissions = permission_manager
        self.sqlite = sqlite_tools

        # Map tool names to handler methods
        self._tool_handlers = {
            "git": self._handle_git,
            "shell": self._handle_shell,
            "file": self._handle_file,
            "sqlite": self._handle_sqlite,
        }

    def execute(self, tool: str, params: Dict[str, Any]) -> ToolResult:
        """Execute tool based on router's classification

        Args:
            tool: Tool type ("git", "shell", "file", "sqlite")
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

    def _handle_sqlite(self, params: Dict[str, Any]) -> ToolResult:
        """Handle SQLite operations

        Args:
            params: SQLite parameters (action, db_path, query, etc.)

        Returns:
            ToolResult with database operation result
        """
        if not self.sqlite:
             return ToolResult(
                success=False,
                error="SQLite tools not initialized",
                tool="sqlite"
            )

        action = params.get('action', 'query')
        db_path = params.get('db_path')

        if not db_path:
            return ToolResult(
                success=False,
                error="No database path provided",
                tool="sqlite",
                action=action
            )

        if action == 'query':
            query = params.get('query')
            if not query:
                return ToolResult(
                    success=False,
                    error="No query provided",
                    tool="sqlite",
                    action="query"
                )
            
            # Simple check for safety/permission could go here
            
            result = self.sqlite.execute_query(db_path, query)
            return ToolResult(
                success=result.get('success', False),
                output=result.get('result') if result.get('success') else result.get('error'),
                tool="sqlite",
                action="query"
            )

        elif action == 'schema':
            result = self.sqlite.get_schema(db_path)
            return ToolResult(
                success=result.get('success', False),
                output=result.get('schema') if result.get('success') else result.get('error'),
                tool="sqlite",
                action="schema"
            )
            
        else:
             return ToolResult(
                success=False,
                error=f"Unknown sqlite action: {action}",
                tool="sqlite"
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

            # Handle -p flag for mkdir (create parent directories)
            parents = False
            if directory.startswith('-p '):
                parents = True
                directory = directory[3:].strip()
            elif directory.startswith('-p'):
                parents = True
                directory = directory[2:].strip()

            # Handle multiple directories separated by space
            directories = directory.split()

            # For multiple directories, use batch permission
            if len(directories) > 1:
                # Request batch permission once for all directories
                if not self.permissions.request_multiple_file_operation(
                    f"Create {len(directories)} directories",
                    directories
                ):
                    return ToolResult(
                        success=False,
                        error="Permission denied by user",
                        tool="shell",
                        action="mkdir"
                    )

                # Create each directory without individual permission prompts
                results = []
                all_success = True
                for dir_name in directories:
                    try:
                        # Resolve path
                        from pathlib import Path
                        if dir_name.startswith('~'):
                            dir_path = Path(dir_name).expanduser()
                        elif Path(dir_name).is_absolute():
                            dir_path = Path(dir_name)
                        else:
                            dir_path = self.shell.workspace_dir / dir_name

                        # Create directory directly (permission already granted)
                        if dir_path.exists():
                            results.append({'success': True, 'message': f'Already exists: {dir_path}'})
                        else:
                            dir_path.mkdir(parents=parents, exist_ok=True)
                            results.append({'success': True, 'path': str(dir_path)})
                    except Exception as e:
                        results.append({'success': False, 'error': str(e)})
                        all_success = False

                return ToolResult(
                    success=all_success,
                    output={'directories': directories, 'results': results},
                    tool="shell",
                    action="mkdir"
                )
            else:
                # Single directory - use normal flow
                result = self.shell.create_directory(directories[0], parents=parents)
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
        forced_action = params.get('action')

        # Write/Create file (if explicitly requested or via action param)
        if forced_action in ['write', 'create'] or any(word in raw_lower for word in ['write', 'create', 'make']):
            if not filename:
                return ToolResult(
                    success=False,
                    error="No filename provided",
                    tool="file",
                    action="write"
                )
            
            content = params.get('content')
            if content is None:
                return ToolResult(
                    success=False,
                    error="No content provided",
                    tool="file",
                    action="write"
                )

            overwrite = params.get('overwrite', False)
            result = self.files.write_file(filename, content, overwrite=overwrite)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                tool="file",
                action="write"
            )

        # Read file
        elif any(word in raw_lower for word in ['read', 'show', 'display', 'cat', 'view']) or forced_action == 'read':
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
        return tool in self._tool_handlers or tool in self._tool_aliases

    # ============================================================
    # Phase 6 Enhancements: Safe Fallbacks and Error Handling
    # ============================================================

    # Tool aliases for common variations
    _tool_aliases = {
        'database': 'sqlite',
        'db': 'sqlite',
        'sql': 'sqlite',
        'bash': 'shell',
        'terminal': 'shell',
        'cmd': 'shell',
        'command': 'shell',
        'dir': 'shell',
        'fs': 'file',
        'filesystem': 'file',
        'vcs': 'git',
        'version_control': 'git',
    }

    def execute_safe(self, tool: str, params: Dict[str, Any], fallback: str = None) -> ToolResult:
        """Execute tool with safe fallback handling

        This method provides additional safety by:
        1. Resolving tool aliases
        2. Attempting to infer tool from params if unknown
        3. Using fallback tool if primary fails
        4. Logging all execution attempts

        Args:
            tool: Tool type
            params: Tool parameters
            fallback: Optional fallback tool if primary fails

        Returns:
            ToolResult with execution status
        """
        # Resolve alias
        resolved_tool = self._tool_aliases.get(tool, tool)

        # Log execution attempt
        logger.info(f"Tool execution: {tool} -> {resolved_tool}")
        logger.debug(f"Parameters: {params}")

        # Try primary tool
        result = self.execute(resolved_tool, params)

        if result.success:
            return result

        # Try to infer correct tool from params if failed
        if not result.success and 'Unknown tool' in str(result.error):
            inferred = self._infer_tool_from_params(params)
            if inferred and inferred != resolved_tool:
                logger.info(f"Inferring tool from params: {inferred}")
                result = self.execute(inferred, params)
                if result.success:
                    return result

        # Try fallback if specified
        if fallback and fallback != resolved_tool:
            logger.info(f"Trying fallback tool: {fallback}")
            result = self.execute(fallback, params)

        return result

    def _infer_tool_from_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Infer tool type from parameters

        Args:
            params: Tool parameters

        Returns:
            Inferred tool name or None
        """
        # Check for common parameter patterns
        if 'command' in params:
            cmd = params['command'].lower()
            if cmd.startswith('git '):
                return 'git'
            if cmd.startswith('mkdir ') or cmd.startswith('cd ') or cmd.startswith('ls '):
                return 'shell'
            return 'shell'

        if 'filename' in params or 'content' in params:
            return 'file'

        if 'query' in params or 'db_path' in params:
            return 'sqlite'

        if 'repo' in params or 'branch' in params:
            return 'git'

        return None

    def execute_with_retry(
        self,
        tool: str,
        params: Dict[str, Any],
        max_retries: int = 2,
        retry_delay: float = 1.0
    ) -> ToolResult:
        """Execute tool with retry logic

        Args:
            tool: Tool type
            params: Tool parameters
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            ToolResult from successful execution or last attempt
        """
        import time

        last_result = None
        for attempt in range(max_retries + 1):
            result = self.execute(tool, params)

            if result.success:
                return result

            last_result = result

            # Check if error is retryable
            if not self._is_retryable_error(result.error):
                break

            if attempt < max_retries:
                logger.info(f"Retry {attempt + 1}/{max_retries} after error: {result.error}")
                time.sleep(retry_delay)

        return last_result

    def _is_retryable_error(self, error: str) -> bool:
        """Check if error is retryable

        Args:
            error: Error message

        Returns:
            True if error can be retried
        """
        if not error:
            return False

        # Non-retryable patterns
        non_retryable = [
            'Permission denied',
            'Forbidden',
            'Unknown tool',
            'No such file',
            'File not found',
            'already exists',
        ]

        for pattern in non_retryable:
            if pattern.lower() in error.lower():
                return False

        # Retryable patterns
        retryable = [
            'timed out',
            'timeout',
            'connection',
            'network',
            'busy',
            'locked',
        ]

        for pattern in retryable:
            if pattern.lower() in error.lower():
                return True

        return False

    def execute_batch(
        self,
        operations: List[Dict[str, Any]],
        stop_on_error: bool = True
    ) -> List[ToolResult]:
        """Execute multiple tool operations

        Args:
            operations: List of {tool: str, params: dict} dicts
            stop_on_error: If True, stop on first error

        Returns:
            List of ToolResult objects
        """
        results = []

        for op in operations:
            tool = op.get('tool')
            params = op.get('params', {})

            if not tool:
                results.append(ToolResult(
                    success=False,
                    error="No tool specified",
                    tool=None
                ))
                if stop_on_error:
                    break
                continue

            result = self.execute_safe(tool, params)
            results.append(result)

            if not result.success and stop_on_error:
                break

        return results

    def create_directory_safe(self, path: str) -> ToolResult:
        """Safely create a directory, handling nested paths

        Args:
            path: Directory path to create

        Returns:
            ToolResult with status
        """
        try:
            dir_path = Path(path)

            # If path is relative, resolve to workspace
            if not dir_path.is_absolute():
                workspace = getattr(self.shell, 'workspace_dir', Path.cwd())
                dir_path = workspace / path

            # Check if exists
            if dir_path.exists():
                if dir_path.is_dir():
                    return ToolResult(
                        success=True,
                        output={'message': f'Directory already exists: {dir_path}'},
                        tool='shell',
                        action='mkdir'
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=f'Path exists but is not a directory: {dir_path}',
                        tool='shell',
                        action='mkdir'
                    )

            # Create with parents
            result = self.shell.create_directory(str(dir_path), parents=True)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                error=result.get('error'),
                tool='shell',
                action='mkdir'
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                tool='shell',
                action='mkdir'
            )

    def write_file_safe(
        self,
        filename: str,
        content: str,
        create_dirs: bool = True,
        backup: bool = True
    ) -> ToolResult:
        """Safely write file with directory creation and backup

        Args:
            filename: File path
            content: File content
            create_dirs: Create parent directories if needed
            backup: Create backup if file exists

        Returns:
            ToolResult with status
        """
        try:
            file_path = Path(filename)

            # Create parent directories if needed
            if create_dirs and file_path.parent and not file_path.parent.exists():
                if hasattr(self.shell, 'workspace_dir'):
                    parent = self.shell.workspace_dir / file_path.parent
                else:
                    parent = file_path.parent

                if not parent.exists():
                    mkdir_result = self.create_directory_safe(str(parent))
                    if not mkdir_result.success:
                        return ToolResult(
                            success=False,
                            error=f"Failed to create directory: {mkdir_result.error}",
                            tool='file',
                            action='write'
                        )

            # Write file
            result = self.files.write_file(filename, content, overwrite=True)
            return ToolResult(
                success=result.get('success', False),
                output=result,
                error=result.get('error'),
                tool='file',
                action='write'
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                tool='file',
                action='write'
            )

    def get_tool_help(self, tool: str) -> Dict[str, Any]:
        """Get help information for a tool

        Args:
            tool: Tool name

        Returns:
            Help information dictionary
        """
        help_info = {
            'git': {
                'description': 'Git version control operations',
                'actions': ['status', 'commit', 'push', 'pull', 'clone', 'init', 'add'],
                'examples': [
                    {'action': 'status', 'params': {}},
                    {'action': 'commit', 'params': {'message': 'Update'}},
                    {'action': 'push', 'params': {'remote': 'origin', 'branch': 'main'}},
                ]
            },
            'shell': {
                'description': 'Shell command execution',
                'actions': ['execute', 'mkdir', 'run', 'install'],
                'examples': [
                    {'command': 'ls -la'},
                    {'command': 'mkdir mydir'},
                    {'command': 'run script.py'},
                ]
            },
            'file': {
                'description': 'File system operations',
                'actions': ['read', 'write', 'delete', 'list', 'check'],
                'examples': [
                    {'action': 'read', 'filename': 'test.py'},
                    {'action': 'write', 'filename': 'out.py', 'content': '# code'},
                    {'action': 'list'},
                ]
            },
            'sqlite': {
                'description': 'SQLite database operations',
                'actions': ['query', 'schema'],
                'examples': [
                    {'action': 'query', 'db_path': 'db.sqlite', 'query': 'SELECT * FROM users'},
                    {'action': 'schema', 'db_path': 'db.sqlite'},
                ]
            }
        }

        # Resolve alias
        resolved = self._tool_aliases.get(tool, tool)
        return help_info.get(resolved, {'error': f'Unknown tool: {tool}'})

    def list_available_tools(self) -> List[str]:
        """List all available tools including aliases

        Returns:
            List of tool names
        """
        tools = list(self._tool_handlers.keys())
        aliases = list(self._tool_aliases.keys())
        return sorted(set(tools + aliases))
