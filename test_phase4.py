#!/usr/bin/env python3
"""Phase 4 Integration Tests - Engine Decomposition

Tests the new decomposed architecture:
- ResponseHandler
- TaskPlanner
- EngineV3

Run: python3 test_phase4.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.response_handler import ResponseHandler
from core.task_planner import TaskPlanner, TaskType, StepStatus
from executor.tool_executor import ToolResult
from models.coder import CodeResult, CodingTask
from models.algorithm_model import AlgorithmResult, AlgorithmTask


def test_response_handler():
    """Test ResponseHandler formatting"""
    print("=" * 70)
    print("TEST 1: ResponseHandler - Format Tool Results")
    print("=" * 70)

    handler = ResponseHandler()

    # Test git result
    git_result = ToolResult(
        success=True,
        tool="git",
        action="status",
        output={
            'clean': False,
            'staged': ['file1.py', 'file2.py'],
            'modified': ['file3.py'],
            'untracked': ['file4.py']
        }
    )

    formatted = handler.format_tool_result(git_result)
    print(f"\nGit Status Result:\n{formatted}")

    assert "Staged (2)" in formatted
    assert "Modified (1)" in formatted
    print("\n✓ PASS: Git result formatting works")

    # Test code result
    code_result = CodeResult(
        success=True,
        code={'test.py': 'def hello():\n    print("Hello World")'},
        explanation="Created a simple hello function"
    )

    task = CodingTask(
        task_type="create",
        target_files=["test.py"],
        instructions="Create hello function",
        language="python"
    )

    formatted = handler.format_code_result(code_result, task)
    print(f"\nCode Result:\n{formatted}")

    assert "Create completed" in formatted
    assert "def hello()" in formatted
    print("\n✓ PASS: Code result formatting works")

    # Test algorithm result
    algo_result = AlgorithmResult(
        success=True,
        code="def binary_search(arr, target):\n    # Implementation",
        complexity_analysis={'time': 'O(log n)', 'space': 'O(1)'},
        explanation="Binary search implementation"
    )

    algo_task = AlgorithmTask(
        problem_description="Binary search in sorted array",
        language="python"
    )

    formatted = handler.format_algorithm_result(algo_result, algo_task)
    print(f"\nAlgorithm Result:\n{formatted}")

    assert "Algorithm solution generated" in formatted
    assert "O(log n)" in formatted
    print("\n✓ PASS: Algorithm result formatting works")

    return True


def test_task_planner_simple():
    """Test TaskPlanner with simple requests"""
    print("\n" + "=" * 70)
    print("TEST 2: TaskPlanner - Single Step Detection")
    print("=" * 70)

    planner = TaskPlanner()

    # Simple request - should NOT need planning
    simple_request = "create a file test.py"
    needs_plan = planner.needs_planning(simple_request)

    print(f"\nRequest: '{simple_request}'")
    print(f"Needs planning: {needs_plan}")

    assert not needs_plan, "Simple request should not need planning"
    print("✓ PASS: Simple requests correctly identified")

    return True


def test_task_planner_multi_step():
    """Test TaskPlanner with multi-step requests"""
    print("\n" + "=" * 70)
    print("TEST 3: TaskPlanner - Multi-Step Decomposition")
    print("=" * 70)

    planner = TaskPlanner()

    # Multi-step request
    multi_request = "create test.py then run it and finally commit the changes"
    needs_plan = planner.needs_planning(multi_request)

    print(f"\nRequest: '{multi_request}'")
    print(f"Needs planning: {needs_plan}")

    assert needs_plan, "Multi-step request should need planning"

    # Create plan
    plan = planner.create_plan(multi_request)

    print(f"\nPlan created:")
    print(f"  Total steps: {len(plan.steps)}")
    print(f"  Sequential: {plan.is_sequential}")

    for step in plan.steps:
        print(f"  Step {step.step_id}: {step.description} ({step.task_type.value})")

    assert len(plan.steps) >= 2, "Should have at least 2 steps"
    assert plan.is_sequential, "Should be sequential"

    print("\n✓ PASS: Multi-step decomposition works")

    return True


def test_task_planner_numbered():
    """Test TaskPlanner with numbered lists"""
    print("\n" + "=" * 70)
    print("TEST 4: TaskPlanner - Numbered List Decomposition")
    print("=" * 70)

    planner = TaskPlanner()

    numbered_request = """1. Create database.py with user model
