"""Smoke tests for Codey Engine core functionality

These tests verify basic functionality without loading heavy models.
Run these before full integration tests to catch obvious issues early.
"""
import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestJSONUtils(unittest.TestCase):
    """Smoke tests for JSON utilities"""

    def test_import(self):
        """Test that json_utils can be imported"""
        from utils.json_utils import extract_json, safe_json_loads
        self.assertIsNotNone(extract_json)
        self.assertIsNotNone(safe_json_loads)

    def test_extract_clean_json(self):
        """Test extracting clean JSON"""
        from utils.json_utils import extract_json
        data, method = extract_json('{"intent": "coding_task", "confidence": 0.9}')
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'coding_task')

    def test_extract_with_noise(self):
        """Test extracting JSON with noise"""
        from utils.json_utils import extract_json
        data, method = extract_json('JSON: {"intent": "tool_call"} done')
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'tool_call')

    def test_yaml_style(self):
        """Test YAML-style extraction"""
        from utils.json_utils import extract_json
        data, method = extract_json('- intent: coding_task\n- confidence: 0.8')
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'coding_task')

    def test_safe_json_loads(self):
        """Test safe JSON loading"""
        from utils.json_utils import safe_json_loads
        self.assertEqual(safe_json_loads('{"key": "value"}'), {'key': 'value'})
        self.assertEqual(safe_json_loads('invalid', default={}), {})


class TestPerformance(unittest.TestCase):
    """Smoke tests for performance utilities"""

    def test_import(self):
        """Test that performance module can be imported"""
        from utils.performance import (
            PerformanceTracker, RequestMetrics, TimingResult,
            start_request, end_request, time_operation
        )
        self.assertIsNotNone(PerformanceTracker)
        self.assertIsNotNone(RequestMetrics)

    def test_request_tracking(self):
        """Test basic request tracking"""
        from utils.performance import start_request, end_request, add_timing

        metrics = start_request()
        self.assertIsNotNone(metrics)
        self.assertIsNotNone(metrics.request_id)

        add_timing("test_operation", 100.0)

        result = end_request()
        self.assertIsNotNone(result)
        self.assertEqual(len(result.timings), 1)
        self.assertEqual(result.timings[0].operation, "test_operation")

    def test_time_operation_context(self):
        """Test time_operation context manager"""
        from utils.performance import start_request, end_request, time_operation
        import time

        start_request()
        with time_operation("sleep_test"):
            time.sleep(0.01)  # 10ms

        result = end_request()
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.timings[0].duration_ms, 10)

    def test_token_estimation(self):
        """Test token estimation"""
        from utils.performance import estimate_tokens

        # ~4 chars per token
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("hello world test"), 4)  # 16 chars / 4
        self.assertEqual(estimate_tokens("a" * 100), 25)  # 100 chars / 4


class TestLogging(unittest.TestCase):
    """Smoke tests for logging configuration"""

    def test_import(self):
        """Test that logging module can be imported"""
        from utils.logging_config import (
            configure_logging, get_logger, set_level
        )
        self.assertIsNotNone(configure_logging)
        self.assertIsNotNone(get_logger)

    def test_get_logger(self):
        """Test getting a logger"""
        from utils.logging_config import get_logger
        import logging

        logger = get_logger("test")
        self.assertIsInstance(logger, logging.Logger)
        self.assertTrue(logger.name.startswith("codey"))


class TestOutputFormat(unittest.TestCase):
    """Smoke tests for output format detection"""

    def test_default_python(self):
        """Test that default is Python"""
        # Import the mock from test file
        from test_output_format import MockOrchestrator
        orch = MockOrchestrator()

        filename, lang = orch._determine_output_format("write a calculator")
        self.assertEqual(lang, 'python')
        self.assertTrue(filename.endswith('.py'))

    def test_html_detection(self):
        """Test HTML detection"""
        from test_output_format import MockOrchestrator
        orch = MockOrchestrator()

        filename, lang = orch._determine_output_format("create an html page")
        self.assertEqual(lang, 'html')
        self.assertTrue(filename.endswith('.html'))

    def test_javascript_detection(self):
        """Test JavaScript detection"""
        from test_output_format import MockOrchestrator
        orch = MockOrchestrator()

        filename, lang = orch._determine_output_format("create a javascript function")
        self.assertEqual(lang, 'javascript')
        self.assertTrue(filename.endswith('.js'))


class TestPrompts(unittest.TestCase):
    """Smoke tests for prompt templates"""

    def test_import_router_prompts(self):
        """Test that router prompts can be imported"""
        from router.prompts import (
            INTENT_ROUTER_SYSTEM, REGEX_PATTERNS,
            get_intent_prompt, get_parameter_extraction_prompt
        )
        self.assertIsNotNone(INTENT_ROUTER_SYSTEM)
        self.assertIsInstance(REGEX_PATTERNS, dict)

    def test_intent_prompt_generation(self):
        """Test intent prompt generation"""
        from router.prompts import get_intent_prompt

        prompt = get_intent_prompt("git status")
        self.assertIn("git status", prompt)
        self.assertIn("intent", prompt.lower())

    def test_regex_patterns_structure(self):
        """Test that regex patterns have correct structure"""
        from router.prompts import REGEX_PATTERNS

        expected_keys = [
            'tool_call_git', 'tool_call_shell', 'tool_call_file',
            'coding_task', 'algorithm_task', 'simple_answer'
        ]
        for key in expected_keys:
            self.assertIn(key, REGEX_PATTERNS)
            self.assertIsInstance(REGEX_PATTERNS[key], list)


