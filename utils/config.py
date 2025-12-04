"""Configuration management for Codey"""
import os
import json
from pathlib import Path

class Config:
    """Centralized configuration for Codey"""

    def __init__(self):
        self.codey_dir = Path.home() / "codey"
        self.config_file = self.codey_dir / "config.json"
        self.load_config()

    def load_config(self):
        """Load configuration from file or create defaults"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
        else:
            config_data = self.default_config()
            self.save_config(config_data)

        # Set attributes
        self.model_dir = Path(config_data.get('model_dir', str(self.codey_dir / 'LLM_Models')))
        self.model_name = config_data.get('model_name', 'CodeLlama-7B-Instruct.Q4_K_M.gguf')
        self.memory_dir = Path(config_data.get('memory_dir', str(self.codey_dir / 'memory')))
        self.log_dir = Path(config_data.get('log_dir', str(self.codey_dir / 'logs')))
        self.workspace_dir = Path(config_data.get('workspace_dir', str(self.codey_dir / 'workspace')))

        # Model parameters
        self.temperature = config_data.get('temperature', 0.3)
        self.max_tokens = config_data.get('max_tokens', 2048)
        self.context_size = config_data.get('context_size', 4096)
        self.n_gpu_layers = config_data.get('n_gpu_layers', 0)  # CPU only by default
        self.n_threads = config_data.get('n_threads', 6)
        self.n_threads_batch = config_data.get('n_threads_batch', 6)

        # Safety settings
        self.require_confirmation = config_data.get('require_confirmation', True)
        self.backup_before_edit = config_data.get('backup_before_edit', True)
        self.auto_backup = config_data.get('auto_backup', True)

        # Perplexity API settings
        self.perplexity_api_key = config_data.get('perplexity_api_key', '')
        self.use_perplexity = config_data.get('use_perplexity', True)
        self.hybrid_mode = config_data.get('hybrid_mode', True)

        # Feature toggles
        self.git_enabled = config_data.get('git_enabled', True)
        self.shell_enabled = config_data.get('shell_enabled', True)

        # Ensure directories exist
        for d in [self.model_dir, self.memory_dir, self.log_dir, self.workspace_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def default_config(self):
        """Return default configuration"""
        return {
            'model_dir': str(self.codey_dir / 'LLM_Models'),
            'model_name': 'CodeLlama-7B-Instruct.Q4_K_M.gguf',
            'memory_dir': str(self.codey_dir / 'memory'),
            'log_dir': str(self.codey_dir / 'logs'),
            'workspace_dir': str(self.codey_dir / 'workspace'),
            'temperature': 0.3,
            'max_tokens': 2048,
            'context_size': 4096,
            'n_gpu_layers': 0,
            'require_confirmation': True,
            'backup_before_edit': True,
            'perplexity_api_key': '',
            'use_perplexity': True,
            'hybrid_mode': True
        }

    def save_config(self, config_data=None):
        """Save current configuration to file"""
        if config_data is None:
            config_data = {
                'model_dir': str(self.model_dir),
                'model_name': self.model_name,
                'memory_dir': str(self.memory_dir),
                'log_dir': str(self.log_dir),
                'workspace_dir': str(self.workspace_dir),
                'temperature': self.temperature,
                'max_tokens': self.max_tokens,
                'context_size': self.context_size,
                'n_gpu_layers': self.n_gpu_layers,
                'require_confirmation': self.require_confirmation,
                'backup_before_edit': self.backup_before_edit,
                'perplexity_api_key': self.perplexity_api_key,
                'use_perplexity': self.use_perplexity,
                'hybrid_mode': self.hybrid_mode
            }

        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

    @property
    def model_path(self):
        """Get full path to the model file"""
        return self.model_dir / self.model_name

# Global config instance
config = Config()
