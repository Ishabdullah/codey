"""Chunked Task Executor - Breaks complex tasks into manageable chunks

This module addresses the 120-second timeout issue on CPU-only hardware by:
1. Breaking large tasks into smaller, independently executable chunks
2. Setting appropriate max_tokens limits per chunk type
3. Providing progress tracking and incremental output
4. Supporting pause/resume for long-running operations

Part of Phase 6: CPU Optimization
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Generator
from enum import Enum
from pathlib import Path
import time
import json


class ChunkType(Enum):
    """Type of code generation chunk"""
    BACKEND_SETUP = "backend_setup"          # Flask/FastAPI app setup (~200 tokens)
    BACKEND_ROUTES = "backend_routes"        # API routes (~300 tokens per route)
    BACKEND_MODELS = "backend_models"        # Database models (~200 tokens)
    FRONTEND_HTML = "frontend_html"          # HTML template (~300 tokens)
    FRONTEND_CSS = "frontend_css"            # CSS styles (~200 tokens)
    FRONTEND_JS = "frontend_js"              # JavaScript logic (~300 tokens)
    DATABASE_SCHEMA = "database_schema"      # SQL schema (~150 tokens)
    DATABASE_INIT = "database_init"          # DB initialization (~100 tokens)
    CONFIG_FILE = "config_file"              # Config/env files (~100 tokens)
    README = "readme"                        # README.md (~200 tokens)
    TESTS = "tests"                          # Unit tests (~300 tokens)
    SINGLE_FILE = "single_file"              # Single file generation (~400 tokens)
    UTILITY = "utility"                      # Helper/utility code (~200 tokens)


@dataclass
class CodeChunk:
    """Represents a single chunk of code to generate"""
    chunk_id: str
    chunk_type: ChunkType
    description: str
    filename: str
    dependencies: List[str] = field(default_factory=list)  # chunk_ids that must complete first
    max_tokens: int = 400
    context: Optional[str] = None  # Context from previous chunks
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    generation_time: float = 0.0


@dataclass
class ChunkedPlan:
    """Complete plan for chunked code generation"""
    task_description: str
    chunks: List[CodeChunk]
    execution_order: List[str]  # chunk_ids in execution order
    estimated_total_time: float = 0.0  # Estimated time in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProgressCallback:
    """Callback interface for progress updates"""

    def on_chunk_start(self, chunk: CodeChunk, index: int, total: int):
        """Called when a chunk starts processing"""
        pass

    def on_chunk_complete(self, chunk: CodeChunk, index: int, total: int):
        """Called when a chunk completes"""
        pass

    def on_chunk_error(self, chunk: CodeChunk, error: str):
        """Called when a chunk fails"""
        pass

    def on_tokens_generated(self, tokens: int, chunk: CodeChunk):
        """Called periodically during generation (for streaming effect)"""
        pass


class ConsoleProgressCallback(ProgressCallback):
    """Default progress callback that prints to console"""

    def on_chunk_start(self, chunk: CodeChunk, index: int, total: int):
        print(f"\n⚙️  [{index}/{total}] Generating: {chunk.description}")
        print(f"   File: {chunk.filename} | Max tokens: {chunk.max_tokens}")

    def on_chunk_complete(self, chunk: CodeChunk, index: int, total: int):
        print(f"   ✓ Completed in {chunk.generation_time:.1f}s")

    def on_chunk_error(self, chunk: CodeChunk, error: str):
        print(f"   ✗ Failed: {error}")

    def on_tokens_generated(self, tokens: int, chunk: CodeChunk):
        # Print a dot for every 50 tokens to show progress
        if tokens % 50 == 0:
            print(".", end="", flush=True)


class ChunkedTaskExecutor:
    """Executes complex tasks by breaking them into chunks

    This executor is designed for CPU-only hardware where:
    - Token generation is slow (~5-10 tokens/sec)
    - Large generations hit timeout limits
    - Memory is constrained

    Strategy:
    1. Analyze task and decompose into chunks
    2. Set appropriate max_tokens per chunk (200-400 tokens)
    3. Generate each chunk with progress tracking
    4. Combine chunks into final output
    """

    # Token budgets per chunk type (conservative for CPU)
    TOKEN_BUDGETS = {
        ChunkType.BACKEND_SETUP: 256,
        ChunkType.BACKEND_ROUTES: 384,
        ChunkType.BACKEND_MODELS: 256,
        ChunkType.FRONTEND_HTML: 384,
        ChunkType.FRONTEND_CSS: 256,
        ChunkType.FRONTEND_JS: 384,
        ChunkType.DATABASE_SCHEMA: 192,
        ChunkType.DATABASE_INIT: 128,
        ChunkType.CONFIG_FILE: 128,
        ChunkType.README: 256,
        ChunkType.TESTS: 384,
        ChunkType.SINGLE_FILE: 512,
        ChunkType.UTILITY: 256,
    }

    # Estimated generation time per token (seconds) on CPU
    TOKENS_PER_SECOND_CPU = 5.0

    def __init__(self, coder_model=None, file_tools=None):
        """Initialize chunked executor

        Args:
            coder_model: PrimaryCoder model instance (can be set later)
            file_tools: FileTools instance for saving files
        """
        self.coder = coder_model
        self.file_tools = file_tools
        self.progress_callback = ConsoleProgressCallback()
        self._current_plan: Optional[ChunkedPlan] = None

    def set_coder(self, coder_model):
        """Set or update the coder model"""
        self.coder = coder_model

    def set_progress_callback(self, callback: ProgressCallback):
        """Set custom progress callback"""
        self.progress_callback = callback

    def analyze_task(self, task_description: str) -> ChunkedPlan:
        """Analyze a task and create a chunked execution plan

        Args:
            task_description: Full description of what to generate

        Returns:
            ChunkedPlan with all chunks and dependencies
        """
        chunks = []
        task_lower = task_description.lower()

        # Detect full-stack app patterns
        is_fullstack = any(kw in task_lower for kw in [
            'full-stack', 'fullstack', 'full stack',
            'frontend and backend', 'backend and frontend',
            'web app', 'web application'
        ])

        is_backend = any(kw in task_lower for kw in [
            'flask', 'fastapi', 'django', 'backend', 'api', 'server',
            'rest api', 'restful'
        ])

        is_frontend = any(kw in task_lower for kw in [
            'html', 'frontend', 'react', 'vue', 'angular', 'webpage',
            'website', 'ui', 'user interface'
        ])

        has_database = any(kw in task_lower for kw in [
            'database', 'sqlite', 'postgres', 'mysql', 'db', 'sql',
            'crud', 'data storage', 'persistence'
        ])

        # Generate chunks based on detected patterns
        if is_fullstack or (is_backend and is_frontend):
            chunks = self._plan_fullstack_app(task_description, has_database)
        elif is_backend:
            chunks = self._plan_backend_app(task_description, has_database)
        elif is_frontend:
            chunks = self._plan_frontend_app(task_description)
        else:
            # Single file or simple task
            chunks = self._plan_single_file(task_description)

        # Calculate execution order respecting dependencies
        execution_order = self._topological_sort(chunks)

        # Estimate total time
        total_tokens = sum(c.max_tokens for c in chunks)
        estimated_time = total_tokens / self.TOKENS_PER_SECOND_CPU

        plan = ChunkedPlan(
            task_description=task_description,
            chunks=chunks,
            execution_order=execution_order,
            estimated_total_time=estimated_time,
            metadata={
                'is_fullstack': is_fullstack,
                'is_backend': is_backend,
                'is_frontend': is_frontend,
                'has_database': has_database,
                'total_chunks': len(chunks),
                'total_tokens': total_tokens
            }
        )

        self._current_plan = plan
        return plan

    def _plan_fullstack_app(self, task: str, has_database: bool) -> List[CodeChunk]:
        """Plan chunks for a full-stack application"""
        chunks = []

        # 1. Database schema (if needed) - no dependencies
        if has_database:
            chunks.append(CodeChunk(
                chunk_id="db_schema",
                chunk_type=ChunkType.DATABASE_SCHEMA,
                description="Database schema and models",
                filename="models.py",
                max_tokens=self.TOKEN_BUDGETS[ChunkType.DATABASE_SCHEMA],
                dependencies=[]
            ))

        # 2. Backend setup - depends on db_schema if exists
        backend_deps = ["db_schema"] if has_database else []
        chunks.append(CodeChunk(
            chunk_id="backend_setup",
            chunk_type=ChunkType.BACKEND_SETUP,
            description="Backend app initialization",
            filename="app.py",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.BACKEND_SETUP],
            dependencies=backend_deps
        ))

        # 3. Backend routes - depends on backend_setup
        chunks.append(CodeChunk(
            chunk_id="backend_routes",
            chunk_type=ChunkType.BACKEND_ROUTES,
            description="API routes and endpoints",
            filename="routes.py",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.BACKEND_ROUTES],
            dependencies=["backend_setup"]
        ))

        # 4. Database initialization - depends on db_schema
        if has_database:
            chunks.append(CodeChunk(
                chunk_id="db_init",
                chunk_type=ChunkType.DATABASE_INIT,
                description="Database initialization script",
                filename="init_db.py",
                max_tokens=self.TOKEN_BUDGETS[ChunkType.DATABASE_INIT],
                dependencies=["db_schema"]
            ))

        # 5. Frontend HTML - can start after backend_setup is known
        chunks.append(CodeChunk(
            chunk_id="frontend_html",
            chunk_type=ChunkType.FRONTEND_HTML,
            description="HTML template",
            filename="templates/index.html",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.FRONTEND_HTML],
            dependencies=["backend_routes"]  # Need to know API endpoints
        ))

        # 6. Frontend CSS - no strict dependency, but logically after HTML
        chunks.append(CodeChunk(
            chunk_id="frontend_css",
            chunk_type=ChunkType.FRONTEND_CSS,
            description="CSS styles",
            filename="static/css/style.css",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.FRONTEND_CSS],
            dependencies=[]  # Can generate in parallel conceptually
        ))

        # 7. Frontend JavaScript - depends on HTML structure and API routes
        chunks.append(CodeChunk(
            chunk_id="frontend_js",
            chunk_type=ChunkType.FRONTEND_JS,
            description="JavaScript client logic",
            filename="static/js/app.js",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.FRONTEND_JS],
            dependencies=["frontend_html", "backend_routes"]
        ))

        # 8. README - depends on everything to document properly
        all_deps = [c.chunk_id for c in chunks]
        chunks.append(CodeChunk(
            chunk_id="readme",
            chunk_type=ChunkType.README,
            description="README documentation",
            filename="README.md",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.README],
            dependencies=all_deps
        ))

        return chunks

    def _plan_backend_app(self, task: str, has_database: bool) -> List[CodeChunk]:
        """Plan chunks for a backend-only application"""
        chunks = []

        if has_database:
            chunks.append(CodeChunk(
                chunk_id="db_schema",
                chunk_type=ChunkType.DATABASE_SCHEMA,
                description="Database schema and models",
                filename="models.py",
                max_tokens=self.TOKEN_BUDGETS[ChunkType.DATABASE_SCHEMA],
                dependencies=[]
            ))

        backend_deps = ["db_schema"] if has_database else []
        chunks.append(CodeChunk(
            chunk_id="backend_main",
            chunk_type=ChunkType.BACKEND_SETUP,
            description="Backend application",
            filename="app.py",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.BACKEND_SETUP] + self.TOKEN_BUDGETS[ChunkType.BACKEND_ROUTES],
            dependencies=backend_deps
        ))

        # README
        chunks.append(CodeChunk(
            chunk_id="readme",
            chunk_type=ChunkType.README,
            description="README documentation",
            filename="README.md",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.README],
            dependencies=["backend_main"]
        ))

        return chunks

    def _plan_frontend_app(self, task: str) -> List[CodeChunk]:
        """Plan chunks for a frontend-only application"""
        chunks = []

        chunks.append(CodeChunk(
            chunk_id="frontend_html",
            chunk_type=ChunkType.FRONTEND_HTML,
            description="HTML page",
            filename="index.html",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.FRONTEND_HTML],
            dependencies=[]
        ))

        chunks.append(CodeChunk(
            chunk_id="frontend_css",
            chunk_type=ChunkType.FRONTEND_CSS,
            description="CSS styles",
            filename="style.css",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.FRONTEND_CSS],
            dependencies=[]
        ))

        chunks.append(CodeChunk(
            chunk_id="frontend_js",
            chunk_type=ChunkType.FRONTEND_JS,
            description="JavaScript logic",
            filename="script.js",
            max_tokens=self.TOKEN_BUDGETS[ChunkType.FRONTEND_JS],
            dependencies=["frontend_html"]
        ))

        return chunks

    def _plan_single_file(self, task: str) -> List[CodeChunk]:
        """Plan for single file generation"""
        # Infer filename and language
        filename = self._infer_filename(task)

        return [CodeChunk(
            chunk_id="main",
            chunk_type=ChunkType.SINGLE_FILE,
            description="Main code file",
            filename=filename,
            max_tokens=self.TOKEN_BUDGETS[ChunkType.SINGLE_FILE],
            dependencies=[]
        )]

    def _infer_filename(self, task: str) -> str:
        """Infer output filename from task description"""
        task_lower = task.lower()

        # Check for explicit filename
        import re
        match = re.search(r'([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)', task)
        if match:
            return match.group(1)

        # Infer from keywords
        if 'calculator' in task_lower:
            return 'calculator.py'
        elif 'game' in task_lower:
            return 'game.py'
        elif 'server' in task_lower or 'api' in task_lower:
            return 'app.py'
        elif 'test' in task_lower:
            return 'test_main.py'

        return 'main.py'

    def _topological_sort(self, chunks: List[CodeChunk]) -> List[str]:
        """Sort chunks respecting dependencies"""
        # Build adjacency and in-degree maps
        in_degree = {c.chunk_id: 0 for c in chunks}
        dependents = {c.chunk_id: [] for c in chunks}
        chunk_map = {c.chunk_id: c for c in chunks}

        for chunk in chunks:
            for dep in chunk.dependencies:
                if dep in dependents:
                    dependents[dep].append(chunk.chunk_id)
                    in_degree[chunk.chunk_id] += 1

        # Kahn's algorithm
        queue = [cid for cid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for dependent in dependents[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result

    def execute_plan(self, plan: ChunkedPlan, context: str = "") -> Dict[str, Any]:
        """Execute a chunked plan

        Args:
            plan: ChunkedPlan to execute
            context: Additional context for generation

        Returns:
            Dict with results and generated files
        """
        if not self.coder:
            return {
                'success': False,
                'error': 'Coder model not set. Call set_coder() first.'
            }

        results = {}
        generated_files = {}
        failed_chunks = []
        completed_chunks = []

        chunk_map = {c.chunk_id: c for c in plan.chunks}
        total = len(plan.execution_order)

        print(f"\n📋 Executing chunked plan: {total} chunks")
        print(f"   Estimated time: {plan.estimated_total_time:.0f}s")
        print(f"   Total tokens: {plan.metadata.get('total_tokens', 0)}")
        print("-" * 50)

        for idx, chunk_id in enumerate(plan.execution_order, 1):
            chunk = chunk_map[chunk_id]

            # Check if dependencies are satisfied
            deps_satisfied = all(
                chunk_map[dep].status == "completed"
                for dep in chunk.dependencies
                if dep in chunk_map
            )

            if not deps_satisfied:
                chunk.status = "skipped"
                chunk.error = "Dependencies not satisfied"
                failed_chunks.append(chunk_id)
                continue

            # Build context from completed chunks
            chunk_context = context
            for dep_id in chunk.dependencies:
                if dep_id in chunk_map and chunk_map[dep_id].result:
                    chunk_context += f"\n\n# From {chunk_map[dep_id].filename}:\n"
                    chunk_context += chunk_map[dep_id].result[:500]  # First 500 chars

            chunk.context = chunk_context
            chunk.status = "in_progress"

            # Notify progress
            self.progress_callback.on_chunk_start(chunk, idx, total)

            # Generate code for this chunk
            start_time = time.time()
            try:
                result = self._generate_chunk(chunk, plan.task_description)
                chunk.generation_time = time.time() - start_time

                if result['success']:
                    chunk.status = "completed"
                    chunk.result = result['code']
                    generated_files[chunk.filename] = result['code']
                    completed_chunks.append(chunk_id)
                    self.progress_callback.on_chunk_complete(chunk, idx, total)

                    # Save file if file_tools available
                    if self.file_tools:
                        self._save_chunk_file(chunk)
                else:
                    chunk.status = "failed"
                    chunk.error = result.get('error', 'Unknown error')
                    failed_chunks.append(chunk_id)
                    self.progress_callback.on_chunk_error(chunk, chunk.error)

            except Exception as e:
                chunk.generation_time = time.time() - start_time
                chunk.status = "failed"
                chunk.error = str(e)
                failed_chunks.append(chunk_id)
                self.progress_callback.on_chunk_error(chunk, str(e))

            results[chunk_id] = {
                'status': chunk.status,
                'filename': chunk.filename,
                'generation_time': chunk.generation_time,
                'error': chunk.error
            }

        # Summary
        success = len(failed_chunks) == 0
        total_time = sum(c.generation_time for c in plan.chunks)

        print("\n" + "=" * 50)
        print(f"{'✓' if success else '✗'} Execution {'completed' if success else 'partial'}")
        print(f"   Completed: {len(completed_chunks)}/{total} chunks")
        print(f"   Total time: {total_time:.1f}s")
        if failed_chunks:
            print(f"   Failed: {', '.join(failed_chunks)}")

        return {
            'success': success,
            'files': generated_files,
            'results': results,
            'completed_chunks': completed_chunks,
            'failed_chunks': failed_chunks,
            'total_time': total_time
        }

    def _generate_chunk(self, chunk: CodeChunk, task_description: str) -> Dict[str, Any]:
        """Generate code for a single chunk

        Args:
            chunk: CodeChunk to generate
            task_description: Overall task description

        Returns:
            Dict with success, code, and error
        """
        # Build chunk-specific prompt
        prompt = self._build_chunk_prompt(chunk, task_description)

        try:
            # Generate with chunk's token limit
            response = self.coder.generate(
                prompt,
                max_tokens=chunk.max_tokens,
                temperature=0.3,
                stop=["</s>", "\n\n\n", "User:", "Human:", "<|im_end|>", "```\n\n"]
            )

            # Extract code from response
            code = self._extract_code(response, chunk)

            if code:
                return {'success': True, 'code': code}
            else:
                return {'success': False, 'error': 'No code extracted from response'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _build_chunk_prompt(self, chunk: CodeChunk, task_description: str) -> str:
        """Build prompt for a specific chunk"""
        prompts = {
            ChunkType.BACKEND_SETUP: f"""Write Python Flask/FastAPI app initialization.
