"""Configuration management for Codey - Enhanced with model profiles (v2.1)"""
import os
import json
from pathlib import Path

class Config:
    """Centralized configuration for Codey with model profile support"""

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

        # Check for model_profiles (v2.1+)
        if 'model_profiles' in config_data:
            self._load_with_profiles(config_data)
        else:
            # Backward compatibility: migrate old config
            print("⚠️  Old config format detected. Migrating to model profiles...")
            self._migrate_old_config(config_data)

        # Set directories
        self.model_dir = Path(config_data.get('model_dir', str(self.codey_dir / 'LLM_Models')))
        self.memory_dir = Path(config_data.get('memory_dir', str(self.codey_dir / 'memory')))
        self.log_dir = Path(config_data.get('log_dir', str(self.codey_dir / 'logs')))
        self.workspace_dir = Path(config_data.get('workspace_dir', str(self.codey_dir / 'workspace')))

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

        # Shell safety settings (v2.1)
        self.shell_safety = config_data.get('shell_safety', {
            'enable_dangerous_commands': False,
            'log_command_decisions': True,
            'require_preview_for_risky': True
        })

        # Performance settings (v2.1)
        self.performance = config_data.get('performance', {
            'streaming_enabled': False,
            'lightweight_mode': False,
            'auto_detect_device': True
        })

        # Ensure directories exist
        for d in [self.model_dir, self.memory_dir, self.log_dir, self.workspace_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _load_with_profiles(self, config_data):
        """Load configuration using model profiles (v2.1+)"""
        self.model_profiles = config_data.get('model_profiles', {})
        self.active_profile_name = config_data.get('active_model_profile', 's24_ultra_default')

        # Get active profile
        if self.active_profile_name not in self.model_profiles:
            print(f"⚠️  Profile '{self.active_profile_name}' not found. Falling back to first available profile.")
            if self.model_profiles:
                self.active_profile_name = list(self.model_profiles.keys())[0]
            else:
                print("❌ No model profiles defined! Using defaults.")
                self._create_default_profile()

        # Load active profile settings
        profile = self.model_profiles.get(self.active_profile_name, {})
        self.model_name = profile.get('model_name', 'CodeLlama-7B-Instruct.Q4_K_M.gguf')
        self.context_size = profile.get('context_size', 4096)
        self.n_gpu_layers = profile.get('n_gpu_layers', 0)
        self.n_threads = profile.get('n_threads', 4)
        self.n_threads_batch = profile.get('n_threads_batch', 4)
        self.temperature = profile.get('temperature', 0.3)
        self.max_tokens = profile.get('max_tokens', 2048)
        self.profile_description = profile.get('description', 'No description')

    def _migrate_old_config(self, config_data):
        """Migrate old config format to new profile-based format"""
        # Create a profile from old settings
        old_profile = {
            'model_name': config_data.get('model_name', 'CodeLlama-7B-Instruct.Q4_K_M.gguf'),
            'context_size': config_data.get('context_size', 4096),
            'n_gpu_layers': config_data.get('n_gpu_layers', 0),
            'n_threads': config_data.get('n_threads', 4),
            'n_threads_batch': config_data.get('n_threads_batch', 4),
            'temperature': config_data.get('temperature', 0.3),
            'max_tokens': config_data.get('max_tokens', 2048),
            'description': 'Migrated from old config format'
        }

        # Create model_profiles
        self.model_profiles = {
            'migrated_profile': old_profile
        }
        self.active_profile_name = 'migrated_profile'

        # Set attributes from migrated profile
        self.model_name = old_profile['model_name']
        self.context_size = old_profile['context_size']
        self.n_gpu_layers = old_profile['n_gpu_layers']
        self.n_threads = old_profile['n_threads']
        self.n_threads_batch = old_profile['n_threads_batch']
        self.temperature = old_profile['temperature']
        self.max_tokens = old_profile['max_tokens']
        self.profile_description = old_profile['description']

        print(f"✓ Migration complete. Active profile: {self.active_profile_name}")
        print("  Consider updating config.json with additional profiles!")

    def _create_default_profile(self):
        """Create a default fallback profile"""
        self.model_profiles = {
            'default': {
                'model_name': 'CodeLlama-7B-Instruct.Q4_K_M.gguf',
                'context_size': 4096,
                'n_gpu_layers': 0,
                'n_threads': 4,
                'n_threads_batch': 4,
                'temperature': 0.3,
                'max_tokens': 2048,
                'description': 'Default fallback profile'
            }
        }
        self.active_profile_name = 'default'
        profile = self.model_profiles['default']
        self.model_name = profile['model_name']
        self.context_size = profile['context_size']
        self.n_gpu_layers = profile['n_gpu_layers']
        self.n_threads = profile['n_threads']
        self.n_threads_batch = profile['n_threads_batch']
        self.temperature = profile['temperature']
        self.max_tokens = profile['max_tokens']
        self.profile_description = profile['description']

    def default_config(self):
        """Return default configuration with model profiles (v2.1)"""
        return {
            'model_profiles': {
                's24_ultra_default': {
                    'model_name': 'CodeLlama-7B-Instruct.Q4_K_M.gguf',
                    'context_size': 16384,
                    'n_gpu_layers': 35,
                    'n_threads': 6,
                    'n_threads_batch': 6,
                    'temperature': 0.3,
                    'max_tokens': 2048,
                    'description': 'Optimized for S24 Ultra with GPU acceleration'
                },
                'light_cpu_only': {
                    'model_name': 'CodeLlama-7B-Instruct.Q4_K_M.gguf',
                    'context_size': 4096,
                    'n_gpu_layers': 0,
                    'n_threads': 4,
                    'n_threads_batch': 4,
                    'temperature': 0.3,
                    'max_tokens': 1024,
                    'description': 'Lightweight CPU-only for low-end devices'
                }
            },
            'active_model_profile': 's24_ultra_default',
            'performance': {
                'streaming_enabled': False,
                'lightweight_mode': False,
                'auto_detect_device': True
            },
            'model_dir': str(self.codey_dir / 'LLM_Models'),
            'memory_dir': str(self.codey_dir / 'memory'),
            'log_dir': str(self.codey_dir / 'logs'),
            'workspace_dir': str(self.codey_dir / 'workspace'),
            'require_confirmation': True,
            'backup_before_edit': True,
            'perplexity_api_key': '',
            'use_perplexity': True,
            'hybrid_mode': True,
            'shell_safety': {
                'enable_dangerous_commands': False,
                'log_command_decisions': True,
                'require_preview_for_risky': True
            }
        }

    def save_config(self, config_data=None):
        """Save current configuration to file"""
        if config_data is None:
            config_data = {
                'model_profiles': self.model_profiles,
                'active_model_profile': self.active_profile_name,
                'performance': self.performance,
                'model_dir': str(self.model_dir),
                'memory_dir': str(self.memory_dir),
                'log_dir': str(self.log_dir),
                'workspace_dir': str(self.workspace_dir),
                'require_confirmation': self.require_confirmation,
                'backup_before_edit': self.backup_before_edit,
                'perplexity_api_key': self.perplexity_api_key,
                'use_perplexity': self.use_perplexity,
                'hybrid_mode': self.hybrid_mode,
                'shell_safety': self.shell_safety
            }

        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

    @property
    def model_path(self):
        """Get full path to the model file"""
        return self.model_dir / self.model_name

    def get_profile_info(self):
        """Get information about the active profile"""
        return {
            'name': self.active_profile_name,
            'description': self.profile_description,
            'model_name': self.model_name,
            'context_size': self.context_size,
            'gpu_layers': self.n_gpu_layers,
            'threads': self.n_threads,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }

# Global config instance
config = Config()
