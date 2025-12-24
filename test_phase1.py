#!/usr/bin/env python3
"""Phase 1 Integration Test - Multi-Model Lifecycle Management

This script tests the complete Phase 1 implementation:
- Loading all three models (router, coder, algorithm)
- Generating text with each model
- Unloading models correctly
- Memory budget enforcement

Run with: python3 test_phase1.py
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from models.lifecycle import ModelLifecycleManager, ModelRole


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_memory_usage(lifecycle):
    """Print current memory usage"""
    usage = lifecycle.get_memory_usage()
    print(f"\n📊 Memory Usage:")
    print(f"   Total: {usage['total_mb']:.0f} MB / {usage['budget_mb']} MB")
    print(f"   Utilization: {usage['utilization_percent']:.1f}%")
    print(f"   Available: {usage['available_mb']:.0f} MB")
    print(f"\n   Per Model:")
    for role, info in usage['models'].items():
        if info['loaded']:
            print(f"     ✓ {role:12s}: {info['memory_mb']:.0f} MB ({info['path']})")
        else:
            print(f"     ○ {role:12s}: not loaded")


def test_router_model(lifecycle):
    """Test the router model (FunctionGemma 270M)"""
    print_section("TEST 1: Router Model (FunctionGemma 270M)")

    print("Loading router model...")
    try:
        model = lifecycle.load_model(ModelRole.ROUTER)
        print(f"✓ Router loaded: {model.model_path.name}")

        print_memory_usage(lifecycle)

        # Test generation
        print("\nGenerating test output...")
        prompt = "Classify this intent: create a file called test.py"
        response = model.generate(prompt, max_tokens=50)
        print(f"\nPrompt: {prompt}")
        print(f"Response: {response[:200]}...")

        return True

    except FileNotFoundError as e:
        print(f"✗ Router model not found: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_coder_model(lifecycle):
    """Test the primary coder model (Qwen2.5-Coder 7B)"""
    print_section("TEST 2: Primary Coder Model (Qwen2.5-Coder 7B)")

    print("Loading coder model...")
    try:
        model = lifecycle.load_model(ModelRole.CODER)
        print(f"✓ Coder loaded: {model.model_path.name}")

        print_memory_usage(lifecycle)

        # Test generation
        print("\nGenerating test code...")
        prompt = """Write a simple Python function to add two numbers.

def add(a, b):"""
        response = model.generate(prompt, max_tokens=100, temperature=0.2)
        print(f"\nPrompt: {prompt}")
        print(f"Response: {response[:300]}...")

        return True

    except FileNotFoundError as e:
        print(f"✗ Coder model not found: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_algorithm_model(lifecycle):
    """Test the algorithm specialist (DeepSeek-Coder 6.7B)"""
    print_section("TEST 3: Algorithm Specialist (DeepSeek-Coder 6.7B)")

    print("Loading algorithm specialist...")
    try:
        model = lifecycle.load_model(ModelRole.ALGORITHM)
        print(f"✓ Algorithm specialist loaded: {model.model_path.name}")

        print_memory_usage(lifecycle)

        # Test generation
        print("\nGenerating test algorithm...")
        prompt = """Implement binary search in Python:

def binary_search(arr, target):"""
        response = model.generate(prompt, max_tokens=150, temperature=0.2)
        print(f"\nPrompt: {prompt}")
        print(f"Response: {response[:300]}...")

        return True

    except FileNotFoundError as e:
        print(f"✗ Algorithm model not found: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_model_swapping(lifecycle):
    """Test loading and unloading models (memory management)"""
    print_section("TEST 4: Model Swapping & Memory Management")

    print("Testing LRU unloading strategy...")

    try:
        # Load router (always resident)
        print("\n1. Loading router (always-resident)...")
        lifecycle.load_model(ModelRole.ROUTER)
        print_memory_usage(lifecycle)

        # Load coder
        print("\n2. Loading coder...")
        lifecycle.load_model(ModelRole.CODER)
        print_memory_usage(lifecycle)

        # Load algorithm (should trigger unloading if memory tight)
        print("\n3. Loading algorithm specialist (may trigger LRU unload)...")
        lifecycle.load_model(ModelRole.ALGORITHM)
        print_memory_usage(lifecycle)

        # Manually unload coder
        print("\n4. Manually unloading coder...")
        lifecycle.unload_model(ModelRole.CODER)
        print_memory_usage(lifecycle)

        # Unload all
        print("\n5. Unloading all models...")
        lifecycle.unload_all()
        print_memory_usage(lifecycle)

        return True

    except Exception as e:
        print(f"✗ Error during model swapping: {e}")
        return False


def test_backward_compatibility(lifecycle):
    """Test that legacy ModelManager still works"""
    print_section("TEST 5: Backward Compatibility (Legacy ModelManager)")

    try:
        from models.manager import ModelManager
        from utils.config import config

        print("Creating legacy ModelManager...")
        manager = ModelManager(config)

        print("Loading model via legacy interface...")
        manager.load_model()

        print("Testing legacy generate()...")
        response = manager.generate("def hello():", max_tokens=50)
        print(f"✓ Legacy generation works: {response[:100]}...")

        print("\nUnloading via legacy interface...")
        manager.unload_model()

        print("✓ Backward compatibility verified")
        return True

    except Exception as e:
        print(f"✗ Legacy compatibility error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 1 tests"""
    print("\n" + "=" * 70)
    print("  PHASE 1 INTEGRATION TEST")
    print("  Multi-Model Architecture - Model Lifecycle Manager")
    print("=" * 70)

    # Load configuration
    print("\nLoading configuration...")
    try:
        config = Config()
        print(f"✓ Config loaded")
        print(f"  Model directory: {config.model_dir}")
        print(f"  Memory budget: {getattr(config, 'memory_budget_mb', 6000)} MB")
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return 1

    # Create lifecycle manager
    print("\nCreating ModelLifecycleManager...")
    try:
        lifecycle = ModelLifecycleManager(config)
        print("✓ Lifecycle manager created")
    except Exception as e:
        print(f"✗ Failed to create lifecycle manager: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Run tests
    results = {}
    results['router'] = test_router_model(lifecycle)
    results['coder'] = test_coder_model(lifecycle)
    results['algorithm'] = test_algorithm_model(lifecycle)
    results['swapping'] = test_model_swapping(lifecycle)
    results['backward_compat'] = test_backward_compatibility(lifecycle)

    # Summary
    print_section("TEST SUMMARY")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {total} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if failed == 0:
        print("\n" + "=" * 70)
        print("  🎉 ALL TESTS PASSED - PHASE 1 COMPLETE!")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print(f"  ⚠️  {failed} TEST(S) FAILED - CHECK ERRORS ABOVE")
        print("=" * 70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
