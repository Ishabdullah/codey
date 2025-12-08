"""Shell command execution manager for Codey - Enhanced v2.1"""
import subprocess
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class ShellManager:
    """Handles safe shell command execution with enhanced security and classification"""

    # Command classification
    SAFE_COMMANDS = {
        'ls', 'pwd', 'which', 'cat', 'head', 'tail', 'echo', 'env',
        'date', 'uptime', 'whoami', 'uname', 'file', 'wc', 'grep',
        'find', 'locate', 'tree', 'du', 'df', 'free', 'ps', 'top'
    }

    RISKY_COMMANDS = {
        'git push', 'git force', 'git reset', 'pip install', 'npm install',
        'mkdir', 'touch', 'cp', 'mv', 'chmod', 'chown', 'ln', 'wget',
        'curl', 'apt', 'pkg', 'make', 'gcc', 'python', 'node', 'npm'
    }

    # Forbidden patterns (regex)
    FORBIDDEN_PATTERNS = [
        r'rm\s+-rf\s+/',                    # rm -rf /
        r'rm\s+-rf\s+/\w+',                 # rm -rf /anything
        r'rm\s+-rf\s+\.\.',                 # rm -rf ..
        r'rm\s+-rf\s+~',                    # rm -rf ~
        r'rm\s+-rf\s+\*',                   # rm -rf *
        r'mkfs',                             # Format filesystem
        r'dd\s+if=.*of=/dev/',              # Direct disk write
        r'fdisk',                            # Partition table modification
        r'format',                           # Format command
        r'git\s+push\s+.*--force.*main',    # Force push to main
        r'git\s+push\s+.*--force.*master',  # Force push to master
        r'git\s+reset\s+--hard\s+origin',   # Hard reset to origin (destructive)
        r':\(\)\{.*;\}',                     # Fork bomb pattern
    ]

    def __init__(self, permission_manager, workspace_dir, config=None):
        self.permission_manager = permission_manager
        self.workspace_dir = Path(workspace_dir)
        self.config = config

        # Initialize command logger if logging enabled
        self.command_logger = None
        if config and hasattr(config, 'log_dir'):
            try:
                from utils.command_logger import CommandLogger
                self.command_logger = CommandLogger(config.log_dir)
            except ImportError:
                pass  # Logger not available

        # Load safety settings from config
        self.enable_dangerous_commands = False
        self.log_command_decisions = True
        self.require_preview_for_risky = True

        if config and hasattr(config, 'shell_safety'):
            safety = config.shell_safety
            self.enable_dangerous_commands = safety.get('enable_dangerous_commands', False)
            self.log_command_decisions = safety.get('log_command_decisions', True)
            self.require_preview_for_risky = safety.get('require_preview_for_risky', True)

    def classify_command(self, command: str) -> Tuple[str, str]:
        """
        Classify a command as SAFE, RISKY, or FORBIDDEN
        Returns: (classification, reason)
        """
        # Check for forbidden patterns first
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return ('FORBIDDEN', f'Matches forbidden pattern: {pattern}')

        # Extract base command
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return ('SAFE', 'Empty command')

        base_cmd = cmd_parts[0]

        # Check if it's a safe command
        if base_cmd in self.SAFE_COMMANDS:
            return ('SAFE', 'Known safe command')

        # Check for risky command patterns
        for risky in self.RISKY_COMMANDS:
            if command.startswith(risky) or base_cmd in risky:
                return ('RISKY', f'Command requires caution: {risky}')

        # Check for specific dangerous flags
        if 'rm' in command:
            if '-rf' in command or '-fr' in command:
                return ('RISKY', 'Recursive file deletion')
            if '-r' in command or '-f' in command:
                return ('RISKY', 'File deletion with flags')
            return ('RISKY', 'File deletion command')

        # Default to RISKY for unknown commands
        return ('RISKY', 'Unknown command - requires verification')

    def execute_command(self, command: str, description: str = None,
                       cwd: str = None, timeout: int = 60) -> Dict:
        """Execute a shell command with enhanced safety checks"""
        try:
            # Classify the command
            classification, reason = self.classify_command(command)

            # Handle FORBIDDEN commands
            if classification == 'FORBIDDEN':
                error_msg = self._format_error_message(
                    'FORBIDDEN COMMAND',
                    f'This command is blocked for safety: {reason}',
                    command,
                    cwd
                )

                # Log the denial
                if self.command_logger and self.log_command_decisions:
                    self.command_logger.log_command(
                        command, 'forbidden', classification, cwd, reason
                    )

                print(error_msg)
                return {'success': False, 'error': f'Forbidden command: {reason}'}

            # Set working directory
            work_dir = Path(cwd) if cwd else self.workspace_dir

            # Request permission with appropriate details
            desc = description or self._infer_description(command)

            if classification == 'RISKY' and self.require_preview_for_risky:
                # Show detailed preview for risky commands
                if not self._request_risky_command_permission(
                    command, desc, classification, reason, work_dir
                ):
                    # Log the denial
                    if self.command_logger and self.log_command_decisions:
                        self.command_logger.log_command(
                            command, 'denied', classification, str(work_dir)
                        )
                    return {'success': False, 'error': 'Permission denied by user'}
            else:
                # Standard permission request
                if not self.permission_manager.request_shell_command(command, desc):
                    # Log the denial
                    if self.command_logger and self.log_command_decisions:
                        self.command_logger.log_command(
                            command, 'denied', classification, str(work_dir)
                        )
                    return {'success': False, 'error': 'Permission denied by user'}

            # Log approval
            if self.command_logger and self.log_command_decisions:
                self.command_logger.log_command(
                    command, 'approved', classification, str(work_dir)
                )

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Log execution result
            if self.command_logger and self.log_command_decisions:
                status = 'executed' if result.returncode == 0 else 'failed'
                error = result.stderr if result.returncode != 0 else None
                self.command_logger.log_command(
                    command, status, classification, str(work_dir), error
                )

            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': command,
                'classification': classification
            }

        except subprocess.TimeoutExpired:
            error_msg = self._format_error_message(
                'TIMEOUT',
                f'Command exceeded timeout of {timeout} seconds',
                command,
                cwd
            )
            print(error_msg)
            return {'success': False, 'error': f'Command timed out after {timeout} seconds'}

        except PermissionError as e:
            error_msg = self._format_error_message(
                'PERMISSION ERROR',
                'Insufficient permissions to execute this command',
                command,
                cwd,
                str(e)
            )
            print(error_msg)
            return {'success': False, 'error': 'Insufficient permissions'}

        except FileNotFoundError as e:
            error_msg = self._format_error_message(
                'COMMAND NOT FOUND',
                'The command or file was not found',
                command,
                cwd,
                str(e)
            )
            print(error_msg)
            return {'success': False, 'error': 'Command not found'}

        except Exception as e:
            error_msg = self._format_error_message(
                'EXECUTION ERROR',
                'An unexpected error occurred',
                command,
                cwd,
                str(e)
            )
            print(error_msg)
            return {'success': False, 'error': f'Execution error: {str(e)}'}

    def _request_risky_command_permission(self, command: str, description: str,
                                          classification: str, reason: str,
                                          work_dir: Path) -> bool:
        """Request permission for risky commands with detailed preview"""
        print("\n⚠️  RISKY COMMAND DETECTED")
        print("=" * 60)
        print(f"Classification: {classification}")
        print(f"Reason: {reason}")
        print(f"\nCommand: {command}")
        print(f"Working Directory: {work_dir}")
        print(f"Description: {description}")
        print("=" * 60)

        try:
            response = input("\n⚠️  This command may modify system state. Proceed? [y/n]: ").strip().lower()
            return response in ['y', 'yes']
        except (KeyboardInterrupt, EOFError):
            print("\n   Operation cancelled.")
            return False

    def _format_error_message(self, error_type: str, message: str,
                              command: str = None, cwd: str = None,
                              details: str = None) -> str:
        """Format a user-friendly error message (no raw stack traces)"""
        msg = f"\n❌ {error_type}\n"
        msg += "─" * 60 + "\n"
        msg += f"Message: {message}\n"

        if command:
            msg += f"Command: {command}\n"
        if cwd:
            msg += f"Directory: {cwd}\n"
        if details:
            msg += f"Details: {details}\n"

        msg += "─" * 60
        return msg

    def install_requirements(self, requirements_file: str = 'requirements.txt',
                            cwd: str = None) -> Dict:
        """Install Python packages from requirements.txt"""
        try:
            # Resolve path
            work_dir = Path(cwd) if cwd else self.workspace_dir
            req_path = work_dir / requirements_file

            if not req_path.exists():
                return {'success': False, 'error': f'File not found: {req_path}'}

            # Read requirements
            with open(req_path, 'r') as f:
                packages = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith('#')
                ]

            if not packages:
                return {'success': False, 'error': 'No packages found in requirements file'}

            # Request permission
            if not self.permission_manager.request_dependency_install(packages, requirements_file):
                return {'success': False, 'error': 'Permission denied by user'}

            # Install packages
            result = subprocess.run(
                ['pip', 'install', '-r', str(req_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for installations
            )

            return {
                'success': result.returncode == 0,
                'packages': packages,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Installation timed out'}
        except Exception as e:
            error_msg = self._format_error_message(
                'INSTALLATION ERROR',
                'Failed to install requirements',
                f'pip install -r {requirements_file}',
                cwd,
                str(e)
            )
            print(error_msg)
            return {'success': False, 'error': str(e)}

    def install_package(self, package: str) -> Dict:
        """Install a single Python package"""
        try:
            # Request permission
            if not self.permission_manager.request_dependency_install([package]):
                return {'success': False, 'error': 'Permission denied by user'}

            # Install package
            result = subprocess.run(
                ['pip', 'install', package],
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                'success': result.returncode == 0,
                'package': package,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Installation timed out'}
        except Exception as e:
            error_msg = self._format_error_message(
                'INSTALLATION ERROR',
                'Failed to install package',
                f'pip install {package}',
                None,
                str(e)
            )
            print(error_msg)
            return {'success': False, 'error': str(e)}

    def create_directory(self, directory: str, parents: bool = True) -> Dict:
        """Create a directory with permission check"""
        try:
            # Support absolute paths - don't force workspace_dir
            if directory.startswith('~'):
                dir_path = Path(directory).expanduser()
            elif Path(directory).is_absolute():
                dir_path = Path(directory)
            else:
                dir_path = self.workspace_dir / directory

            # Check if already exists
            if dir_path.exists():
                return {'success': False, 'error': f'Directory already exists: {dir_path}'}

            # Request permission
            if not self.permission_manager.request_directory_creation(str(dir_path)):
                return {'success': False, 'error': 'Permission denied by user'}

            # Create directory
            dir_path.mkdir(parents=parents, exist_ok=False)

            return {
                'success': True,
                'path': str(dir_path),
                'message': f'Created directory: {dir_path}'
            }

        except Exception as e:
            error_msg = self._format_error_message(
                'DIRECTORY CREATION ERROR',
                'Failed to create directory',
                f'mkdir {directory}',
                None,
                str(e)
            )
            print(error_msg)
            return {'success': False, 'error': str(e)}

    def run_python_file(self, filename: str, args: List[str] = None,
                       cwd: str = None, timeout: int = 60) -> Dict:
        """Execute a Python file"""
        try:
            work_dir = Path(cwd) if cwd else self.workspace_dir
            file_path = work_dir / filename

            if not file_path.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            # Build command
            cmd = ['python', str(file_path)]
            if args:
                cmd.extend(args)

            # Request permission
            cmd_str = ' '.join(cmd)
            if not self.permission_manager.request_shell_command(cmd_str, f"Run Python script: {filename}"):
                return {'success': False, 'error': 'Permission denied by user'}

            # Execute
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Execution timed out after {timeout} seconds'}
        except Exception as e:
            error_msg = self._format_error_message(
                'EXECUTION ERROR',
                'Failed to run Python file',
                f'python {filename}',
                cwd,
                str(e)
            )
            print(error_msg)
            return {'success': False, 'error': str(e)}

    def check_command_available(self, command: str) -> bool:
        """Check if a command is available in the system"""
        try:
            result = subprocess.run(
                ['which', command],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def get_system_info(self) -> Dict:
        """Get system information"""
        info = {
            'python_version': None,
            'pip_version': None,
            'git_available': False,
            'npm_available': False
        }

        try:
            # Python version
            result = subprocess.run(['python', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['python_version'] = result.stdout.strip()

            # Pip version
            result = subprocess.run(['pip', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['pip_version'] = result.stdout.strip()

            # Git
            info['git_available'] = self.check_command_available('git')

            # NPM
            info['npm_available'] = self.check_command_available('npm')

        except Exception as e:
            info['error'] = str(e)

        return info

    def _infer_description(self, command: str) -> str:
        """Infer a description from the command"""
        cmd_parts = command.split()
        if not cmd_parts:
            return "Execute shell command"

        cmd = cmd_parts[0]

        descriptions = {
            'ls': 'List directory contents',
            'cd': 'Change directory',
            'pwd': 'Print working directory',
            'mkdir': 'Create directory',
            'touch': 'Create file',
            'cat': 'Display file contents',
            'cp': 'Copy file',
            'mv': 'Move/rename file',
            'rm': 'Delete file',
            'chmod': 'Change file permissions',
            'git': 'Git operation',
            'pip': 'Python package operation',
            'python': 'Run Python script',
            'npm': 'NPM operation'
        }

        return descriptions.get(cmd, f"Execute: {cmd}")