Task: {task_description}
File: {chunk.filename}
{f'Context: {chunk.context[:300]}' if chunk.context else ''}

Requirements:
- Import statements
- App initialization
- Basic configuration

Code:
```python
""",
            ChunkType.BACKEND_ROUTES: f"""Write API routes/endpoints.
Task: {task_description}
File: {chunk.filename}
{f'Context: {chunk.context[:300]}' if chunk.context else ''}

Requirements:
- Route handlers
- Request/response handling
- Error handling

Code:
```python
""",
            ChunkType.DATABASE_SCHEMA: f"""Write database schema/models.
Task: {task_description}
File: {chunk.filename}

Requirements:
- SQLite/SQLAlchemy models
- Table definitions
- Relationships

Code:
```python
""",
            ChunkType.DATABASE_INIT: f"""Write database initialization.
Task: {task_description}
File: {chunk.filename}
{f'Context: {chunk.context[:200]}' if chunk.context else ''}

Requirements:
- Create tables
- Initialize database

Code:
```python
""",
            ChunkType.FRONTEND_HTML: f"""Write HTML template.
Task: {task_description}
File: {chunk.filename}
{f'Context: {chunk.context[:200]}' if chunk.context else ''}

Requirements:
- Semantic HTML5
- Form elements
- Script/style links

