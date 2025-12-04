"""Automatic cleanup utility for Codey - removes junk files created by errors"""
import os
import re
from pathlib import Path


class CleanupManager:
    """Manages automatic cleanup of junk files and directories"""

    # Patterns for junk file/directory names that should be removed
    JUNK_PATTERNS = [
        # Common junk from command misinterpretation
        r'^directory$',
        r'^the$',
        r'^`venv`$',
        r'^\`.*\`$',  # Any backtick-wrapped names
        r'^file$',
        r'^folder$',
        r'^script$',
        r'^code$',

        # Single-character or very short invalid names
        r'^[a-z]$',  # Single letters (except valid ones)

        # Temporary/test files that shouldn't persist
        r'^test\d*$',
        r'^tmp\d*$',
        r'^temp\d*$',
    ]

    # Whitelist - these should NEVER be deleted
    WHITELIST = {
        'a',  # Could be valid
        'i',  # Could be valid
        'x',  # Could be valid
        'y',  # Could be valid
        'z',  # Could be valid
        # Add any other single-char names that might be intentional
    }

    def __init__(self, workspace_dir):
        """Initialize cleanup manager

        Args:
            workspace_dir: Path to workspace directory to clean
        """
        self.workspace_dir = Path(workspace_dir)

    def is_junk_file(self, filename):
        """Check if a filename matches junk patterns

        Args:
            filename: Name of file/directory to check

        Returns:
            bool: True if file should be cleaned up
        """
        # Never clean whitelisted names
        if filename in self.WHITELIST:
            return False

        # Check against junk patterns
        for pattern in self.JUNK_PATTERNS:
            if re.match(pattern, filename, re.IGNORECASE):
                return True

        return False

    def cleanup_workspace(self, dry_run=False):
        """Clean up junk files from workspace

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            dict: Summary of cleanup operation
        """
        if not self.workspace_dir.exists():
            return {'cleaned': 0, 'files': [], 'error': 'Workspace does not exist'}

        cleaned_files = []

        try:
            for item in self.workspace_dir.iterdir():
                if self.is_junk_file(item.name):
                    if dry_run:
                        cleaned_files.append(str(item))
                    else:
                        # Remove file or directory
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            # Remove directory and contents
                            import shutil
                            shutil.rmtree(item)
                        cleaned_files.append(str(item))

            return {
                'success': True,
                'cleaned': len(cleaned_files),
                'files': cleaned_files,
                'dry_run': dry_run
            }

        except Exception as e:
            return {
                'success': False,
                'cleaned': len(cleaned_files),
                'files': cleaned_files,
                'error': str(e)
            }

    def get_junk_files(self):
        """Get list of junk files without cleaning

        Returns:
            list: List of junk file paths
        """
        result = self.cleanup_workspace(dry_run=True)
        return result.get('files', [])
