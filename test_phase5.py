#!/usr/bin/env python3
"""Phase 5 Integration Tests - Diff-Based Editing

Tests the diff-based editing system:
- DiffGenerator
- EditBlock creation and validation
- FileTools.patch_file()
- Token savings estimation

Run: python3 test_phase5.py
"""
import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from core.diff_generator import DiffGenerator, EditBlock
from core.tools import FileTools
from utils.config import Config


def test_edit_block_creation():
    """Test EditBlock dataclass creation and validation"""
    print("=" * 70)
    print("TEST 1: EditBlock - Creation and Validation")
    print("=" * 70)

    # Valid edit block
    edit = EditBlock(
        start_line=5,
        end_line=7,
        old_content="old code",
        new_content="new code",
        description="Replace old code with new code"
    )

    print(f"\n✓ Created valid EditBlock")
    print(f"  Lines: {edit.start_line}-{edit.end_line}")
    print(f"  Description: {edit.description}")

    # Test validation - invalid start_line
    try:
        invalid_edit = EditBlock(
            start_line=0,  # Invalid - must be >= 1
            end_line=5,
            old_content="",
            new_content="",
            description="Invalid"
        )
        print("\n✗ FAIL: Should have raised ValueError for start_line < 1")
        return False
    except ValueError as e:
        print(f"\n✓ Correctly rejected start_line < 1: {e}")

    # Test validation - end_line < start_line
    try:
        invalid_edit = EditBlock(
            start_line=10,
            end_line=5,  # Invalid - end < start
            old_content="",
            new_content="",
            description="Invalid"
        )
        print("✗ FAIL: Should have raised ValueError for end_line < start_line")
        return False
    except ValueError as e:
        print(f"✓ Correctly rejected end_line < start_line: {e}")

    print("\n✓ PASS: EditBlock creation and validation works")
    return True


def test_diff_generator_parsing():
    """Test parsing edit blocks from model response"""
    print("\n" + "=" * 70)
    print("TEST 2: DiffGenerator - Parse Edit Blocks")
    print("=" * 70)

    diff_gen = DiffGenerator()

    # Simulated model response with edit blocks
    model_response = """Here are the edits needed:

EDIT 1:
Lines: 5-7
Description: Fix the function signature
Old:
```python
def hello(name):
    print(name)
```
New:
```python
def hello(name: str) -> None:
    print(f"Hello, {name}!")
```

EDIT 2:
Lines: 15
Description: Add return statement
Old:
```python
result = calculate()
```
New:
```python
result = calculate()
return result
```
"""

    edits = diff_gen.parse_edit_blocks(model_response)

    print(f"\nParsed {len(edits)} edit blocks")

    if len(edits) != 2:
        print(f"✗ FAIL: Expected 2 edits, got {len(edits)}")
        return False

    # Check first edit
    edit1 = edits[0]
    print(f"\nEdit 1:")
    print(f"  Lines: {edit1.start_line}-{edit1.end_line}")
    print(f"  Description: {edit1.description}")

    assert edit1.start_line == 5
    assert edit1.end_line == 7
    assert "Fix the function signature" in edit1.description

    # Check second edit
    edit2 = edits[1]
    print(f"\nEdit 2:")
    print(f"  Lines: {edit2.start_line}-{edit2.end_line}")
    print(f"  Description: {edit2.description}")

    assert edit2.start_line == 15
    assert edit2.end_line == 15

    print("\n✓ PASS: Edit block parsing works")
    return True


def test_diff_apply_edits():
    """Test applying edits to code"""
    print("\n" + "=" * 70)
    print("TEST 3: DiffGenerator - Apply Edits")
    print("=" * 70)

    diff_gen = DiffGenerator()

    # Original code
    original = """def greet(name):
    print(name)

def calculate(a, b):
    return a + b

result = calculate(5, 3)
"""

    print("\nOriginal code:")
    print(original)

    # Create edits
    edits = [
        EditBlock(
            start_line=1,
            end_line=2,
            old_content='def greet(name):\n    print(name)',
            new_content='def greet(name: str) -> None:\n    print(f"Hello, {name}!")',
            description="Add type hints and improve greeting"
        ),
        EditBlock(
            start_line=7,
            end_line=7,
            old_content='result = calculate(5, 3)',
            new_content='result = calculate(5, 3)\nprint(f"Result: {result}")',
            description="Add print statement"
        )
    ]

    # Apply edits
    modified = diff_gen.apply_edits(original, edits)

    print("\nModified code:")
    print(modified)

    # Verify changes
    assert "name: str" in modified
    assert "Hello, {name}!" in modified
    assert 'print(f"Result: {result}")' in modified

    print("\n✓ PASS: Edit application works")
    return True


