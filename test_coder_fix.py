#!/usr/bin/env python3
"""Quick test to verify coder generation fix"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from models.lifecycle import ModelLifecycleManager, ModelRole
from models.coder import PrimaryCoder, CodingTask

def test_simple_generation():
    """Test simple code generation"""
    print("=" * 60)
    print("Testing Simple Code Generation Fix")
    print("=" * 60)

    # Load config
    config = Config()

    # Create lifecycle manager
    lifecycle = ModelLifecycleManager(config)

    try:
        # Load coder model
        print("\n1. Loading Qwen2.5-Coder model...")
        coder_model = lifecycle.ensure_loaded(ModelRole.CODER)
        print("✓ Model loaded successfully")

        # Create PrimaryCoder instance
        coder = PrimaryCoder(coder_model.model_path, coder_model.config)
        coder._model = coder_model._model
        coder._loaded = coder_model._loaded

        # Create simple task
        print("\n2. Creating test task...")
        task = CodingTask(
            task_type="create",
            target_files=["calculator.py"],
            instructions="Create functions for add, subtract, multiply, and divide",
            language="python"
        )
        print(f"   Task: {task.task_type} - {task.instructions}")

        # Generate code
        print("\n3. Generating code (with 30s timeout)...")
        result = coder.generate_code(task)

        # Display result
        print("\n" + "=" * 60)
        print("RESULT:")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Needs algo specialist: {result.needs_algorithm_specialist}")

        if result.error:
            print(f"Error: {result.error}")
            return False

        if result.code:
            print("\nGenerated Code:")
            for filename, code in result.code.items():
                print(f"\n--- {filename} ---")
                print(code[:500])  # First 500 chars
                if len(code) > 500:
                    print(f"... ({len(code) - 500} more characters)")

        if result.explanation:
            print(f"\nExplanation: {result.explanation[:200]}")

        print("\n✅ Test PASSED - Generation completed without hanging!")
        return True

    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print("\n4. Cleaning up...")
        lifecycle.unload_all()
        print("✓ Cleanup complete")

if __name__ == "__main__":
    success = test_simple_generation()
    sys.exit(0 if success else 1)