Code:
```html
""",
            ChunkType.FRONTEND_CSS: f"""Write CSS styles.
Task: {task_description}
File: {chunk.filename}

Requirements:
- Modern CSS
- Responsive design
- Clean layout

Code:
```css
""",
            ChunkType.FRONTEND_JS: f"""Write JavaScript client code.
Task: {task_description}
File: {chunk.filename}
{f'Context: {chunk.context[:200]}' if chunk.context else ''}

Requirements:
- Event handlers
- API calls (fetch)
- DOM manipulation

Code:
```javascript
""",
            ChunkType.README: f"""Write README.md documentation.
Task: {task_description}
Files created: {chunk.context if chunk.context else 'app files'}

Requirements:
- Project description
- Setup instructions
- Usage examples

Code:
```markdown
""",
            ChunkType.SINGLE_FILE: f"""Write code: {task_description}
File: {chunk.filename}

Code:
```python
""",
        }

        return prompts.get(chunk.chunk_type, prompts[ChunkType.SINGLE_FILE])

    def _extract_code(self, response: str, chunk: CodeChunk) -> Optional[str]:
        """Extract code from model response"""
        import re

        # Try to extract code block
        patterns = [
            r'```\w*\n(.*?)```',  # Standard code block
            r'```\w*\n(.*?)$',     # Unclosed code block
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()

        # If no code block, use entire response (might be raw code)
        if response.strip():
            return response.strip()

        return None

    def _save_chunk_file(self, chunk: CodeChunk) -> bool:
        """Save generated chunk to file"""
        if not self.file_tools or not chunk.result:
            return False

        try:
            # Create parent directories if needed
            filepath = Path(chunk.filename)
            if filepath.parent != Path('.'):
                # Use shell to create directories
                pass  # file_tools.write_file handles this

            result = self.file_tools.write_file(
                chunk.filename,
                chunk.result,
                overwrite=True
            )
            return result.get('success', False)
        except Exception as e:
            print(f"   ⚠️  Failed to save {chunk.filename}: {e}")
            return False

    def get_plan_summary(self, plan: ChunkedPlan) -> str:
        """Get human-readable summary of a plan"""
        lines = [
            f"📋 Chunked Execution Plan",
            f"   Task: {plan.task_description[:50]}...",
            f"   Chunks: {len(plan.chunks)}",
            f"   Estimated time: {plan.estimated_total_time:.0f}s",
            "",
            "   Execution order:"
        ]

        for i, chunk_id in enumerate(plan.execution_order, 1):
            chunk = next(c for c in plan.chunks if c.chunk_id == chunk_id)
            deps = f" (depends on: {', '.join(chunk.dependencies)})" if chunk.dependencies else ""
            lines.append(f"   {i}. [{chunk.chunk_type.value}] {chunk.filename}{deps}")

        return "\n".join(lines)


def estimate_generation_time(task_description: str, tokens_per_second: float = 5.0) -> float:
    """Estimate generation time for a task on CPU

    Args:
        task_description: Task to analyze
        tokens_per_second: Expected generation speed (default: 5 for CPU)

    Returns:
        Estimated time in seconds
    """
    executor = ChunkedTaskExecutor()
    plan = executor.analyze_task(task_description)
    return plan.estimated_total_time
