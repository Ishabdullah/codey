"""Tool system for file operations and code manipulation"""
import os
import shutil
from pathlib import Path
from datetime import datetime

class FileTools:
    """Tools for safe file operations"""

    def __init__(self, config):
        self.config = config
        self.workspace = config.workspace_dir

    def _resolve_path(self, filepath):
        """Resolve a filepath relative to workspace or as absolute"""
        path = Path(filepath)
        if not path.is_absolute():
            path = self.workspace / path
        return path

    def _backup_file(self, filepath):
        """Create a timestamped backup of a file"""
        if not self.config.backup_before_edit:
            return None

        path = self._resolve_path(filepath)
        if not path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.config.log_dir / "backups"
        backup_dir.mkdir(exist_ok=True, parents=True)

        backup_path = backup_dir / f"{path.name}.{timestamp}.bak"
        shutil.copy2(path, backup_path)
        return backup_path

    def read_file(self, filepath):
        """Read and return file contents"""
        path = self._resolve_path(filepath)

        if not path.exists():
            return {
                'success': False,
                'error': f"File not found: {filepath}",
                'content': None
            }

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                'success': True,
                'content': content,
                'path': str(path)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'content': None
            }

    def write_file(self, filepath, content, overwrite=False):
        """Write content to a file"""
        path = self._resolve_path(filepath)

        # Check if file exists
        if path.exists() and not overwrite:
            return {
                'success': False,
                'error': f"File already exists: {filepath}. Use overwrite=True to replace.",
                'path': str(path)
            }

        # Backup if editing existing file
        backup_path = None
        if path.exists():
            backup_path = self._backup_file(filepath)

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {
                'success': True,
                'path': str(path),
                'backup': str(backup_path) if backup_path else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'path': str(path)
            }

    def list_files(self, directory='.', pattern='*'):
        """List files in a directory"""
        dir_path = self._resolve_path(directory)

        if not dir_path.exists():
            return {
                'success': False,
                'error': f"Directory not found: {directory}",
                'files': []
            }

        try:
            files = list(dir_path.glob(pattern))
            return {
                'success': True,
                'files': [str(f.relative_to(self.workspace)) if f.is_relative_to(self.workspace) else str(f) for f in files],
                'path': str(dir_path)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'files': []
            }

    def delete_file(self, filepath):
        """Delete a file (with backup)"""
        path = self._resolve_path(filepath)

        if not path.exists():
            return {
                'success': False,
                'error': f"File not found: {filepath}"
            }

        # Always backup before delete
        backup_path = self._backup_file(filepath)

        try:
            path.unlink()
            return {
                'success': True,
                'path': str(path),
                'backup': str(backup_path) if backup_path else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def file_exists(self, filepath):
        """Check if a file exists"""
        path = self._resolve_path(filepath)
        return {
            'success': True,
            'exists': path.exists(),
            'path': str(path)
        }

    def patch_file(self, filepath, edits):
        """Apply diff-based edits to a file (Phase 5)

        Args:
            filepath: Path to file to patch
            edits: List of EditBlock objects from DiffGenerator

        Returns:
            Dict with success status, path, backup info
        """
        from core.diff_generator import DiffGenerator

        # Read original file
        read_result = self.read_file(filepath)
        if not read_result['success']:
            return read_result

        original = read_result['content']

        # Initialize diff generator
        diff_gen = DiffGenerator()

        # Validate edits
        errors = diff_gen.validate_edits(original, edits)
        if errors:
            return {
                'success': False,
                'error': f"Invalid edits:\n" + "\n".join(errors),
                'path': str(self._resolve_path(filepath))
            }

        # Backup before applying edits
        backup_path = self._backup_file(filepath)

        # Apply edits
        try:
            new_content = diff_gen.apply_edits(original, edits)

            # Write patched content
            write_result = self.write_file(filepath, new_content, overwrite=True)

            if write_result['success']:
                # Generate diff for display
                unified_diff = diff_gen.generate_unified_diff(original, new_content, filepath)

                # Estimate token savings
                savings = diff_gen.estimate_token_savings(original, edits)

                return {
                    'success': True,
                    'path': write_result['path'],
                    'backup': str(backup_path) if backup_path else None,
                    'num_edits': len(edits),
                    'diff': unified_diff,
                    'token_savings': savings
                }
            else:
                return write_result

        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to apply edits: {str(e)}",
                'path': str(self._resolve_path(filepath))
            }
