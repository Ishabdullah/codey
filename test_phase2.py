#!/usr/bin/env python3
"""Phase 2 Integration Test - Intent Router & Tool Executor

This script tests the complete Phase 2 implementation:
- Intent classification with router model
- Tool execution without model loading
- Orchestrator coordination
- Fallback to regex when needed

Run with: python3 test_phase2.py
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from models.lifecycle import ModelLifecycleManager, ModelRole
from router.intent_router import IntentRouter, IntentResult
from executor.tool_executor import ToolExecutor
from core.orchestrator import Orchestrator
from core.git_manager import GitManager
from core.shell_manager import ShellManager
from core.tools import FileTools
from core.permission_manager import PermissionManager


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_intent_classification(router):
    """Test intent router classification"""
    print_section("TEST 1: Intent Classification")

    test_cases = [
        ("git status", "tool_call", "git"),
        ("list files", "tool_call", "file"),
        ("create a file test.py", "coding_task", None),
        ("implement quicksort", "algorithm_task", None),
        ("what is python?", "simple_answer", None),
    ]

    passed = 0
    failed = 0

    for user_input, expected_intent, expected_tool in test_cases:
        print(f"\nInput: '{user_input}'")
        try:
            result = router.classify(user_input)
            print(f"  Intent: {result.intent} (confidence: {result.confidence:.2f})")
            print(f"  Tool: {result.tool}")
            print(f"  Escalate to: {result.escalate_to}")
            print(f"  Used fallback: {result.used_fallback}")

            # Validate
            if result.intent == expected_intent:
                if expected_tool is None or result.tool == expected_tool:
                    print("  ✓ PASS")
                    passed += 1
                else:
                    print(f"  ✗ FAIL: Expected tool '{expected_tool}', got '{result.tool}'")
                    failed += 1
            else:
                print(f"  ✗ FAIL: Expected intent '{expected_intent}', got '{result.intent}'")
                failed += 1

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print(f"\nIntent Classification: {passed}/{passed+failed} tests passed")
    return passed == (passed + failed)


def test_tool_execution(tool_executor):
    """Test direct tool execution"""
    print_section("TEST 2: Tool Execution (Without Model)")

    passed = 0
    failed = 0

    # Test git status
    print("\nTest: Git Status")
    try:
        result = tool_executor.execute("git", {"action": "status"})
        if result.success:
            print(f"  ✓ PASS: git status executed")
            passed += 1
        else:
            print(f"  ✗ FAIL: {result.error}")
            failed += 1
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        failed += 1

    # Test file list
    print("\nTest: List Files")
    try:
        result = tool_executor.execute("file", {"raw_input": "list files"})
        if result.success:
            print(f"  ✓ PASS: file list executed")
            print(f"  Files: {len(result.output) if result.output else 0}")
            passed += 1
        else:
            print(f"  ✗ FAIL: {result.error}")
            failed += 1
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        failed += 1

    print(f"\nTool Execution: {passed}/{passed+failed} tests passed")
    return passed == (passed + failed)


def test_orchestrator(orchestrator):
    """Test orchestrator end-to-end"""
    print_section("TEST 3: Orchestrator Integration")

    passed = 0
    failed = 0

    test_cases = [
        "git status",
        "list files",
        "what is python?",
    ]

    for user_input in test_cases:
        print(f"\nInput: '{user_input}'")
        try:
            response = orchestrator.process(user_input)
            if response and len(response) > 0:
                print(f"  Response preview: {response[:100]}...")
                print(f"  ✓ PASS")
                passed += 1
            else:
                print(f"  ✗ FAIL: Empty response")
                failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\nOrchestrator: {passed}/{passed+failed} tests passed")
    return passed == (passed + failed)


def test_fallback_regex(router):
    """Test regex fallback when model fails"""
    print_section("TEST 4: Regex Fallback")

    # Test patterns that should trigger regex fallback
    test_cases = [
        "git log",
        "mkdir test_dir",
        "read test.py",
    ]

    passed = 0
    failed = 0

    for user_input in test_cases:
        print(f"\nInput: '{user_input}'")
        try:
            result = router.classify(user_input)
            # Fallback should still produce valid result
            if result.intent and result.confidence > 0:
                print(f"  Intent: {result.intent}")
                print(f"  Used fallback: {result.used_fallback}")
                print(f"  ✓ PASS")
                passed += 1
            else:
                print(f"  ✗ FAIL: Invalid result")
                failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print(f"\nFallback: {passed}/{passed+failed} tests passed")
    return passed == (passed + failed)


def test_model_memory_usage(lifecycle):
    """Test that routing doesn't load unnecessary models"""
    print_section("TEST 5: Memory Efficiency")

    usage = lifecycle.get_memory_usage()
    print(f"\nMemory usage:")
    print(f"  Total: {usage['total_mb']:.0f} MB")
    print(f"  Router loaded: {usage['models']['router']['loaded']}")
    print(f"  Coder loaded: {usage['models']['coder']['loaded']}")
    print(f"  Algorithm loaded: {usage['models']['algorithm']['loaded']}")

    # Only router should be loaded for Phase 2
    if usage['models']['router']['loaded']:
        if not usage['models']['coder']['loaded'] and not usage['models']['algorithm']['loaded']:
            print("\n  ✓ PASS: Only router loaded (efficient)")
            return True
        else:
            print("\n  ✗ FAIL: Unnecessary models loaded")
            return False
    else:
        print("\n  ✗ FAIL: Router not loaded")
        return False