def test_diff_validation():
    """Test edit validation"""
    print("\n" + "=" * 70)
    print("TEST 4: DiffGenerator - Validate Edits")
    print("=" * 70)

    diff_gen = DiffGenerator()

    original = """line 1
line 2
line 3
line 4
line 5
"""

    # Valid edits
    valid_edits = [
        EditBlock(1, 2, "line 1\nline 2", "modified 1\nmodified 2", "Valid edit")
    ]

    errors = diff_gen.validate_edits(original, valid_edits)
    print(f"\nValid edits: {len(errors)} errors")
    assert len(errors) == 0
    print("✓ Valid edits pass validation")

    # Invalid edits - out of range
    invalid_edits = [
        EditBlock(10, 15, "", "", "Out of range")  # File only has 6 lines (including empty)
    ]

    errors = diff_gen.validate_edits(original, invalid_edits)
    print(f"\nInvalid edits (out of range): {len(errors)} errors")
    assert len(errors) > 0
    print(f"✓ Correctly detected errors: {errors[0]}")

    # Overlapping edits
    overlapping_edits = [
        EditBlock(2, 4, "", "", "First edit"),
        EditBlock(3, 5, "", "", "Overlapping edit")
    ]

    errors = diff_gen.validate_edits(original, overlapping_edits)
    print(f"\nOverlapping edits: {len(errors)} errors")
    assert len(errors) > 0
    print(f"✓ Correctly detected overlap: {errors[0]}")

    print("\n✓ PASS: Edit validation works")
    return True


def test_unified_diff_generation():
    """Test unified diff format generation"""
    print("\n" + "=" * 70)
    print("TEST 5: DiffGenerator - Unified Diff")
    print("=" * 70)

    diff_gen = DiffGenerator()

    original = """def hello():
    print("Hello")
"""

    modified = """def hello(name: str):
    print(f"Hello, {name}")
"""

    diff = diff_gen.generate_unified_diff(original, modified, "test.py")

    print("\nGenerated unified diff:")
    print(diff)

    assert "def hello" in diff
    assert "-" in diff  # Should have deletions
    assert "+" in diff  # Should have additions

    print("\n✓ PASS: Unified diff generation works")
    return True


def test_token_savings_estimation():
    """Test token savings estimation"""
    print("\n" + "=" * 70)
    print("TEST 6: DiffGenerator - Token Savings")
    print("=" * 70)

    diff_gen = DiffGenerator()

    # Large file
    original = "\n".join([f"line {i}" for i in range(1, 101)])  # 100 lines

    # Small edit - change only line 50
    edits = [
        EditBlock(
            start_line=50,
            end_line=50,
            old_content="line 50",
            new_content="modified line 50",
            description="Single line change"
        )
    ]

    savings = diff_gen.estimate_token_savings(original, edits)

    print(f"\nOriginal file: ~{savings['full_file_tokens']} tokens")
    print(f"Diff edits: ~{savings['diff_tokens']} tokens")
    print(f"Savings: ~{savings['savings_tokens']} tokens ({savings['savings_percent']:.1f}%)")

    # Should have significant savings for small edit on large file
    assert savings['savings_percent'] > 50, "Should save >50% tokens for small edits"

    print("\n✓ PASS: Token savings estimation works")
    return True


def test_file_tools_patch():
    """Test FileTools.patch_file() integration"""
    print("\n" + "=" * 70)
    print("TEST 7: FileTools - patch_file()")
    print("=" * 70)

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"\nUsing temp directory: {temp_dir}")

    try:
        # Create config with temp workspace
        config = Config()
        config.workspace_dir = temp_dir
        config.backup_before_edit = False  # Disable backup for test

        # Create FileTools
        file_tools = FileTools(config)

        # Create test file
        test_file = "test_patch.py"
        original_content = """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""

        write_result = file_tools.write_file(test_file, original_content)
        assert write_result['success']
        print(f"✓ Created test file: {test_file}")

        # Create edits
        edits = [
            EditBlock(
                start_line=1,
                end_line=2,
                old_content="def add(a, b):\n    return a + b",
                new_content="def add(a: int, b: int) -> int:\n    \"\"\"Add two numbers\"\"\"\n    return a + b",
                description="Add type hints and docstring"
            )
        ]

        # Apply patch
        print(f"\nApplying {len(edits)} edit(s)...")
        patch_result = file_tools.patch_file(test_file, edits)

        if not patch_result['success']:
            print(f"✗ FAIL: Patch failed: {patch_result.get('error')}")
            return False

        print(f"✓ Patch applied successfully")
        print(f"  Edits: {patch_result['num_edits']}")
        print(f"  Token savings: {patch_result['token_savings']['savings_percent']:.1f}%")

        # Verify patched file
        read_result = file_tools.read_file(test_file)
        patched_content = read_result['content']

        print(f"\nPatched content:")
        print(patched_content)

        assert "def add(a: int, b: int) -> int:" in patched_content
        assert '"""Add two numbers"""' in patched_content
        assert "def subtract(a, b):" in patched_content  # Unchanged

        print("\n✓ PASS: FileTools.patch_file() works")
        return True

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n✓ Cleaned up temp directory")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  PHASE 5 INTEGRATION TESTS")
    print("  Diff-Based Editing (DiffGenerator + EditBlock + FileTools)")
    print("=" * 70)

    results = {}

    # Run tests
    results['edit_block'] = test_edit_block_creation()
    results['diff_parsing'] = test_diff_generator_parsing()
    results['diff_apply'] = test_diff_apply_edits()
    results['diff_validation'] = test_diff_validation()
    results['unified_diff'] = test_unified_diff_generation()
    results['token_savings'] = test_token_savings_estimation()
    results['file_patch'] = test_file_tools_patch()

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
