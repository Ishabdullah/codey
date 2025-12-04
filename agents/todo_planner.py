"""Todo and task planning agent"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class TodoPlanner:
    """Plans and manages tasks from natural language requests"""

    def __init__(self, config, model_manager, perplexity_api=None):
        self.config = config
        self.model = model_manager
        self.perplexity = perplexity_api
        self.todos_file = config.memory_dir / "todos.json"
        self.todos = self._load_todos()

    def _load_todos(self) -> List[Dict[str, Any]]:
        """Load todos from disk"""
        if self.todos_file.exists():
            try:
                with open(self.todos_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load todos: {e}")
                return []
        return []

    def _save_todos(self):
        """Save todos to disk"""
        try:
            with open(self.todos_file, 'w') as f:
                json.dump(self.todos, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save todos: {e}")

    def create_plan(self, request: str) -> Dict[str, Any]:
        """Create a structured plan from natural language request"""
        # Use Perplexity to enhance understanding if available
        context = None
        if self.perplexity:
            research = self.perplexity.research_topic(
                f"How to implement: {request}",
                context="Break this into specific development steps"
            )
            context = research

        # Generate plan using local model with optional Perplexity context
        prompt = self._build_planning_prompt(request, context)

        try:
            plan_text = self.model.generate(prompt, max_tokens=1024, temperature=0.3)
            todos = self._parse_plan(plan_text, request)

            # Save todos
            self.todos.extend(todos)
            self._save_todos()

            return {
                'success': True,
                'todos': todos,
                'total_tasks': len(todos),
                'research_used': context is not None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'todos': []
            }

    def _build_planning_prompt(self, request: str, context: Optional[str]) -> str:
        """Build prompt for task planning"""
        prompt = f"""You are a development task planner. Break down this request into specific, actionable steps.

Request: {request}

"""
        if context:
            prompt += f"Research context:\n{context}\n\n"

        prompt += """Create a numbered list of specific tasks. For each task, specify:
1. The action (create, edit, research, etc.)
2. The target file(s) if applicable
3. What needs to be done

Format each task as:
[number]. [action] [file]: [description]

Example:
1. create utils/api.py: API client for stock data
2. edit main.py: Add stock scanning function
3. research: Best Python stock APIs

Tasks:
"""
        return prompt

    def _parse_plan(self, plan_text: str, original_request: str) -> List[Dict[str, Any]]:
        """Parse plan text into structured todos"""
        todos = []
        lines = plan_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or not line[0].isdigit():
                continue

            # Parse task
            task = self._parse_task_line(line)
            if task:
                task['request'] = original_request
                task['created'] = datetime.now().isoformat()
                task['status'] = 'pending'
                todos.append(task)

        return todos

    def _parse_task_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single task line"""
        import re

        # Remove number prefix
        line = re.sub(r'^\d+[\.\)]\s*', '', line)

        # Extract action
        actions = ['create', 'edit', 'delete', 'research', 'debug', 'test', 'refactor']
        action = None
        for act in actions:
            if line.lower().startswith(act):
                action = act
                break

        if not action:
            action = 'general'

        # Extract file if present
        file_match = re.search(r'([a-zA-Z0-9_/\.-]+\.[a-zA-Z]+)', line)
        target_file = file_match.group(1) if file_match else None

        # Extract description (everything after file or action)
        if target_file:
            parts = line.split(target_file, 1)
            description = parts[1].strip().lstrip(':').strip() if len(parts) > 1 else line
        else:
            description = line

        return {
            'action': action,
            'file': target_file,
            'description': description,
            'dependencies': [],
            'notes': None
        }

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get the next pending task"""
        for todo in self.todos:
            if todo['status'] == 'pending':
                return todo
        return None

    def mark_completed(self, task_id: int):
        """Mark a task as completed"""
        if 0 <= task_id < len(self.todos):
            self.todos[task_id]['status'] = 'completed'
            self.todos[task_id]['completed'] = datetime.now().isoformat()
            self._save_todos()

    def mark_failed(self, task_id: int, error: str):
        """Mark a task as failed"""
        if 0 <= task_id < len(self.todos):
            self.todos[task_id]['status'] = 'failed'
            self.todos[task_id]['error'] = error
            self._save_todos()

    def add_note(self, task_id: int, note: str):
        """Add a note to a task"""
        if 0 <= task_id < len(self.todos):
            if 'notes' not in self.todos[task_id] or self.todos[task_id]['notes'] is None:
                self.todos[task_id]['notes'] = []
            self.todos[task_id]['notes'].append({
                'timestamp': datetime.now().isoformat(),
                'note': note
            })
            self._save_todos()

    def get_all_todos(self) -> List[Dict[str, Any]]:
        """Get all todos"""
        return self.todos

    def get_pending_todos(self) -> List[Dict[str, Any]]:
        """Get pending todos"""
        return [t for t in self.todos if t['status'] == 'pending']

    def clear_completed(self):
        """Remove completed todos"""
        self.todos = [t for t in self.todos if t['status'] != 'completed']
        self._save_todos()

    def clear_all(self):
        """Clear all todos"""
        self.todos = []
        self._save_todos()