def main():
    """Run all Phase 2 tests"""
    print("\n" + "=" * 70)
    print("  PHASE 2 INTEGRATION TEST")
    print("  Intent Router & Tool Executor")
    print("=" * 70)

    # Load configuration
    print("\nLoading configuration...")
    try:
        config = Config()
        print(f"✓ Config loaded")
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
        return 1

    # Load router model
    print("\nLoading router model...")
    try:
        router_model = lifecycle.load_model(ModelRole.ROUTER)
        print(f"✓ Router loaded: {router_model.model_path.name}")

        # Create IntentRouter instance
        router = IntentRouter(router_model.model_path, router_model.config)
        router._model = router_model._model
        router._loaded = router_model._loaded
        print("✓ IntentRouter initialized")
    except Exception as e:
        print(f"✗ Failed to load router: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Create tool executor
    print("\nCreating ToolExecutor...")
    try:
        permission_manager = PermissionManager(config)
        git_manager = GitManager(permission_manager, config.workspace_dir)
        shell_manager = ShellManager(permission_manager, config.workspace_dir, config)
        file_tools = FileTools(config)

        tool_executor = ToolExecutor(git_manager, shell_manager, file_tools, permission_manager)
        print("✓ ToolExecutor created")
    except Exception as e:
        print(f"✗ Failed to create tool executor: {e}")
        return 1

    # Create orchestrator
    print("\nCreating Orchestrator...")
    try:
        orchestrator = Orchestrator(config, lifecycle, tool_executor)
        orchestrator.router = router  # Reuse loaded router
        print("✓ Orchestrator created")
    except Exception as e:
        print(f"✗ Failed to create orchestrator: {e}")
        return 1

    # Run tests
    results = {}
    results['classification'] = test_intent_classification(router)
    results['tool_execution'] = test_tool_execution(tool_executor)
    results['orchestrator'] = test_orchestrator(orchestrator)
    results['fallback'] = test_fallback_regex(router)
    results['memory'] = test_model_memory_usage(lifecycle)

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

    # Cleanup
    print("\nCleaning up...")
    lifecycle.unload_all()

    if failed == 0:
        print("\n" + "=" * 70)
        print("  🎉 ALL TESTS PASSED - PHASE 2 COMPLETE!")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print(f"  ⚠️  {failed} TEST(S) FAILED - CHECK ERRORS ABOVE")
        print("=" * 70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
