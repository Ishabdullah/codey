"""Enhanced Codey engine with hybrid reasoning and advanced capabilities"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import config
from models.manager import ModelManager
from core.tools import FileTools
from core.parser import CommandParser
from agents.coding_agent import CodingAgent
from agents.perplexity_api import PerplexityAPI
from agents.todo_planner import TodoPlanner
from agents.debug_agent import DebugAgent
from memory.store import MemoryStore

class CodeyEngineV2:
    """Enhanced engine with hybrid reasoning and autonomous capabilities"""

    def __init__(self):
        self.config = config
        self.model_manager = ModelManager(self.config)
        self.file_tools = FileTools(self.config)
        self.parser = CommandParser()
        self.memory = MemoryStore(self.config)

        # Initialize Perplexity if enabled
        self.perplexity = None
        if self.config.use_perplexity and self.config.perplexity_api_key:
            self.perplexity = PerplexityAPI(self.config.perplexity_api_key)

        # Initialize agents
        self.coding_agent = CodingAgent(self.model_manager, self.file_tools, self.config)
        self.todo_planner = TodoPlanner(self.config, self.model_manager, self.perplexity)
        self.debug_agent = DebugAgent(self.model_manager, self.file_tools, self.perplexity)

        self.memory.start_session()

    def process_command(self, user_input):
        """Process a natural language command with hybrid reasoning"""
        if not user_input or not user_input.strip():
            return "Please enter a command."

        # Check for special commands first
        if user_input.lower().startswith('plan '):
            return self._handle_plan_command(user_input[5:])

        if user_input.lower() == 'execute plan':
            return self._execute_plan()

        if user_input.lower() == 'show plan':
            return self._show_plan()

        if user_input.lower().startswith('debug '):
            return self._handle_debug_command(user_input[6:])

        if user_input.lower().startswith('ask '):
            return self._ask_perplexity(user_input[4:])

        # Parse the command
        parsed = self.parser.parse(user_input)
        action = parsed['action']
        filename = parsed['filename']
        instructions = parsed['instructions']

        # Determine if we should use hybrid reasoning
        use_hybrid = self._should_use_hybrid(user_input, action)

        response = None

        try:
            if action == 'create':
                response = self._handle_create(filename, instructions, user_input, use_hybrid)

            elif action == 'edit':
                response = self._handle_edit(filename, instructions, use_hybrid)

            elif action == 'read':
                response = self._handle_read(filename)

            elif action == 'delete':
                response = self._handle_delete(filename)

            elif action == 'list':
                response = self._handle_list()

            elif action == 'general':
                response = self._handle_general(user_input, use_hybrid)

            else:
                response = "I'm not sure how to handle that command. Try: create, edit, read, delete, list files, plan, debug, or ask."

        except Exception as e:
            response = f"An error occurred: {str(e)}"

        # Store in memory
        self.memory.add_conversation(user_input, response, action)

        return response

    def _should_use_hybrid(self, user_input, action):
        """Determine if hybrid reasoning (Perplexity) should be used"""
        if not self.config.hybrid_mode or not self.perplexity:
            return False

        # Complex indicators
        complex_keywords = [
            'best way', 'how to', 'what is the', 'implement',
            'algorithm', 'optimize', 'pattern', 'design',
            'framework', 'library', 'api', 'authenticate',
            'database', 'security', 'performance'
        ]

        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in complex_keywords)

    def _handle_create(self, filename, instructions, user_input, use_hybrid):
        """Handle file creation with optional hybrid reasoning"""
        if not filename:
            filename = self.parser.extract_filename(user_input)
            if not filename:
                return "I couldn't determine the filename. Please specify a filename."

        # If hybrid mode, get suggestions from Perplexity
        perplexity_code = None
        if use_hybrid:
            print("[Hybrid Mode] Consulting Perplexity for best practices...")
            extension = filename.split('.')[-1] if '.' in filename else 'py'
            language = self.coding_agent._infer_language(extension)

            perplexity_code = self.perplexity.get_code_from_perplexity(instructions, language)
            if perplexity_code:
                print("[Hybrid Mode] Received Perplexity suggestion")

        # Generate code (incorporate Perplexity if available)
        if perplexity_code and self.config.use_perplexity:
            # Use Perplexity code directly
            result = self.file_tools.write_file(filename, perplexity_code)
            result['content'] = perplexity_code
        else:
            result = self.coding_agent.create_file(filename, instructions)

        if result['success']:
            self.memory.add_file_action(filename, 'created', {'instructions': instructions})
            response = f"Created {filename}"
            if use_hybrid:
                response += " (with Perplexity assistance)"
            if self.config.require_confirmation:
                response += f"\n\n{self._show_preview(result['content'])}"
        else:
            response = f"Error: {result['error']}"

        return response

    def _handle_edit(self, filename, instructions, use_hybrid):
        """Handle file editing with optional hybrid reasoning"""
        if not filename:
            return "Please specify which file to edit."

        result = self.coding_agent.edit_file(filename, instructions)

        if result['success']:
            self.memory.add_file_action(filename, 'edited', {'instructions': instructions})
            response = f"Updated {filename}"
            if result.get('backup'):
                response += f"\n(Backup: {result['backup']})"
            if self.config.require_confirmation:
                response += f"\n\n{self._show_preview(result['content'])}"
        else:
            response = f"Error: {result['error']}"

        return response

    def _handle_read(self, filename):
        """Handle file reading"""
        if not filename:
            return "Please specify which file to read."

        result = self.file_tools.read_file(filename)

        if result['success']:
            return f"Contents of {filename}:\n\n{result['content']}"
        else:
            return f"Error: {result['error']}"

    def _handle_delete(self, filename):
        """Handle file deletion"""
        if not filename:
            return "Please specify which file to delete."

        if self.config.require_confirmation:
            confirm = input(f"Delete {filename}? (yes/no): ")
            if confirm.lower() not in ['yes', 'y']:
                return "Delete cancelled."

        result = self.file_tools.delete_file(filename)

        if result['success']:
            self.memory.add_file_action(filename, 'deleted')
            response = f"Deleted {filename}"
            if result.get('backup'):
                response += f"\n(Backup: {result['backup']})"
        else:
            response = f"Error: {result['error']}"

        return response

    def _handle_list(self):
        """Handle file listing"""
        result = self.file_tools.list_files()

        if result['success']:
            if result['files']:
                return "Files in workspace:\n" + "\n".join(f"  - {f}" for f in result['files'])
            else:
                return "No files in workspace."
        else:
            return f"Error: {result['error']}"

    def _handle_general(self, query, use_hybrid):
        """Handle general queries with hybrid reasoning"""
        intent = self.parser.infer_intent(query)

        if intent == 'code_explanation':
            filename = self.parser.extract_filename(query)
            if filename:
                result = self.coding_agent.explain_code(filename)
                if result['success']:
                    return result['explanation']
                else:
                    return f"Error: {result['error']}"
            else:
                return "Which file would you like me to explain?"

        # Use hybrid reasoning for complex queries
        if use_hybrid and self.perplexity:
            print("[Hybrid Mode] Consulting Perplexity...")
            response = self.perplexity.ask_perplexity(query)
            if response:
                return response

        # Fall back to local model
        return self._local_query(query)

    def _local_query(self, query):
        """Handle query with local model"""
        prompt = f"""You are Codey, a helpful coding assistant. Answer concisely:

