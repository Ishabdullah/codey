"""Structured logging for shell command decisions"""
import json
from datetime import datetime
from pathlib import Path

class CommandLogger:
    """Logs command approvals, denials, and executions"""

    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "command_decisions.log"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_command(self, command: str, decision: str, classification: str,
                   cwd: str = None, error: str = None):
        """Log a command decision"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'decision': decision,  # 'approved', 'denied', 'forbidden', 'executed', 'failed'
            'classification': classification,  # 'safe', 'risky', 'forbidden'
            'cwd': cwd,
            'error': error
        }

        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            # Don't fail if logging fails
            pass

    def get_recent_logs(self, n: int = 10) -> list:
        """Get recent command logs"""
        if not self.log_file.exists():
            return []

        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                recent = lines[-n:] if len(lines) > n else lines
                return [json.loads(line) for line in recent]
        except Exception:
            return []
