"""Permission manager for Codey - handles all user confirmations"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import colors if available
try:
    from cli.colors import permission, info, warning, bold, Icons
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Fallback to no colors
    def permission(x): return x
    def info(x): return x
    def warning(x): return x
    def bold(x): return x
    class Icons:
        LOCK = "🔒"
        WARNING = "⚠️"

class PermissionManager:
    """Manages permission requests for all Codey operations"""

    def __init__(self, config):
        self.config = config
        self.auto_approve = False  # Can be toggled for batch operations

    def request_file_creation(self, filename: str, preview: str = None) -> bool:
        """Request permission to create a file"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold('Create file?')}")
        print(f"   Filename: {info(filename)}")
        if preview:
            print(f"   Preview:\n{self._format_preview(preview)}")
        return self._get_confirmation()

    def request_file_edit(self, filename: str, preview: str = None, backup_path: str = None) -> bool:
        """Request permission to edit a file"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold('Edit file?')}")
        print(f"   Filename: {info(filename)}")
        if backup_path:
            print(f"   Backup will be created: {info(backup_path)}")
        if preview:
            print(f"   Preview:\n{self._format_preview(preview)}")
        return self._get_confirmation()

    def request_file_deletion(self, filename: str, backup_path: str = None) -> bool:
        """Request permission to delete a file"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold('Delete file?')}")
        print(f"   Filename: {info(filename)}")
        if backup_path:
            print(f"   Backup will be created: {info(backup_path)}")
        print(f"   {warning(f'{Icons.WARNING} This action cannot be easily undone!')}")
        return self._get_confirmation()

    def request_shell_command(self, command: str, description: str = None) -> bool:
        """Request permission to execute a shell command"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold('Execute shell command?')}")
        print(f"   Command: {info(command)}")
        if description:
            print(f"   Purpose: {description}")
        return self._get_confirmation()

    def request_git_clone(self, repo_url: str, destination: str) -> bool:
        """Request permission to clone a git repository"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold('Clone repository?')}")
        print(f"   Repository: {info(repo_url)}")
        print(f"   Destination: {info(destination)}")
        return self._get_confirmation()

    def request_git_commit(self, message: str, files: List[str]) -> bool:
        """Request permission to create a git commit"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold('Create git commit?')}")
        print(f"   Message: {info(message)}")
        print(f"   Files: {len(files)} file(s)")
        if len(files) <= 5:
            for f in files:
                print(f"     - {f}")
        else:
            for f in files[:5]:
                print(f"     - {f}")
            print(f"     ... and {len(files) - 5} more")
        return self._get_confirmation()

    def request_git_push(self, branch: str, remote: str = "origin") -> bool:
        """Request permission to push to remote repository"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold('Push to remote repository?')}")
        print(f"   Remote: {info(remote)}")
        print(f"   Branch: {info(branch)}")
        print(f"   {warning(f'{Icons.WARNING} This will modify the remote repository!')}")
        return self._get_confirmation()

    def request_dependency_install(self, packages: List[str], file: str = None) -> bool:
        """Request permission to install dependencies"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold('Install Python packages?')}")
        if file:
            print(f"   From: {info(file)}")
        print(f"   Packages: {len(packages)} package(s)")
        if len(packages) <= 10:
            for pkg in packages:
                print(f"     - {pkg}")
        else:
            for pkg in packages[:10]:
                print(f"     - {pkg}")
            print(f"     ... and {len(packages) - 10} more")
        return self._get_confirmation()

    def request_directory_creation(self, directory: str) -> bool:
        """Request permission to create a directory"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold('Create directory?')}")
        print(f"   Directory: {info(directory)}")
        return self._get_confirmation()

    def request_multiple_file_operation(self, operation: str, files: List[str]) -> bool:
        """Request permission for operations affecting multiple files"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold(f'{operation}?')}")
        print(f"   Files affected: {len(files)}")
        if len(files) <= 5:
            for f in files:
                print(f"     - {f}")
        else:
            for f in files[:5]:
                print(f"     - {f}")
            print(f"     ... and {len(files) - 5} more")
        return self._get_confirmation()

    def request_custom_operation(self, title: str, details: Dict[str, Any]) -> bool:
        """Request permission for a custom operation"""
        print(f"\n{permission(f'{Icons.LOCK} Permission required:')} {bold(f'{title}?')}")
        for key, value in details.items():
            print(f"   {key}: {info(str(value))}")
        return self._get_confirmation()

    def _get_confirmation(self) -> bool:
        """Get user confirmation"""
        if self.auto_approve:
            print("   [Auto-approved]")
            return True

        try:
            response = input("\n   Proceed? [y/n]: ").strip().lower()
            return response in ['y', 'yes']
        except (KeyboardInterrupt, EOFError):
            print("\n   Operation cancelled.")
            return False

    def _format_preview(self, content: str, max_lines: int = 10) -> str:
        """Format content preview"""
        lines = content.split('\n')
        if len(lines) <= max_lines:
            return '\n'.join(f"     {line}" for line in lines)
        else:
            preview_lines = lines[:max_lines]
            preview = '\n'.join(f"     {line}" for line in preview_lines)
            return f"{preview}\n     ... ({len(lines) - max_lines} more lines)"

    def enable_auto_approve(self):
        """Enable auto-approval for batch operations"""
        self.auto_approve = True
        print("⚠️  Auto-approval enabled. All operations will proceed without confirmation.")

    def disable_auto_approve(self):
        """Disable auto-approval"""
        self.auto_approve = False
        print("✓ Auto-approval disabled. Confirmations required.")

    def request_batch_operation(self, operation_name: str, count: int) -> bool:
        """Request permission for batch operations"""
        print(f"\n🔒 Permission required: Batch operation")
        print(f"   Operation: {operation_name}")
        print(f"   Count: {count} operations")
        print("\n   Options:")
        print("     y - Approve all (auto-approve mode)")
        print("     a - Ask for each operation individually")
        print("     n - Cancel")

        try:
            response = input("\n   Choice [y/a/n]: ").strip().lower()
            if response in ['y', 'yes']:
                self.enable_auto_approve()
                return True
            elif response == 'a':
                return True
            else:
                return False
        except (KeyboardInterrupt, EOFError):
            print("\n   Operation cancelled.")
            return False
