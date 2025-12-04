"""Git operations manager for Codey"""
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Optional

class GitManager:
    """Handles all git operations with proper error handling and safety checks"""

    def __init__(self, permission_manager, workspace_dir):
        self.permission_manager = permission_manager
        self.workspace_dir = Path(workspace_dir)

    def clone_repository(self, repo_url: str, destination: str = None) -> Dict:
        """Clone a git repository"""
        try:
            # Determine destination
            if destination:
                dest_path = self.workspace_dir / destination
            else:
                # Extract repo name from URL
                repo_name = repo_url.rstrip('/').split('/')[-1]
                if repo_name.endswith('.git'):
                    repo_name = repo_name[:-4]
                dest_path = self.workspace_dir / repo_name

            # Check if destination already exists
            if dest_path.exists():
                return {
                    'success': False,
                    'error': f"Destination '{dest_path}' already exists"
                }

            # Request permission
            if not self.permission_manager.request_git_clone(repo_url, str(dest_path)):
                return {'success': False, 'error': 'Permission denied by user'}

            # Ensure parent directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Clone the repository
            result = subprocess.run(
                ['git', 'clone', repo_url, str(dest_path)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                return {
                    'success': True,
                    'path': str(dest_path),
                    'message': f"Successfully cloned to {dest_path}"
                }
            else:
                return {
                    'success': False,
                    'error': f"Git clone failed: {result.stderr}"
                }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Clone operation timed out'}
        except FileNotFoundError:
            return {'success': False, 'error': 'Git is not installed'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def git_status(self, repo_path: str = None) -> Dict:
        """Get git status of a repository"""
        try:
            path = Path(repo_path) if repo_path else self.workspace_dir

            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parse status
                modified = []
                untracked = []
                staged = []

                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    status = line[:2]
                    filename = line[3:]

                    if status[0] in ['M', 'A', 'D', 'R', 'C']:
                        staged.append(filename)
                    if status[1] in ['M', 'D']:
                        modified.append(filename)
                    if status == '??':
                        untracked.append(filename)

                return {
                    'success': True,
                    'staged': staged,
                    'modified': modified,
                    'untracked': untracked,
                    'clean': len(staged) == 0 and len(modified) == 0 and len(untracked) == 0
                }
            else:
                return {'success': False, 'error': 'Not a git repository'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def git_add(self, files: List[str], repo_path: str = None) -> Dict:
        """Stage files for commit"""
        try:
            path = Path(repo_path) if repo_path else self.workspace_dir

            result = subprocess.run(
                ['git', 'add'] + files,
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return {'success': True, 'files': files}
            else:
                return {'success': False, 'error': result.stderr}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def git_commit(self, message: str, files: List[str] = None, repo_path: str = None) -> Dict:
        """Create a git commit"""
        try:
            path = Path(repo_path) if repo_path else self.workspace_dir

            # Get files to commit if not specified
            if files is None:
                status = self.git_status(repo_path)
                if status['success']:
                    files = status['staged'] + status['modified']
                else:
                    return status

            if not files:
                return {'success': False, 'error': 'No files to commit'}

            # Stage files if needed
            add_result = self.git_add(files, repo_path)
            if not add_result['success']:
                return add_result

            # Request permission
            if not self.permission_manager.request_git_commit(message, files):
                return {'success': False, 'error': 'Permission denied by user'}

            # Create commit
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return {
                    'success': True,
                    'message': message,
                    'files': files,
                    'output': result.stdout
                }
            else:
                return {'success': False, 'error': result.stderr}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def git_push(self, remote: str = 'origin', branch: str = None, repo_path: str = None) -> Dict:
        """Push commits to remote repository"""
        try:
            path = Path(repo_path) if repo_path else self.workspace_dir

            # Get current branch if not specified
            if branch is None:
                branch_result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if branch_result.returncode == 0:
                    branch = branch_result.stdout.strip()
                else:
                    return {'success': False, 'error': 'Could not determine current branch'}

            # Request permission
            if not self.permission_manager.request_git_push(branch, remote):
                return {'success': False, 'error': 'Permission denied by user'}

            # Push to remote
            result = subprocess.run(
                ['git', 'push', remote, branch],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return {
                    'success': True,
                    'remote': remote,
                    'branch': branch,
                    'output': result.stdout
                }
            else:
                return {'success': False, 'error': result.stderr}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def git_pull(self, remote: str = 'origin', branch: str = None, repo_path: str = None) -> Dict:
        """Pull changes from remote repository"""
        try:
            path = Path(repo_path) if repo_path else self.workspace_dir

            # Get current branch if not specified
            if branch is None:
                branch_result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if branch_result.returncode == 0:
                    branch = branch_result.stdout.strip()
                else:
                    branch = 'main'

            # Pull from remote
            result = subprocess.run(
                ['git', 'pull', remote, branch],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return {
                    'success': True,
                    'remote': remote,
                    'branch': branch,
                    'output': result.stdout
                }
            else:
                return {'success': False, 'error': result.stderr}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def git_init(self, repo_path: str = None) -> Dict:
        """Initialize a new git repository"""
        try:
            path = Path(repo_path) if repo_path else self.workspace_dir

            # Check if already a git repo
            if (path / '.git').exists():
                return {'success': False, 'error': 'Already a git repository'}

            result = subprocess.run(
                ['git', 'init'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return {'success': True, 'path': str(path)}
            else:
                return {'success': False, 'error': result.stderr}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_commit_history(self, count: int = 10, repo_path: str = None) -> Dict:
        """Get recent commit history"""
        try:
            path = Path(repo_path) if repo_path else self.workspace_dir

            result = subprocess.run(
                ['git', 'log', f'-{count}', '--pretty=format:%h|%an|%ar|%s'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                commits = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|', 3)
                        if len(parts) == 4:
                            commits.append({
                                'hash': parts[0],
                                'author': parts[1],
                                'date': parts[2],
                                'message': parts[3]
                            })

                return {'success': True, 'commits': commits}
            else:
                return {'success': False, 'error': result.stderr}

        except Exception as e:
            return {'success': False, 'error': str(e)}
