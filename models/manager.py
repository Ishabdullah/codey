"""Model management and loading for Codey"""
import sys
from pathlib import Path

try:
    from llama_cpp import Llama
except ImportError:
    print("Error: llama-cpp-python not installed.")
    print("Install it with: pip install llama-cpp-python")
    sys.exit(1)

class ModelManager:
    """Manages loading and interaction with GGUF models via llama.cpp"""

    def __init__(self, config):
        self.config = config
        self.model = None
        self.model_loaded = False

    def load_model(self):
        """Load the GGUF model into memory"""
        if self.model_loaded:
            return self.model

        model_path = self.config.model_path

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}\n"
                f"Please place your GGUF model in {self.config.model_dir}/"
            )

        print(f"Loading model from {model_path}...")
        print("This may take a moment...")

        try:
            self.model = Llama(
                model_path=str(model_path),
                n_ctx=self.config.context_size,
                n_gpu_layers=self.config.n_gpu_layers,
                verbose=False
            )
            self.model_loaded = True
            print("Model loaded successfully!")
            return self.model
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")

    def generate(self, prompt, temperature=None, max_tokens=None, stop=None):
        """Generate text from the model"""
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

    def unload_model(self):
        """Unload the model from memory"""
        if self.model:
            del self.model
            self.model = None
            self.model_loaded = False
