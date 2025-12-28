"""Phase 6 Integration Tests - CPU Optimization

Tests for:
1. ChunkedTaskExecutor
2. IncrementalGenerator
3. ProgressTracker
4. Full-stack app decomposition
5. README auto-generation
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestChunkedExecutor(unittest.TestCase):
    """Tests for ChunkedTaskExecutor"""

    def test_analyze_fullstack_task(self):
        """Test full-stack task analysis"""
        from core.chunked_executor import ChunkedTaskExecutor, ChunkType

        executor = ChunkedTaskExecutor()
        plan = executor.analyze_task(
            "create a full-stack todo app with Flask backend and database"
        )

        self.assertTrue(plan.metadata.get('is_fullstack') or plan.metadata.get('is_backend'))
        self.assertTrue(plan.metadata.get('has_database'))
        self.assertGreater(len(plan.chunks), 3)

    def test_analyze_simple_task(self):
        """Test simple task analysis"""
        from core.chunked_executor import ChunkedTaskExecutor, ChunkType

        executor = ChunkedTaskExecutor()
        plan = executor.analyze_task("create a calculator")

        self.assertEqual(len(plan.chunks), 1)
        self.assertEqual(plan.chunks[0].chunk_type, ChunkType.SINGLE_FILE)

    def test_chunk_dependencies(self):
        """Test that chunk dependencies are properly set"""
        from core.chunked_executor import ChunkedTaskExecutor

        executor = ChunkedTaskExecutor()
        plan = executor.analyze_task(
            "create a full-stack web app with Flask and SQLite database"
        )

        # Find README chunk - should depend on other chunks
        readme_chunk = None
        for chunk in plan.chunks:
            if 'README' in chunk.filename:
                readme_chunk = chunk
                break

        if readme_chunk:
            self.assertGreater(len(readme_chunk.dependencies), 0)

    def test_execution_order(self):
        """Test topological sorting of chunks"""
        from core.chunked_executor import ChunkedTaskExecutor

        executor = ChunkedTaskExecutor()
        plan = executor.analyze_task(
            "create a Flask app with database"
        )

        # Execution order should be valid
        self.assertEqual(len(plan.execution_order), len(plan.chunks))

    def test_time_estimation(self):
        """Test generation time estimation"""
        from core.chunked_executor import ChunkedTaskExecutor

        executor = ChunkedTaskExecutor()
        plan = executor.analyze_task("create a full-stack todo app")

        # Should have reasonable time estimate
        self.assertGreater(plan.estimated_total_time, 0)
        # At 5 tok/s, even small tasks should take some time
        self.assertLess(plan.estimated_total_time, 600)  # Less than 10 minutes


class TestProgressTracker(unittest.TestCase):
    """Tests for ProgressTracker"""

    def test_task_lifecycle(self):
        """Test task start/complete lifecycle"""
        from core.progress_tracker import ProgressTracker, TaskPhase, StepType

        # Use silent callback for testing
        class SilentCallback:
            def on_task_start(self, task): pass
            def on_phase_start(self, task, phase): pass
            def on_phase_complete(self, task, phase): pass
            def on_step_start(self, task, step): pass
            def on_step_progress(self, task, step, pct): pass
            def on_step_complete(self, task, step): pass
            def on_step_failed(self, task, step, error): pass
            def on_task_complete(self, task): pass
            def on_task_failed(self, task, error): pass

        tracker = ProgressTracker(callback=SilentCallback())

        # Start task
        task = tracker.start_task("Test task")
        self.assertEqual(task.status, "running")

        # Start phase
        phase = tracker.start_phase(TaskPhase.GENERATION)
        self.assertEqual(phase.status, "running")

        # Start step
        step = tracker.start_step("step1", StepType.GENERATE_CODE, "Generate code")
        self.assertEqual(step.status, "running")

        # Complete step
        tracker.complete_step("step1")
        self.assertEqual(step.status, "completed")

        # Complete phase
        tracker.complete_phase()

        # Complete task
        final = tracker.complete_task()
        self.assertEqual(final.status, "completed")
        self.assertGreater(final.overall_progress, 0)

    def test_step_failure(self):
        """Test step failure handling"""
        from core.progress_tracker import ProgressTracker, TaskPhase, StepType

        class SilentCallback:
            def __getattr__(self, name):
                return lambda *args, **kwargs: None

        tracker = ProgressTracker(callback=SilentCallback())
        tracker.start_task("Test")
        tracker.start_phase(TaskPhase.GENERATION)
        step = tracker.start_step("step1", StepType.GENERATE_CODE, "Test step")

        tracker.fail_step("step1", "Test error")

        self.assertEqual(step.status, "failed")
        self.assertEqual(step.error, "Test error")

    def test_summary(self):
        """Test summary generation"""
        from core.progress_tracker import ProgressTracker, TaskPhase, StepType

        class SilentCallback:
            def __getattr__(self, name):
                return lambda *args, **kwargs: None

        tracker = ProgressTracker(callback=SilentCallback())
        tracker.start_task("Summary test")
        tracker.start_phase(TaskPhase.PLANNING)
        tracker.start_step("s1", StepType.ANALYZE, "Analyze")
        tracker.complete_step("s1")
        tracker.complete_phase()
        tracker.complete_task()

        summary = tracker.get_summary()

        self.assertEqual(summary['status'], 'completed')
        self.assertIn('phases', summary)


class TestTaskPlanner(unittest.TestCase):
    """Tests for TaskPlanner enhancements"""

    def test_fullstack_detection(self):
        """Test full-stack app detection"""
        from core.task_planner import TaskPlanner

        planner = TaskPlanner()

        # Explicit full-stack
        self.assertTrue(planner.is_fullstack_app("create a full-stack todo app"))
        self.assertTrue(planner.is_fullstack_app("build a fullstack web application"))

        # Implicit full-stack (backend + frontend)
        self.assertTrue(planner.is_fullstack_app("create a Flask app with HTML frontend"))
        self.assertTrue(planner.is_fullstack_app("build an API with a webpage interface"))

        # Not full-stack
        self.assertFalse(planner.is_fullstack_app("create a calculator"))
        self.assertFalse(planner.is_fullstack_app("implement binary search"))

    def test_fullstack_decomposition(self):
        """Test full-stack decomposition"""
        from core.task_planner import TaskPlanner, TaskType

        planner = TaskPlanner()
        plan = planner.decompose_fullstack(
            "create a todo app with Flask backend and SQLite database"
        )

        # Should have multiple steps
        self.assertGreater(len(plan.steps), 5)

        # Should have database-related steps
        has_db_step = any('database' in s.description.lower() or 'model' in s.description.lower()
                         for s in plan.steps)
        self.assertTrue(has_db_step)

        # Should have frontend steps
        has_html_step = any('html' in s.description.lower() for s in plan.steps)
        self.assertTrue(has_html_step)

        # Should have README step
        has_readme = any('readme' in s.description.lower() for s in plan.steps)
        self.assertTrue(has_readme)

    def test_time_estimation(self):
        """Test generation time estimation"""
        from core.task_planner import TaskPlanner

        planner = TaskPlanner()
        plan = planner.decompose_fullstack("create a full-stack todo app")

        time_estimate = planner.estimate_generation_time(plan)

        # Should have positive estimate
        self.assertGreater(time_estimate, 0)


class TestReadmeGenerator(unittest.TestCase):
    """Tests for README auto-generation"""

    def test_readme_generation(self):
        """Test basic README generation"""
        from core.readme_generator import ReadmeGenerator

        generator = ReadmeGenerator()
        readme = generator.generate(
            task_description="create a todo app",
            generated_files=['app.py', 'models.py', 'templates/index.html'],
            extra_context={'has_database': True, 'is_fullstack': True}
        )

        # Should have key sections
        self.assertIn('# ', readme)  # Title
        self.assertIn('## ', readme)  # Sections
        self.assertIn('app.py', readme)  # Files listed
        self.assertIn('Installation', readme)
        self.assertIn('Usage', readme)

    def test_project_type_detection(self):
        """Test project type detection"""
        from core.readme_generator import ReadmeGenerator

        generator = ReadmeGenerator()

        # Flask detection
        ptype = generator._detect_project_type(['app.py', 'templates/index.html'], None)
        self.assertEqual(ptype, 'flask')

        # Static detection
        ptype = generator._detect_project_type(['index.html', 'style.css'], None)
        self.assertEqual(ptype, 'static')

    def test_structure_formatting(self):
        """Test file structure formatting"""
        from core.readme_generator import ReadmeGenerator

        generator = ReadmeGenerator()
        structure = generator._analyze_structure([
            'app.py',
            'models.py',
            'templates/index.html',
            'static/css/style.css',
            'static/js/app.js'
        ])

        formatted = generator._format_structure(structure)

        # Should have tree-like structure
        self.assertIn('├──', formatted)
        self.assertIn('templates/', formatted)
        self.assertIn('static/', formatted)


class TestToolExecutor(unittest.TestCase):
    """Tests for ToolExecutor enhancements"""

    def test_tool_aliases(self):
        """Test tool alias resolution"""
        from executor.tool_executor import ToolExecutor

        # Check that aliases are defined
        self.assertIn('database', ToolExecutor._tool_aliases)
        self.assertIn('bash', ToolExecutor._tool_aliases)
        self.assertIn('db', ToolExecutor._tool_aliases)

    def test_can_handle_with_alias(self):
        """Test can_handle_directly with aliases"""
        from executor.tool_executor import ToolExecutor
        from unittest.mock import Mock

        # Create mock dependencies
        mock_git = Mock()
        mock_shell = Mock()
        mock_files = Mock()
        mock_perms = Mock()

        executor = ToolExecutor(mock_git, mock_shell, mock_files, mock_perms)

        # Should handle both direct and aliased tools
        self.assertTrue(executor.can_handle_directly('git'))
        self.assertTrue(executor.can_handle_directly('bash'))  # Alias for shell
        self.assertTrue(executor.can_handle_directly('db'))    # Alias for sqlite

    def test_tool_help(self):
        """Test tool help information"""
        from executor.tool_executor import ToolExecutor
        from unittest.mock import Mock

        executor = ToolExecutor(Mock(), Mock(), Mock(), Mock())

        # Get help for known tools
        git_help = executor.get_tool_help('git')
        self.assertIn('description', git_help)
        self.assertIn('actions', git_help)

        # Get help for alias
        bash_help = executor.get_tool_help('bash')
        self.assertIn('description', bash_help)

        # Unknown tool
        unknown = executor.get_tool_help('unknown_tool')
        self.assertIn('error', unknown)


class TestModelLifecycle(unittest.TestCase):
    """Tests for ModelLifecycleManager enhancements"""

    def test_loading_time_estimate(self):
        """Test model loading time estimation"""
        from models.lifecycle import ModelLifecycleManager, ModelRole
        from unittest.mock import Mock

        mock_config = Mock()
        mock_config.models = {}
        mock_config.model_dir = Path('.')
        mock_config.memory_budget_mb = 6000

        manager = ModelLifecycleManager(mock_config)

        # Not loaded - should return estimate
        estimate = manager.get_loading_time_estimate(ModelRole.CODER)
        self.assertGreater(estimate, 0)

    def test_generation_time_estimate(self):
        """Test generation time estimation"""
        from models.lifecycle import ModelLifecycleManager, ModelRole
        from unittest.mock import Mock

        mock_config = Mock()
        mock_config.models = {}
        mock_config.model_dir = Path('.')
        mock_config.memory_budget_mb = 6000

        manager = ModelLifecycleManager(mock_config)

        # Estimate for 100 tokens
        estimate = manager.get_generation_time_estimate(ModelRole.CODER, 100)
        self.assertGreater(estimate, 0)
        # At 5 tok/s, 100 tokens = 20 seconds
        self.assertAlmostEqual(estimate, 20.0, delta=5)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
