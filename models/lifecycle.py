"""Model Lifecycle Manager for multi-model support"""
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path
import gc
import time
from threading import Lock

try:
    from llama_cpp import Llama
except ImportError:
    print("Error: llama-cpp-python not installed.")
    print("Install it with: pip install llama-cpp-python")
    import sys
    sys.exit(1)

from models.base import BaseModel


class ModelRole(Enum):
    """Enum defining the role of each model in the system"""
    ROUTER = "router"           # Intent classification, always-resident
    CODER = "coder"            # Primary code generation, on-demand
    ALGORITHM = "algorithm"    # Algorithm specialist, cold-loaded


class GGUFModel(BaseModel):
    """Concrete implementation of BaseModel using llama-cpp-python

    This class wraps llama.cpp GGUF models and provides the standard interface
    defined by BaseModel.
    """

    def load(self) -> None:
        """Load GGUF model into memory"""
        if self._loaded:
            return  # Already loaded

        print(f"Loading {self.model_path.name}...")

        try:
            # Extract configuration
            n_ctx = self.config.get('context_size', 2048)
            n_gpu_layers = self.config.get('n_gpu_layers', 0)
            n_threads = self.config.get('n_threads', 4)
            n_threads_batch = self.config.get('n_threads_batch', n_threads)

            # Load model with llama.cpp
            self._model = Llama(
                model_path=str(self.model_path),
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                n_threads=n_threads,
                n_threads_batch=n_threads_batch,
                use_mmap=True,
                use_mlock=False,
                n_batch=512,
                verbose=False,
                rope_freq_base=0,  # Auto-detect
                rope_freq_scale=0,  # Auto-detect
            )

            self._loaded = True
            print(f"✓ Loaded {self.model_path.name}")
            print(f"  Context: {n_ctx} tokens, GPU layers: {n_gpu_layers}, Threads: {n_threads}")

        except Exception as e:
            self._loaded = False
            self._model = None
            raise RuntimeError(f"Failed to load model {self.model_path.name}: {e}")

    def unload(self) -> None:
        """Unload model from memory"""
        if not self._loaded:
            return  # Not loaded

        print(f"Unloading {self.model_path.name}...")

        if self._model is not None:
            del self._model
            self._model = None

        self._loaded = False

        # Force garbage collection to free memory
        gc.collect()

        print(f"✓ Unloaded {self.model_path.name}")

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt

        Args:
            prompt: Input text
            **kwargs: Generation parameters (temperature, max_tokens, stop, etc.)

        Returns:
            Generated text
        """
        self._ensure_loaded()

        # Extract generation parameters with defaults
        temperature = kwargs.get('temperature', self.config.get('temperature', 0.3))
        max_tokens = kwargs.get('max_tokens', self.config.get('max_tokens', 512))
        stop = kwargs.get('stop', ["</s>", "User:", "Human:"])

        try:
            result = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
                echo=False
            )
            return result['choices'][0]['text'].strip()

        except Exception as e:
            raise RuntimeError(f"Generation failed: {e}")


class ModelLifecycleManager:
    """Manages loading/unloading of multiple models with memory budgeting

    This is the central coordinator for all models in the system. It:
    - Loads models on-demand based on their role
    - Enforces memory budget limits
    - Unloads models using LRU (Least Recently Used) strategy
    - Tracks model usage for optimization
    """

    def __init__(self, config):
        """Initialize lifecycle manager

        Args:
            config: Configuration object with model settings
        """
        self.config = config
        self.models: Dict[ModelRole, Optional[GGUFModel]] = {
            ModelRole.ROUTER: None,
            ModelRole.CODER: None,
            ModelRole.ALGORITHM: None,
        }

        # Track last usage time for LRU unloading
        self._last_used: Dict[ModelRole, float] = {}

        # Thread safety for concurrent access (use RLock for reentrant locking)
        from threading import RLock
        self._lock = RLock()

        # Load model configurations from config
        self.model_configs = self._load_model_configs()

        # Memory budget in MB
        self.memory_budget_mb = getattr(config, 'memory_budget_mb', 6000)

        print(f"ModelLifecycleManager initialized")
        print(f"Memory budget: {self.memory_budget_mb} MB")

    def _load_model_configs(self) -> Dict[ModelRole, Dict[str, Any]]:
        """Load model configurations from config object

        Returns:
            Dictionary mapping ModelRole to configuration dict
        """
        configs = {}

        # Check if config has 'models' attribute (new format)
        if hasattr(self.config, 'models'):
            model_configs = self.config.models

            # Map config keys to ModelRole
            role_map = {
                'router': ModelRole.ROUTER,
                'coder': ModelRole.CODER,
                'algorithm': ModelRole.ALGORITHM,
            }

            for key, role in role_map.items():
                if key in model_configs:
                    cfg = model_configs[key]
                    # Build full path
                    model_path = self.config.model_dir / cfg['path']
                    configs[role] = {
                        'path': model_path,
                        'context_size': cfg.get('context_size', 2048),
                        'n_gpu_layers': cfg.get('n_gpu_layers', 0),
                        'n_threads': cfg.get('n_threads', 4),
                        'n_threads_batch': cfg.get('n_threads_batch', 4),
                        'temperature': cfg.get('temperature', 0.3),
                        'max_tokens': cfg.get('max_tokens', 512),
                        'always_resident': cfg.get('always_resident', False),
                        'unload_after_seconds': cfg.get('unload_after_seconds', 60),
                    }

        return configs

    def load_model(self, role: ModelRole) -> GGUFModel:
        """Load model for specified role

        Args:
            role: The ModelRole to load

        Returns:
            Loaded GGUFModel instance

        Raises:
            ValueError: If role configuration not found
            RuntimeError: If model fails to load
        """
        with self._lock:
            # Check if already loaded
            if self.models[role] is not None and self.models[role].loaded:
                self._last_used[role] = time.time()
                return self.models[role]

            # Get configuration
            if role not in self.model_configs:
                raise ValueError(f"No configuration found for role: {role.value}")

            config = self.model_configs[role]

            # Check memory budget
            required_mb = self._estimate_memory_requirement(config['path'])
            self._enforce_memory_limit(required_mb, exempt_role=role)

            # Create and load model
            model = GGUFModel(config['path'], config)
            model.load()

            self.models[role] = model
            self._last_used[role] = time.time()

            return model

    def unload_model(self, role: ModelRole) -> None:
        """Unload model for specified role

        Args:
            role: The ModelRole to unload
        """
        with self._lock:
            if self.models[role] is not None:
                self.models[role].unload()
                self.models[role] = None
                if role in self._last_used:
                    del self._last_used[role]

    def ensure_loaded(self, role: ModelRole) -> GGUFModel:
        """Ensure model is loaded, loading if necessary

        Args:
            role: The ModelRole to ensure is loaded

        Returns:
            Loaded GGUFModel instance
        """
        return self.load_model(role)

    def unload_all(self) -> None:
        """Unload all models"""
        print("Unloading all models...")
        for role in ModelRole:
            self.unload_model(role)

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage per model

        Returns:
            Dictionary with memory usage information
        """
        usage = {
            'total_mb': 0,
            'budget_mb': self.memory_budget_mb,
            'models': {}
        }

        for role, model in self.models.items():
            if model is not None and model.loaded:
                mem_mb = model.get_memory_estimate_mb()
                usage['models'][role.value] = {
                    'loaded': True,
                    'memory_mb': mem_mb,
                    'path': str(model.model_path.name)
                }
                usage['total_mb'] += mem_mb
            else:
                usage['models'][role.value] = {
                    'loaded': False,
                    'memory_mb': 0
                }

        usage['available_mb'] = self.memory_budget_mb - usage['total_mb']
        usage['utilization_percent'] = (usage['total_mb'] / self.memory_budget_mb * 100) if self.memory_budget_mb > 0 else 0

        return usage

    def _estimate_memory_requirement(self, model_path: Path) -> int:
        """Estimate memory required for a model

        Args:
            model_path: Path to model file

        Returns:
            Estimated memory in MB
        """
        if not model_path.exists():
            return 0

        # File size * 1.2 for overhead
        file_size_mb = model_path.stat().st_size / (1024 * 1024)
        return int(file_size_mb * 1.2)

    def _enforce_memory_limit(self, required_mb: int, exempt_role: Optional[ModelRole] = None) -> None:
        """Unload models to fit within memory budget

        Uses LRU (Least Recently Used) strategy to decide which models to unload.

        Args:
            required_mb: Memory required for new model
            exempt_role: Role that should not be unloaded (the one we're loading)
        """
        usage = self.get_memory_usage()
        current_mb = usage['total_mb']

        # Check if we fit within budget
        if current_mb + required_mb <= self.memory_budget_mb:
            return  # We're good

        print(f"Memory budget enforcement: Need {required_mb}MB, currently using {current_mb}MB")

        # Build list of candidates for unloading (LRU order)
        candidates = []
        for role, model in self.models.items():
            if model is None or not model.loaded:
                continue
            if role == exempt_role:
                continue

            # Never unload router if it's configured as always_resident
            config = self.model_configs.get(role, {})
            if config.get('always_resident', False):
                continue

            last_used = self._last_used.get(role, 0)
            candidates.append((last_used, role, model.get_memory_estimate_mb()))

        # Sort by least recently used first
        candidates.sort(key=lambda x: x[0])

        # Unload models until we fit
        for _, role, mem_mb in candidates:
            print(f"  Unloading {role.value} to free {mem_mb}MB")
            self.unload_model(role)
            current_mb -= mem_mb

            if current_mb + required_mb <= self.memory_budget_mb:
                break

        # Final check
        if current_mb + required_mb > self.memory_budget_mb:
            print(f"⚠️  Warning: May exceed memory budget ({current_mb + required_mb}MB > {self.memory_budget_mb}MB)")

    def get_model_info(self, role: ModelRole) -> Dict[str, Any]:
        """Get information about a specific model

        Args:
            role: The ModelRole to get info for

        Returns:
            Dictionary with model information
        """
        model = self.models.get(role)
        if model is None:
            return {
                'role': role.value,
                'loaded': False,
                'config': self.model_configs.get(role, {})
            }

        return {
            'role': role.value,
            'loaded': model.loaded,
            **model.get_model_info()
        }