2. Create api.py with REST endpoints
3. Run the tests"""

    needs_plan = planner.needs_planning(numbered_request)
    print(f"\nRequest:\n{numbered_request}")
    print(f"\nNeeds planning: {needs_plan}")

    assert needs_plan, "Numbered list should need planning"

    # Create plan
    plan = planner.create_plan(numbered_request)

    print(f"\nPlan created:")
    print(f"  Total steps: {len(plan.steps)}")

    for step in plan.steps:
        print(f"  Step {step.step_id}: {step.description}")

    assert len(plan.steps) == 3, "Should have 3 steps"

    print("\n✓ PASS: Numbered list decomposition works")

    return True


def test_task_planner_execution():
    """Test TaskPlanner execution tracking"""
    print("\n" + "=" * 70)
    print("TEST 5: TaskPlanner - Execution Tracking")
    print("=" * 70)

    planner = TaskPlanner()

    # Create plan
    request = "create test.py then run it"
    plan = planner.create_plan(request)

    print(f"\nOriginal plan:")
    print(planner.get_plan_summary(plan))

    # Simulate execution
    print("\nSimulating execution...")

    # Get first step
    step = planner.get_next_pending_step(plan)
    assert step is not None, "Should have a pending step"

    print(f"  Executing step {step.step_id}: {step.description}")
    planner.update_step_status(plan, step.step_id, StepStatus.IN_PROGRESS)
    planner.update_step_status(plan, step.step_id, StepStatus.COMPLETED, result="Success")

    # Get next step
    step = planner.get_next_pending_step(plan)
    assert step is not None, "Should have another pending step"

    print(f"  Executing step {step.step_id}: {step.description}")
    planner.update_step_status(plan, step.step_id, StepStatus.IN_PROGRESS)
    planner.update_step_status(plan, step.step_id, StepStatus.COMPLETED, result="Success")

    # Check completion
    is_complete = planner.is_plan_complete(plan)
    assert is_complete, "Plan should be complete"

    print(f"\nFinal plan:")
    print(planner.get_plan_summary(plan))

    print("\n✓ PASS: Execution tracking works")

    return True


def test_engine_v3_import():
    """Test Engine V3 can be imported and initialized"""
    print("\n" + "=" * 70)
    print("TEST 6: EngineV3 - Import and Initialize")
    print("=" * 70)

    try:
        from engine_v3 import EngineV3
        from utils.config import Config

        print("\nLoading configuration...")
        config = Config()

        print("Initializing EngineV3...")
        engine = EngineV3(config)

        print("✓ Engine initialized successfully")

        # Cleanup
        engine.shutdown()

        print("\n✓ PASS: EngineV3 import and initialization works")
        return True

    except Exception as e:
        print(f"\n✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  PHASE 4 INTEGRATION TESTS")
    print("  Engine Decomposition (ResponseHandler + TaskPlanner + EngineV3)")
    print("=" * 70)

    results = {}

    # Run tests
    results['response_handler'] = test_response_handler()
    results['planner_simple'] = test_task_planner_simple()
    results['planner_multi'] = test_task_planner_multi_step()
    results['planner_numbered'] = test_task_planner_numbered()
    results['planner_execution'] = test_task_planner_execution()
    results['engine_v3_import'] = test_engine_v3_import()

    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")

    total = len(results)
    passed = sum(1 for p in results.values() if p)
    failed = total - passed

    print(f"\n  Total: {total} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if failed > 0:
        print("\n" + "=" * 70)
        print("  ⚠️  SOME TESTS FAILED")
        print("=" * 70)
        return 1
    else:
        print("\n" + "=" * 70)
        print("  ✅ ALL TESTS PASSED")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
