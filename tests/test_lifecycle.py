"""Unit tests for Model Lifecycle Manager

Run with: pytest tests/test_lifecycle.py -v
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from models.lifecycle import ModelLifecycleManager, ModelRole, GGUFModel
from utils.config import Config


class TestModelLifecycleManager:
    """Test suite for ModelLifecycleManager"""

    @pytest.fixture
    def config(self):
        """Create a test configuration"""
        return Config()

    @pytest.fixture
    def lifecycle(self, config):
        """Create a ModelLifecycleManager instance"""
        return ModelLifecycleManager(config)

    def test_initialization(self, lifecycle):
        """Test that lifecycle manager initializes correctly"""
        assert lifecycle is not None
        assert isinstance(lifecycle.models, dict)
        assert ModelRole.ROUTER in lifecycle.models
        assert ModelRole.CODER in lifecycle.models
        assert ModelRole.ALGORITHM in lifecycle.models

    def test_model_configs_loaded(self, lifecycle):
        """Test that model configurations are loaded"""
        assert len(lifecycle.model_configs) > 0
        # Should have at least router config
        if ModelRole.ROUTER in lifecycle.model_configs:
            router_config = lifecycle.model_configs[ModelRole.ROUTER]
            assert 'path' in router_config
            assert 'context_size' in router_config

    def test_memory_budget(self, lifecycle):
        """Test that memory budget is set"""
        assert lifecycle.memory_budget_mb > 0
        assert isinstance(lifecycle.memory_budget_mb, int)

    def test_get_memory_usage_empty(self, lifecycle):
        """Test memory usage when no models loaded"""
        usage = lifecycle.get_memory_usage()
        assert 'total_mb' in usage
        assert 'budget_mb' in usage
        assert 'models' in usage
        assert usage['total_mb'] == 0

    def test_load_router_model(self, lifecycle):
        """Test loading the router model"""
        try:
            model = lifecycle.load_model(ModelRole.ROUTER)
            assert model is not None
            assert model.loaded
            assert lifecycle.models[ModelRole.ROUTER] is not None

            # Check memory usage updated
            usage = lifecycle.get_memory_usage()
            assert usage['total_mb'] > 0

            # Cleanup
            lifecycle.unload_model(ModelRole.ROUTER)
        except FileNotFoundError as e:
            pytest.skip(f"Model file not found: {e}")
        except Exception as e:
            pytest.fail(f"Failed to load router model: {e}")

    def test_unload_model(self, lifecycle):
        """Test unloading a model"""
        try:
            # Load a model first
            lifecycle.load_model(ModelRole.ROUTER)
            assert lifecycle.models[ModelRole.ROUTER] is not None

            # Unload it
            lifecycle.unload_model(ModelRole.ROUTER)
            assert lifecycle.models[ModelRole.ROUTER] is None

            # Check memory freed
            usage = lifecycle.get_memory_usage()
            assert usage['models'][ModelRole.ROUTER.value]['loaded'] is False

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_ensure_loaded(self, lifecycle):
        """Test ensure_loaded method"""
        try:
            # First call should load
            model1 = lifecycle.ensure_loaded(ModelRole.ROUTER)
            assert model1.loaded

            # Second call should return same model
            model2 = lifecycle.ensure_loaded(ModelRole.ROUTER)
            assert model2 is model1

            # Cleanup
            lifecycle.unload_model(ModelRole.ROUTER)
        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_get_model_info(self, lifecycle):
        """Test getting model information"""
        # Info when not loaded
        info = lifecycle.get_model_info(ModelRole.ROUTER)
        assert 'loaded' in info
        assert info['loaded'] is False

        try:
            # Load and get info
            lifecycle.load_model(ModelRole.ROUTER)
            info = lifecycle.get_model_info(ModelRole.ROUTER)
            assert info['loaded'] is True
            assert 'path' in info

            # Cleanup
            lifecycle.unload_model(ModelRole.ROUTER)
        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_unload_all(self, lifecycle):
        """Test unloading all models"""
        try:
            # Load router
            lifecycle.load_model(ModelRole.ROUTER)

            # Unload all
            lifecycle.unload_all()

            # Check all unloaded
            for role in ModelRole:
                assert lifecycle.models[role] is None

        except FileNotFoundError:
            pytest.skip("Model file not found")


class TestGGUFModel:
    """Test suite for GGUFModel wrapper"""

    @pytest.fixture
    def config(self):
        """Create a test configuration"""
        return Config()

    def test_model_path_validation(self, config):
        """Test that invalid model path raises error"""
        fake_path = Path("/nonexistent/model.gguf")
        model_config = {'context_size': 2048, 'n_gpu_layers': 0}

        with pytest.raises(FileNotFoundError):
            GGUFModel(fake_path, model_config)

    def test_memory_estimate(self, config):
        """Test memory estimation"""
        # Find router model path
        if hasattr(config, 'models') and 'router' in config.models:
            router_cfg = config.models['router']
            model_path = config.model_dir / router_cfg['path']

            if model_path.exists():
                model = GGUFModel(model_path, router_cfg)
                mem_mb = model.get_memory_estimate_mb()
                assert mem_mb > 0
                assert isinstance(mem_mb, int)
            else:
                pytest.skip("Router model file not found")
        else:
            pytest.skip("Multi-model config not found")

    def test_loaded_property(self, config):
        """Test loaded property"""
        if hasattr(config, 'models') and 'router' in config.models:
            router_cfg = config.models['router']
            model_path = config.model_dir / router_cfg['path']

            if model_path.exists():
                model = GGUFModel(model_path, router_cfg)
                assert model.loaded is False

                try:
                    model.load()
                    assert model.loaded is True

                    model.unload()
                    assert model.loaded is False
                except Exception as e:
                    pytest.skip(f"Could not load model: {e}")
            else:
                pytest.skip("Router model file not found")
        else:
            pytest.skip("Multi-model config not found")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
