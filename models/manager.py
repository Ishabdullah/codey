"""Model management and loading for Codey - Optimized for S24 Ultra

LEGACY WRAPPER: This class now delegates to ModelLifecycleManager for
backward compatibility. New code should use ModelLifecycleManager directly.
"""
import sys
import warnings
from pathlib import Path

try:
    from llama_cpp import Llama
except ImportError:
    print("Error: llama-cpp-python not installed.")
    print("Install it with: pip install llama-cpp-python")
    sys.exit(1)


class ModelManager:
    """Manages loading and interaction with GGUF models via llama.cpp

    LEGACY WRAPPER: This class delegates to ModelLifecycleManager for
    backward compatibility with existing code.

    For new code, use:
        from models.lifecycle import ModelLifecycleManager, ModelRole
        lifecycle = ModelLifecycleManager(config)
        model = lifecycle.load_model(ModelRole.CODER)
    """

    def __init__(self, config):
        self.config = config
        self.model = None
        self.model_loaded = False
        self.model_info = {}

        # Check if new multi-model config exists
        if hasattr(config, 'models') and config.models:
            # Use new lifecycle manager
            from models.lifecycle import ModelLifecycleManager, ModelRole
            self._lifecycle = ModelLifecycleManager(config)
            self._default_role = ModelRole.CODER
            self._use_lifecycle = True
            print("ModelManager: Using ModelLifecycleManager backend")
        else:
            # Legacy mode - use old single-model loading
            self._lifecycle = None
            self._use_lifecycle = False
            print("ModelManager: Using legacy single-model backend")

    def load_model(self):
        """Load the GGUF model into memory with optimizations"""
        # If using lifecycle manager, delegate to it
        if self._use_lifecycle:
            model_obj = self._lifecycle.load_model(self._default_role)
            self.model = model_obj._model  # Access underlying llama.cpp model
            self.model_loaded = model_obj.loaded
            self.model_info = model_obj.get_model_info()
            return self.model

        # Legacy loading path
        if self.model_loaded:
            return self.model

        model_path = self.config.model_path

        if not model_path.exists():
            # Provide helpful error message with suggestions
            error_msg = f"\n❌ Model not found: {model_path.name}\n"
            error_msg += "─" * 60 + "\n"
            error_msg += f"Expected location: {model_path}\n"
            error_msg += f"\n💡 Suggestions:\n"
            error_msg += f"  1. Check that the model file exists in: {self.config.model_dir}/\n"
            error_msg += f"  2. Verify the model name in config.json (active profile: {self.config.active_profile_name})\n"
            error_msg += f"  3. Download a GGUF model from HuggingFace (e.g., TheBloke models)\n"
            error_msg += f"  4. Try switching to a different profile in config.json\n"
            error_msg += "─" * 60
            raise FileNotFoundError(error_msg)

        # Show profile info
        profile_info = self.config.get_profile_info()
        print(f"Loading model from {model_path}...")
        print(f"Profile: {profile_info['name']} - {profile_info['description']}")

        try:
            # Optimized parameters for S24 Ultra
            # Use full context window if available
            n_ctx = self.config.context_size

            # GPU layers optimization for mobile GPU
            # S24 Ultra has Snapdragon 8 Gen 3 with Adreno 750 GPU
            n_gpu_layers = self.config.n_gpu_layers
            if n_gpu_layers == 0:
                # Auto-detect: Use GPU layers for 7B model on S24 Ultra
                n_gpu_layers = 35  # Optimal for 7B models on mobile
                print(f"Auto-detected GPU: offloading {n_gpu_layers} layers to GPU")

            # Thread optimization for Snapdragon 8 Gen 3 (1x3.3GHz + 3x3.2GHz + 2x3.0GHz + 2x2.3GHz)
            n_threads = self.config.n_threads  # Use performance cores
            n_threads_batch = self.config.n_threads_batch

            self.model = Llama(
                model_path=str(model_path),
                n_ctx=n_ctx,  # Full context window
                n_gpu_layers=n_gpu_layers,  # GPU acceleration
                n_threads=n_threads,  # CPU threads
                n_threads_batch=n_threads_batch,  # Batch processing threads
                use_mmap=True,  # Memory-mapped file for efficient loading
                use_mlock=False,  # Don't lock memory (mobile optimization)
                n_batch=512,  # Batch size for processing
                verbose=False,
                rope_freq_base=0,  # Auto-detect from model
                rope_freq_scale=0,  # Auto-detect from model
            )

            self.model_loaded = True

            # Store model info
            self.model_info = {
                'path': str(model_path),
                'context_size': n_ctx,
                'gpu_layers': n_gpu_layers,
                'threads': n_threads,
                'batch_size': 512
            }

            print("Model loaded successfully!")
            print(f"Context window: {n_ctx} tokens")
            print(f"GPU layers: {n_gpu_layers}")
            print(f"CPU threads: {n_threads}")

            return self.model
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")

    def generate(self, prompt, temperature=None, max_tokens=None, stop=None):
        """Generate text from the model"""
        # If using lifecycle manager, delegate to it
        if self._use_lifecycle:
            model_obj = self._lifecycle.ensure_loaded(self._default_role)
            return model_obj.generate(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop
            )

        # Legacy generation path
        if not self.model_loaded:
            self.load_model()

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            result = self.model(
                prompt,
                max_tokens=max_tok,
                temperature=temp,
                stop=stop or ["</s>", "User:", "Human:"],
                echo=False
            )
            return result['choices'][0]['text'].strip()
        except Exception as e:
            raise RuntimeError(f"Generation failed: {e}")

    def get_model_info(self):
        """Get information about the loaded model"""
        # If using lifecycle manager, get info from it
        if self._use_lifecycle:
            return self._lifecycle.get_model_info(self._default_role)

        # Legacy info path
        if not self.model_loaded:
            return {'loaded': False}

        return {
            'loaded': True,
            **self.model_info
        }

    def unload_model(self):
        """Unload the model from memory"""
        # If using lifecycle manager, delegate to it
        if self._use_lifecycle:
            self._lifecycle.unload_model(self._default_role)
            self.model = None
            self.model_loaded = False
            self.model_info = {}
            return

        # Legacy unload path
        if self.model:
            del self.model
            self.model = None
            self.model_loaded = False
            self.model_info = {}
            print("Model unloaded from memory")
