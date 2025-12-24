"""Abstract base class for all model wrappers"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
import gc


class BaseModel(ABC):
    """Abstract base for all model wrappers

    This class defines the interface that all model implementations must follow.
    It provides common functionality for loading, unloading, and generating text.
    """

    def __init__(self, model_path: Path, config: Dict[str, Any]):
        """Initialize the base model

        Args:
            model_path: Path to the GGUF model file
            config: Model-specific configuration dictionary
        """
        self.model_path = Path(model_path)
        self.config = config
        self._model = None
        self._loaded = False

        # Validate model path exists
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

    @abstractmethod
    def load(self) -> None:
        """Load model into memory

        Implementations should:
        - Load the GGUF model using llama-cpp-python
        - Set self._model to the loaded model instance
        - Set self._loaded = True
        - Apply model-specific optimizations (GPU layers, threads, etc.)
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload model from memory

        Implementations should:
        - Delete the model instance
        - Set self._model = None
        - Set self._loaded = False
        - Force garbage collection to free RAM
        """
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt

        Args:
            prompt: Input text prompt
            **kwargs: Model-specific generation parameters
                     (temperature, max_tokens, stop sequences, etc.)

        Returns:
            Generated text string

        Raises:
            RuntimeError: If model is not loaded
        """
        pass

    @property
    def loaded(self) -> bool:
        """Check if model is currently loaded in memory"""
        return self._loaded

    def get_memory_estimate_mb(self) -> int:
        """Estimate memory usage for this model

        Returns rough estimate based on quantization and parameter count.
        Override in subclasses for more accurate estimates.

        Returns:
            Estimated memory usage in MB
        """
        if not self.model_path.exists():
            return 0

        # Rough estimate: file size * 1.2 (for overhead)
        file_size_mb = self.model_path.stat().st_size / (1024 * 1024)
        return int(file_size_mb * 1.2)

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model

        Returns:
            Dictionary with model metadata
        """
        return {
            'loaded': self._loaded,
            'path': str(self.model_path),
            'size_mb': self.get_memory_estimate_mb(),
            'config': self.config,
        }

    def _ensure_loaded(self) -> None:
        """Internal helper to ensure model is loaded before generation

        Raises:
            RuntimeError: If model is not loaded
        """
        if not self._loaded:
            raise RuntimeError(
                f"Model not loaded. Call load() before generate(). "
                f"Model: {self.model_path.name}"
            )

    def __repr__(self) -> str:
        """String representation of model"""
        status = "loaded" if self._loaded else "not loaded"
        return f"{self.__class__.__name__}({self.model_path.name}, {status})"