User: {query}

Codey:"""

        try:
            return self.model_manager.generate(prompt, max_tokens=512)
        except Exception as e:
            return f"Error: {str(e)}"

    def _handle_plan_command(self, request):
        """Create a plan for a complex task"""
        print("Creating plan...")
        result = self.todo_planner.create_plan(request)

        if result['success']:
            todos = result['todos']
            response = f"Created plan with {result['total_tasks']} tasks:\n\n"
            for i, todo in enumerate(todos, 1):
                file_info = f" [{todo['file']}]" if todo['file'] else ""
                response += f"{i}. {todo['action']}{file_info}: {todo['description']}\n"

            if result['research_used']:
                response += "\n(Plan enhanced with Perplexity research)"

            response += "\nUse 'execute plan' to run automatically or handle tasks manually."
            return response
        else:
            return f"Error creating plan: {result['error']}"

    def _show_plan(self):
        """Show current plan"""
        todos = self.todo_planner.get_all_todos()

        if not todos:
            return "No active plan."

        response = "Current plan:\n\n"
        for i, todo in enumerate(todos, 1):
            status_icon = "✓" if todo['status'] == 'completed' else ("✗" if todo['status'] == 'failed' else "○")
            file_info = f" [{todo['file']}]" if todo['file'] else ""
            response += f"{i}. {status_icon} {todo['action']}{file_info}: {todo['description']}\n"

        return response

    def _execute_plan(self):
        """Execute the current plan autonomously"""
        todos = self.todo_planner.get_pending_todos()

        if not todos:
            return "No pending tasks in plan."

        print(f"Executing plan with {len(todos)} tasks...\n")

        for i, todo in enumerate(todos):
            print(f"Task {i+1}/{len(todos)}: {todo['description']}")

            # Execute based on action
            try:
                if todo['action'] == 'create':
                    result = self.coding_agent.create_file(todo['file'], todo['description'])
                elif todo['action'] == 'edit':
                    result = self.coding_agent.edit_file(todo['file'], todo['description'])
                elif todo['action'] == 'research':
                    if self.perplexity:
                        research = self.perplexity.research_topic(todo['description'])
                        self.todo_planner.add_note(i, research)
                        result = {'success': True}
                    else:
                        result = {'success': False, 'error': 'Perplexity not available'}
                elif todo['action'] == 'debug':
                    result = self.debug_agent.auto_fix(todo['file'])
                else:
                    result = {'success': False, 'error': 'Unknown action'}

                if result['success']:
                    self.todo_planner.mark_completed(i)
                    print(f"  ✓ Completed\n")
                else:
                    self.todo_planner.mark_failed(i, result.get('error', 'Unknown error'))
                    print(f"  ✗ Failed: {result.get('error')}\n")

            except Exception as e:
                self.todo_planner.mark_failed(i, str(e))
                print(f"  ✗ Error: {str(e)}\n")

        return "Plan execution complete. Use 'show plan' to see results."

    def _handle_debug_command(self, filename):
        """Handle debugging command"""
        print(f"Analyzing {filename}...")

        result = self.debug_agent.analyze_file(filename)

        if result['success']:
            if result['issues']:
                response = f"Found {result['issue_count']} issue(s) in {filename}:\n\n"
                for issue in result['issues']:
                    line_info = f" (line {issue['line']})" if issue.get('line') else ""
                    response += f"  [{issue['severity'].upper()}]{line_info} {issue['message']}\n"

                response += "\nWould you like me to attempt fixes? (Use 'debug fix filename')"
            else:
                response = f"No issues found in {filename}"
        else:
            response = f"Error: {result['error']}"

        return response

    def _ask_perplexity(self, question):
        """Ask Perplexity a question directly"""
        if not self.perplexity:
            return "Perplexity API not available. Check configuration."

        print("Asking Perplexity...")
        response = self.perplexity.ask_perplexity(question)

        if response:
            return response
        else:
            return "Failed to get response from Perplexity."

    def _show_preview(self, content, max_lines=10):
        """Show a preview of file content"""
        lines = content.split('\n')
        if len(lines) <= max_lines:
            return f"Preview:\n{content}"
        else:
            preview = '\n'.join(lines[:max_lines])
            return f"Preview (first {max_lines} lines):\n{preview}\n... ({len(lines) - max_lines} more lines)"

    def shutdown(self):
        """Clean shutdown"""
        self.memory.save_memory()
        self.todo_planner._save_todos()
        self.model_manager.unload_model()