class TestThinkingDisplay(unittest.TestCase):
    """Smoke tests for thinking display"""

    def test_import(self):
        """Test that thinking display can be imported"""
        from utils.thinking_display import (
            ThinkingStep, ThinkingDisplay,
            step, substep, complete, error
        )
        self.assertIsNotNone(ThinkingStep)
        self.assertIsNotNone(ThinkingDisplay)

    def test_thinking_steps_enum(self):
        """Test ThinkingStep enum values"""
        from utils.thinking_display import ThinkingStep

        # Check key steps exist
        self.assertIsNotNone(ThinkingStep.CLASSIFYING)
        self.assertIsNotNone(ThinkingStep.ROUTING)
        self.assertIsNotNone(ThinkingStep.GENERATING_CODE)
        self.assertIsNotNone(ThinkingStep.COMPLETE)

    def test_display_disabled(self):
        """Test display works when disabled"""
        from utils.thinking_display import ThinkingDisplay, ThinkingStep

        display = ThinkingDisplay(enabled=False)
        # Should not raise
        display.step(ThinkingStep.CLASSIFYING)
        display.substep("test")
        display.complete()


class TestCoderStructure(unittest.TestCase):
    """Smoke tests for coder model structure"""

    def test_import(self):
        """Test that coder can be imported"""
        from models.coder import PrimaryCoder, CodingTask, CodeResult
        self.assertIsNotNone(PrimaryCoder)
        self.assertIsNotNone(CodingTask)
        self.assertIsNotNone(CodeResult)

    def test_coding_task_creation(self):
        """Test CodingTask creation"""
        from models.coder import CodingTask

        task = CodingTask(
            task_type="create",
            target_files=["test.py"],
            instructions="create a test function",
            language="python"
        )
        self.assertEqual(task.task_type, "create")
        self.assertEqual(task.language, "python")

    def test_code_result_creation(self):
        """Test CodeResult creation"""
        from models.coder import CodeResult

        result = CodeResult(
            success=True,
            code={"test.py": "def test(): pass"},
            explanation="Created test function"
        )
        self.assertTrue(result.success)
        self.assertIn("test.py", result.code)


class TestIntentRouter(unittest.TestCase):
    """Smoke tests for intent router structure"""

    def test_import(self):
        """Test that intent router can be imported"""
        from router.intent_router import IntentRouter, IntentResult
        self.assertIsNotNone(IntentRouter)
        self.assertIsNotNone(IntentResult)

    def test_intent_result_creation(self):
        """Test IntentResult creation"""
        from router.intent_router import IntentResult

        result = IntentResult(
            intent="coding_task",
            confidence=0.95,
            tool=None,
            escalate_to="coder"
        )
        self.assertTrue(result.is_coding_task())
        self.assertTrue(result.should_escalate())
        self.assertFalse(result.is_tool_call())

    def test_intent_result_tool_call(self):
        """Test IntentResult for tool call"""
        from router.intent_router import IntentResult

        result = IntentResult(
            intent="tool_call",
            confidence=0.99,
            tool="git",
            escalate_to=None
        )
        self.assertTrue(result.is_tool_call())
        self.assertFalse(result.should_escalate())


class TestDiffGenerator(unittest.TestCase):
    """Smoke tests for diff generator"""

    def test_import(self):
        """Test that diff generator can be imported"""
        from core.diff_generator import DiffGenerator, EditBlock
        self.assertIsNotNone(DiffGenerator)
        self.assertIsNotNone(EditBlock)

    def test_edit_block_creation(self):
        """Test EditBlock creation"""
        from core.diff_generator import EditBlock

        block = EditBlock(
            start_line=1,
            end_line=5,
            old_content="old code",
            new_content="new code",
            description="Test edit"
        )
        self.assertEqual(block.start_line, 1)
        self.assertEqual(block.end_line, 5)

    def test_diff_generator_creation(self):
        """Test DiffGenerator creation"""
        from core.diff_generator import DiffGenerator

        gen = DiffGenerator()
        self.assertIsNotNone(gen)


class TestTaskPlanner(unittest.TestCase):
    """Smoke tests for task planner"""

    def test_import(self):
        """Test that task planner can be imported"""
        from core.task_planner import TaskPlanner, TaskStep
        self.assertIsNotNone(TaskPlanner)
        self.assertIsNotNone(TaskStep)

    def test_task_step_creation(self):
        """Test TaskStep creation"""
        from core.task_planner import TaskStep, TaskType, StepStatus

        step = TaskStep(
            step_id=1,
            task_type=TaskType.CODE_GEN,
            description="Create a file"
        )
        self.assertEqual(step.step_id, 1)
        self.assertEqual(step.status, StepStatus.PENDING)


def run_smoke_tests():
    """Run all smoke tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestJSONUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestOutputFormat))
    suite.addTests(loader.loadTestsFromTestCase(TestPrompts))
    suite.addTests(loader.loadTestsFromTestCase(TestThinkingDisplay))
    suite.addTests(loader.loadTestsFromTestCase(TestCoderStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestIntentRouter))
    suite.addTests(loader.loadTestsFromTestCase(TestDiffGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskPlanner))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == '__main__':
    success = run_smoke_tests()
    sys.exit(0 if success else 1)
