"""Shell command execution manager for Codey"""
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Optional

class ShellManager:
    """Handles safe shell command execution with permission checks"""

    def __init__(self, permission_manager, workspace_dir):
        self.permission_manager = permission_manager
        self.workspace_dir = Path(workspace_dir)

        # Dangerous commands that require extra caution
        self.dangerous_commands = [
            'rm', 'rmdir', 'del', 'format', 'fdisk',
            'dd', 'mkfs', '>', '>>', 'sudo', 'su'
        ]

    def execute_command(self, command: str, description: str = None,
                       cwd: str = None, timeout: int = 60) -> Dict:
        """Execute a shell command with permission check"""
        try:
            # Check if command contains dangerous operations
            is_dangerous = any(danger in command.split() for danger in self.dangerous_commands)

            # Request permission
            desc = description or self._infer_description(command)
            if is_dangerous:
                desc += " ⚠️ POTENTIALLY DANGEROUS"

            if not self.permission_manager.request_shell_command(command, desc):
                return {'success': False, 'error': 'Permission denied by user'}

            # Set working directory
            work_dir = Path(cwd) if cwd else self.workspace_dir

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': command
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Command timed out after {timeout} seconds'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

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
            return {'success': False, 'error': str(e)}

    def create_directory(self, directory: str, parents: bool = True) -> Dict:
        """Create a directory with permission check"""
        try:
            dir_path = self.workspace_dir / directory if not Path(directory).is_absolute() else Path(directory)

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
