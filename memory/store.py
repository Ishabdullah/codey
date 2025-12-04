"""Memory and context persistence for Codey"""
import json
from datetime import datetime
from pathlib import Path

class MemoryStore:
    """Persistent memory storage for conversation and file history"""

    def __init__(self, config):
        self.config = config
        self.memory_file = config.memory_dir / "memory.json"
        self.load_memory()

    def load_memory(self):
        """Load memory from disk or initialize"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                self.conversations = data.get('conversations', [])
                self.file_history = data.get('file_history', {})
                self.session_count = data.get('session_count', 0)
            except Exception as e:
                print(f"Warning: Could not load memory: {e}")
                self._initialize_memory()
        else:
            self._initialize_memory()

    def _initialize_memory(self):
        """Initialize empty memory"""
        self.conversations = []
        self.file_history = {}
        self.session_count = 0

    def save_memory(self):
        """Save memory to disk"""
        try:
            data = {
                'conversations': self.conversations[-50:],  # Keep last 50
                'file_history': self.file_history,
                'session_count': self.session_count,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save memory: {e}")

    def add_conversation(self, user_input, response, action=None):
        """Add a conversation exchange to memory"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user_input,
            'assistant': response,
            'action': action
        }
        self.conversations.append(entry)
        self.save_memory()

    def add_file_action(self, filepath, action_type, details=None):
        """Record a file action"""
        if filepath not in self.file_history:
            self.file_history[filepath] = []

        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action_type,
            'details': details or {}
        }
        self.file_history[filepath].append(entry)
        self.save_memory()

    def get_recent_context(self, n=5):
        """Get recent conversation context"""
        return self.conversations[-n:]

    def get_file_history(self, filepath):
        """Get history for a specific file"""
        return self.file_history.get(filepath, [])

    def start_session(self):
        """Increment session count"""
        self.session_count += 1
        self.save_memory()

    def clear_conversations(self):
        """Clear conversation history"""
        self.conversations = []
        self.save_memory()
