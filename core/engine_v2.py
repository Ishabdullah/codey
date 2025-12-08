"""Enhanced Codey engine with hybrid reasoning and advanced capabilities - Claude Code Edition"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import config
from models.manager import ModelManager
from core.tools import FileTools
from core.parser import CommandParser
from core.permission_manager import PermissionManager
from core.git_manager import GitManager
from core.shell_manager import ShellManager
from agents.coding_agent import CodingAgent
from agents.perplexity_api import PerplexityAPI
from agents.todo_planner import TodoPlanner
from agents.debug_agent import DebugAgent
from memory.store import MemoryStore
from utils.cleanup import CleanupManager

class CodeyEngineV2:
    """Enhanced engine with hybrid reasoning, git, shell, and Claude Code-like capabilities"""

    def __init__(self):
        self.config = config

        # Initialize core managers
        self.permission_manager = PermissionManager(self.config)
        self.model_manager = ModelManager(self.config)
        self.file_tools = FileTools(self.config)
        self.parser = CommandParser()
        self.memory = MemoryStore(self.config)

        # Initialize Git and Shell managers
        self.git_manager = GitManager(self.permission_manager, self.config.workspace_dir)
        self.shell_manager = ShellManager(self.permission_manager, self.config.workspace_dir, self.config)

        # Initialize Perplexity if enabled
        self.perplexity = None
        if self.config.use_perplexity and self.config.perplexity_api_key:
            self.perplexity = PerplexityAPI(self.config.perplexity_api_key, self.config)

        # Initialize agents
        self.coding_agent = CodingAgent(self.model_manager, self.file_tools, self.config)
        self.todo_planner = TodoPlanner(self.config, self.model_manager, self.perplexity)
        self.debug_agent = DebugAgent(self.model_manager, self.file_tools, self.perplexity)

        # Initialize cleanup manager
        self.cleanup_manager = CleanupManager(self.config.workspace_dir)

        self.memory.start_session()

        # Show initialization info with profile details
        profile_info = self.config.get_profile_info()
        print(f"\n✓ Codey initialized - Claude Code Edition v2.1")
        print(f"✓ Profile: {profile_info['name']}")
        print(f"  └─ {profile_info['description']}")
        print(f"✓ Context: {self.config.context_size} tokens")
        print(f"✓ GPU layers: {self.config.n_gpu_layers}")
        print(f"✓ Threads: {self.config.n_threads}")
        print(f"✓ Git enabled: {self.config.git_enabled}")
        print(f"✓ Shell enabled: {self.config.shell_enabled}")

    def process_command(self, user_input):
        """Process a natural language command with hybrid reasoning"""
        if not user_input or not user_input.strip():
            return "Please enter a command."

        # IMPORTANT: Check for complex multi-step instruction FIRST
        # This prevents the model from generating responses before we detect complexity
        if self._is_complex_instruction(user_input):
            return self._handle_complex_instruction(user_input)

        # Check for special commands
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

        # Git commands
        if user_input.lower().startswith(('git ', 'clone ', 'commit ', 'push ', 'pull ')):
            return self._handle_git_command(user_input)

        # Shell commands
        if user_input.lower().startswith(('run ', 'execute ', 'install ', 'mkdir ')):
            return self._handle_shell_command(user_input)

        # System info
        if user_input.lower() in ['info', 'system info', 'model info']:
            return self._show_system_info()

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
        """Handle file creation with optional hybrid reasoning and permission check"""
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
            content = perplexity_code
        else:
            # Generate code first
            temp_result = self.coding_agent.create_file(filename, instructions)
            if not temp_result['success']:
                return f"Error: {temp_result['error']}"
            content = temp_result['content']

        # Request permission with preview
        if not self.permission_manager.request_file_creation(filename, content):
            return "Operation cancelled by user"

        # Write file
        result = self.file_tools.write_file(filename, content)
        result['content'] = content

        if result['success']:
            self.memory.add_file_action(filename, 'created', {'instructions': instructions})
            response = f"✓ Created {filename}"
            if use_hybrid:
                response += " (with Perplexity assistance)"
        else:
            response = f"✗ Error: {result['error']}"

        return response

    def _handle_edit(self, filename, instructions, use_hybrid):
        """Handle file editing with optional hybrid reasoning and permission check"""
        if not filename:
            return "Please specify which file to edit."

        # Generate edited content
        result = self.coding_agent.edit_file(filename, instructions)

        if not result['success']:
            return f"✗ Error: {result['error']}"

        # Request permission with preview
        backup_path = result.get('backup')
        if not self.permission_manager.request_file_edit(filename, result['content'], backup_path):
            return "Operation cancelled by user"

        # File has already been written by coding_agent, so just record it
        self.memory.add_file_action(filename, 'edited', {'instructions': instructions})
        response = f"✓ Updated {filename}"
        if result.get('backup'):
            response += f"\n(Backup: {result['backup']})"

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
        """Handle file deletion with permission check"""
        if not filename:
            return "Please specify which file to delete."

        # Request permission
        backup_path = f"{self.config.log_dir}/backups/{filename}.bak"
        if not self.permission_manager.request_file_deletion(filename, backup_path):
            return "Operation cancelled by user"

        result = self.file_tools.delete_file(filename)

        if result['success']:
            self.memory.add_file_action(filename, 'deleted')
            response = f"✓ Deleted {filename}"
            if result.get('backup'):
                response += f"\n(Backup: {result['backup']})"
        else:
            response = f"✗ Error: {result['error']}"

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

    def _handle_git_command(self, command):
        """Handle git operations"""
        cmd_lower = command.lower()

        try:
            # Clone repository
            if cmd_lower.startswith('clone '):
                parts = command.split()
                if len(parts) < 2:
                    return "Usage: clone <repo_url> [destination]"

                repo_url = parts[1]
                destination = parts[2] if len(parts) > 2 else None

                result = self.git_manager.clone_repository(repo_url, destination)

                if result['success']:
                    return f"✓ {result['message']}"
                else:
                    return f"✗ {result['error']}"

            # Git status
            elif cmd_lower in ['git status', 'status']:
                result = self.git_manager.git_status()

                if result['success']:
                    if result['clean']:
                        return "✓ Working directory is clean"
                    else:
                        response = "Git status:\n"
                        if result['staged']:
                            response += f"\nStaged ({len(result['staged'])}):\n"
                            for f in result['staged'][:10]:
                                response += f"  + {f}\n"
                        if result['modified']:
                            response += f"\nModified ({len(result['modified'])}):\n"
                            for f in result['modified'][:10]:
                                response += f"  M {f}\n"
                        if result['untracked']:
                            response += f"\nUntracked ({len(result['untracked'])}):\n"
                            for f in result['untracked'][:10]:
                                response += f"  ? {f}\n"
                        return response
                else:
                    return f"✗ {result['error']}"

            # Commit
            elif cmd_lower.startswith('commit '):
                # Extract message
                if ' message ' in cmd_lower or ' with message ' in cmd_lower:
                    parts = command.split(' message ', 1)
                    if len(parts) == 1:
                        parts = command.split(' with message ', 1)
                    message = parts[1].strip('"\'')
                else:
                    message = command.split('commit ', 1)[1].strip('"\'')

                result = self.git_manager.git_commit(message)

                if result['success']:
                    return f"✓ Committed {len(result['files'])} file(s): {message}"
                else:
                    return f"✗ {result['error']}"

            # Push
            elif cmd_lower.startswith('push'):
                parts = command.split()
                remote = parts[1] if len(parts) > 1 else 'origin'
                branch = parts[2] if len(parts) > 2 else None

                result = self.git_manager.git_push(remote, branch)

                if result['success']:
                    return f"✓ Pushed to {result['remote']}/{result['branch']}"
                else:
                    return f"✗ {result['error']}"

            # Pull
            elif cmd_lower.startswith('pull'):
                parts = command.split()
                remote = parts[1] if len(parts) > 1 else 'origin'
                branch = parts[2] if len(parts) > 2 else None

                result = self.git_manager.git_pull(remote, branch)

                if result['success']:
                    return f"✓ Pulled from {result['remote']}/{result['branch']}\n{result['output']}"
                else:
                    return f"✗ {result['error']}"

            # Git init
            elif cmd_lower in ['git init', 'init']:
                result = self.git_manager.git_init()

                if result['success']:
                    return f"✓ Initialized git repository at {result['path']}"
                else:
                    return f"✗ {result['error']}"

            else:
                return "Unknown git command. Available: clone, status, commit, push, pull, init"

        except Exception as e:
            return f"Error: {str(e)}"

    def _handle_shell_command(self, command):
        """Handle shell operations"""
        cmd_lower = command.lower()

        try:
            # Install dependencies
            if cmd_lower.startswith('install '):
                if 'requirements.txt' in cmd_lower or 'dependencies' in cmd_lower:
                    result = self.shell_manager.install_requirements()
                else:
                    # Extract package name
                    package = command.split('install ', 1)[1].strip()
                    result = self.shell_manager.install_package(package)

                if result['success']:
                    return f"✓ Installation completed"
                else:
                    return f"✗ {result['error']}"

            # Create directory
            elif cmd_lower.startswith('mkdir '):
                directory = command.split('mkdir ', 1)[1].strip()
                result = self.shell_manager.create_directory(directory)

                if result['success']:
                    return f"✓ {result['message']}"
                else:
                    return f"✗ {result['error']}"

            # Run Python file
            elif cmd_lower.startswith('run '):
                filename = command.split('run ', 1)[1].strip()
                result = self.shell_manager.run_python_file(filename)

                if result['success']:
                    response = f"✓ Executed {filename}\n"
                    if result['stdout']:
                        response += f"\nOutput:\n{result['stdout']}"
                    return response
                else:
                    error_msg = f"✗ Execution failed\n"
                    if result.get('stderr'):
                        error_msg += f"\nError:\n{result['stderr']}"
                    return error_msg

            # Execute shell command
            elif cmd_lower.startswith('execute '):
                shell_cmd = command.split('execute ', 1)[1].strip()
                result = self.shell_manager.execute_command(shell_cmd)

                if result['success']:
                    response = f"✓ Command executed\n"
                    if result['stdout']:
                        response += f"\nOutput:\n{result['stdout']}"
                    return response
                else:
                    error_msg = f"✗ Command failed\n"
                    if result.get('stderr'):
                        error_msg += f"Error:\n{result['stderr']}"
                    elif result.get('error'):
                        error_msg += f"Error: {result['error']}"
                    return error_msg

            else:
                return "Unknown shell command. Available: install, mkdir, run, execute"

        except Exception as e:
            return f"Error: {str(e)}"

    def _show_system_info(self):
        """Show system and model information"""
        model_info = self.model_manager.get_model_info()
        system_info = self.shell_manager.get_system_info()
        profile_info = self.config.get_profile_info()

        response = "System Information:\n\n"

        # Model Profile
        response += "Active Profile:\n"
        response += f"  Name: {profile_info['name']}\n"
        response += f"  Description: {profile_info['description']}\n\n"

        # Model Info
        if model_info['loaded']:
            response += "Model:\n"
            response += f"  File: {profile_info['model_name']}\n"
            response += f"  Path: {model_info['path']}\n"
            response += f"  Context: {model_info['context_size']} tokens\n"
            response += f"  GPU layers: {model_info['gpu_layers']}\n"
            response += f"  CPU threads: {model_info['threads']}\n"
            response += f"  Batch size: {model_info['batch_size']}\n"
            response += f"  Temperature: {profile_info['temperature']}\n"
            response += f"  Max tokens: {profile_info['max_tokens']}\n\n"
        else:
            response += "Model: Not loaded\n\n"

        # Performance Settings
        response += "Performance:\n"
        response += f"  Streaming: {'Enabled' if self.config.performance.get('streaming_enabled') else 'Disabled'}\n"
        response += f"  Lightweight mode: {'Yes' if self.config.performance.get('lightweight_mode') else 'No'}\n\n"

        # System Tools
        response += "System:\n"
        if system_info.get('python_version'):
            response += f"  Python: {system_info['python_version']}\n"
        if system_info.get('pip_version'):
            response += f"  Pip: {system_info['pip_version']}\n"

        response += f"  Git: {'✓' if system_info['git_available'] else '✗'}\n"
        response += f"  NPM: {'✓' if system_info['npm_available'] else '✗'}\n"

        response += f"\nWorkspace: {self.config.workspace_dir}\n"

        return response

    def _is_complex_instruction(self, user_input: str) -> bool:
        """Detect if instruction contains multiple steps or is complex"""
        # Indicators of complex instructions
        complexity_indicators = [
            # Multiple sentences or steps
            len(user_input.split('.')) > 2,
            len(user_input.split('\n')) > 2,

            # Numbered/bulleted lists
            any(user_input.strip().startswith(str(i)) for i in range(1, 10)),
            '1.' in user_input or '2.' in user_input,

            # Multiple actions
            user_input.count(' then ') > 0,
            user_input.count(' and then ') > 0,
            user_input.count(' after ') > 0,

            # Keywords suggesting multi-step tasks
            'set up' in user_input.lower() and ('project' in user_input.lower() or 'environment' in user_input.lower()),
            'follow these' in user_input.lower(),
            'step by step' in user_input.lower(),

            # Very long instructions (likely complex)
            len(user_input) > 200 and any(word in user_input.lower() for word in ['create', 'install', 'clone', 'set up', 'configure'])
        ]

        return any(complexity_indicators)

    def _handle_complex_instruction(self, user_input: str):
        """Handle complex multi-step instructions by breaking them down automatically"""
        print("\n🤖 Complex instruction detected - Breaking down into steps...")
        print("━" * 60)

        # Parse the instruction to extract individual steps
        steps = self._extract_steps(user_input)

        # Debug: show what was extracted
        print(f"\n[DEBUG] Extracted {len(steps)} step(s) from input")
        for i, step in enumerate(steps, 1):
            print(f"[DEBUG] Step {i}: {step}")

        if not steps:
            return "I couldn't break down that instruction. Please try simpler, one-step commands."

        print(f"\n📋 Created {len(steps)} steps:\n")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step['description']}")

        print("\n━" * 60)
        print("\nℹ️  You'll be asked to confirm EACH step before it executes.")
        print("━" * 60)

        # Ask for confirmation to proceed with the plan
        try:
            proceed = input("\n🚀 Ready to start? [y/n]: ").strip().lower()
            if proceed not in ['y', 'yes']:
                return "Execution cancelled."
        except (KeyboardInterrupt, EOFError):
            return "\nExecution cancelled."

        print("\n" + "━" * 60)
        print("Starting execution...\n")

        # Track step status
        step_status = ['⏳' for _ in steps]  # pending = hourglass
        completed = 0
        failed = 0

        def show_todo_list():
            """Display the current todo list with status"""
            print("\n" + "━" * 60)
            print("📋 TODO LIST:")
            for i, step in enumerate(steps):
                status = step_status[i]
                print(f"  {status} {i+1}. {step['description']}")
            print("━" * 60)

        # Show initial todo list
        show_todo_list()

        # Track created files for cleanup
        created_files = []
        created_dirs = []

        # Execute each step
        for i, step in enumerate(steps):
            print(f"\n▶️  Step {i+1}/{len(steps)}: {step['description']}")
            print("─" * 60)

            # ASK FOR CONFIRMATION BEFORE EXECUTING
            try:
                confirm = input(f"\n   Execute this step? [y/n]: ").strip().lower()
                if confirm not in ['y', 'yes']:
                    step_status[i] = '⊘'  # skipped
                    print(f"   ⊘ Step {i+1} skipped")
                    show_todo_list()
                    continue
            except (KeyboardInterrupt, EOFError):
                # Mark remaining as skipped
                for j in range(i, len(steps)):
                    step_status[j] = '⊘'
                break

            # NOW execute the step
            try:
                result = self._execute_step(step)

                # Track what was created
                if result and result.get('success'):
                    if step.get('type') == 'mkdir' and 'path' in result:
                        created_dirs.append(result['path'])
                    elif step.get('type') == 'clone' and 'path' in result:
                        created_dirs.append(result['path'])

                if result and 'success' in result:
                    if result['success']:
                        step_status[i] = '✅'  # completed
                        completed += 1
                        print(f"\n   ✅ Step {i+1} completed!")
                    else:
                        step_status[i] = '❌'  # failed
                        failed += 1
                        print(f"\n   ❌ Step {i+1} failed: {result.get('error', 'Unknown error')}")

                        # Show updated todo list
                        show_todo_list()

                        # Ask if should continue
                        cont = input("\n   Continue with remaining steps? [y/n]: ").strip().lower()
                        if cont not in ['y', 'yes']:
                            # Mark remaining as skipped
                            for j in range(i+1, len(steps)):
                                step_status[j] = '⊘'
                            break
                else:
                    # String response from regular command
                    print(result)
                    step_status[i] = '✅'
                    completed += 1

                # Show updated todo list after each step
                show_todo_list()

            except Exception as e:
                step_status[i] = '❌'
                failed += 1
                print(f"\n   ❌ Step {i+1} error: {str(e)}")

                # Show updated todo list
                show_todo_list()

                cont = input("\n   Continue with remaining steps? [y/n]: ").strip().lower()
                if cont not in ['y', 'yes']:
                    # Mark remaining as skipped
                    for j in range(i+1, len(steps)):
                        step_status[j] = '⊘'
                    break

        # Final summary
        show_todo_list()
        print(f"\n📊 Execution Summary:")
        print(f"   ✅ Completed: {completed}/{len(steps)}")
        if failed > 0:
            print(f"   ❌ Failed: {failed}/{len(steps)}")
        skipped = len([s for s in step_status if s == '⊘'])
        if skipped > 0:
            print(f"   ⊘ Skipped: {skipped}/{len(steps)}")
        print("━" * 60)

        # Offer cleanup if any steps completed
        if completed > 0:
            self._offer_cleanup(created_dirs)

        return f"\n✓ Automatic execution finished: {completed} completed, {failed} failed"

    def _offer_cleanup(self, created_dirs):
        """Offer to clean up temporary/unnecessary files after execution"""
        print("\n" + "━" * 60)
        print("🧹 CLEANUP CHECK")
        print("━" * 60)

        # Look for common temporary files
        cleanup_candidates = []

        for directory in created_dirs:
            from pathlib import Path
            dir_path = Path(directory)
            if dir_path.exists():
                # Check for common unnecessary files
                temp_patterns = [
                    '**/__pycache__',
                    '**/*.pyc',
                    '**/*.pyo',
                    '**/.pytest_cache',
                    '**/.DS_Store',
                    '**/Thumbs.db',
                    '**/*.log',
                    '**/.git/logs',
                    '**/.coverage',
                    '**/node_modules/.cache',
                    '**/.mypy_cache',
                    '**/*.egg-info'
                ]

                for pattern in temp_patterns:
                    matches = list(dir_path.glob(pattern))
                    cleanup_candidates.extend(matches)

        if cleanup_candidates:
            print(f"\nFound {len(cleanup_candidates)} temporary/cache file(s):")
            # Show first 10
            for item in cleanup_candidates[:10]:
                print(f"  - {item}")
            if len(cleanup_candidates) > 10:
                print(f"  ... and {len(cleanup_candidates) - 10} more")

            print("\n These files are typically safe to delete and save space.")

            try:
                cleanup = input("\n🗑️  Delete these files? [y/n]: ").strip().lower()
                if cleanup in ['y', 'yes']:
                    deleted = 0
                    for item in cleanup_candidates:
                        try:
                            if item.is_file():
                                item.unlink()
                                deleted += 1
                            elif item.is_dir():
                                import shutil
                                shutil.rmtree(item)
                                deleted += 1
                        except Exception as e:
                            print(f"   Warning: Couldn't delete {item}: {e}")

                    print(f"\n   ✅ Cleaned up {deleted} item(s)")
                else:
                    print("\n   Cleanup skipped")
            except (KeyboardInterrupt, EOFError):
                print("\n   Cleanup skipped")
        else:
            print("\n✓ No temporary files found - already clean!")

        print("━" * 60)

    def _extract_steps(self, user_input: str) -> list:
        """Extract individual steps from complex instruction"""
        steps = []

        # Clean up input and handle multi-line steps
        lines = user_input.split('\n')
        cleaned_lines = []
        current_step = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a numbered step
            is_numbered = False
            for i in range(1, 20):
                for separator in ['.', ')', ' -', ':']:
                    pattern = f"{i}{separator}"
                    if line.startswith(pattern):
                        # If we had a previous step, save it
                        if current_step:
                            cleaned_lines.append(current_step)
                        # Start new step
                        current_step = line
                        is_numbered = True
                        break
                if is_numbered:
                    break

            # If not numbered and we have a current step, append to it
            if not is_numbered and current_step:
                current_step += " " + line
            elif not is_numbered and not current_step:
                # Skip non-numbered lines before first step
                continue

        # Don't forget the last step
        if current_step:
            cleaned_lines.append(current_step)

        # Now parse the cleaned steps
        for line in cleaned_lines:
            matched = False
            for i in range(1, 20):
                for separator in ['.', ')', ' -', ':']:
                    pattern = f"{i}{separator}"
                    if line.startswith(pattern):
                        description = line[len(pattern):].strip()
                        if description:
                            step = self._parse_step_description(description)
                            if step:
                                steps.append(step)
                        matched = True
                        break
                if matched:
                    break

        # If no numbered steps found, try to infer steps from keywords
        if not steps:
            steps = self._infer_steps_from_text(user_input)

        return steps

    def _parse_step_description(self, description: str) -> dict:
        """Parse a step description into a command"""
        desc_lower = description.lower()

        # Detect command type
        if 'create directory' in desc_lower or 'make directory' in desc_lower or 'mkdir' in desc_lower or ('create' in desc_lower and 'directory' in desc_lower):
            # Extract directory path or name
            import re

            # Look for "called X" or "named X" patterns
            called_match = re.search(r'(?:called|named)\s+(\w+)', description, re.IGNORECASE)
            if called_match:
                dir_name = called_match.group(1)
                # Determine if it should be in home or workspace
                path = f"~/{dir_name}"
                return {'type': 'mkdir', 'path': path, 'description': f'Create directory {path}'}

            # Look for explicit paths
            words = description.split()
            for word in words:
                if '/' in word or word.startswith('~'):
                    return {'type': 'mkdir', 'path': word, 'description': description}

            # Default to generic if no name found
            return {'type': 'mkdir', 'description': description}

        elif 'clone' in desc_lower and ('repository' in desc_lower or 'repo' in desc_lower or 'github' in desc_lower or 'http' in desc_lower):
            # Extract URL and destination
            import re

            # Look for GitHub URLs or any http(s) URLs
            url_match = re.search(r'https?://[^\s]+', description)
            if url_match:
                url = url_match.group(0)

                # Look for "into X" or "to X" patterns for destination
                dest = None
                into_match = re.search(r'(?:into|to)\s+(?:the\s+)?(?:new\s+)?(?:directory\s+)?(?:called\s+)?(\S+)', description, re.IGNORECASE)
                if into_match:
                    dest_name = into_match.group(1).rstrip('.,;')
                    # Check if it's a path or just a name
                    if '/' in dest_name or dest_name.startswith('~'):
                        dest = dest_name
                    else:
                        dest = f"~/{dest_name}"

                # Also check for explicit paths in words
                if not dest:
                    words = description.split()
                    for word in words:
                        if ('/' in word or word.startswith('~')) and word != url:
                            dest = word
                            break

                return {'type': 'clone', 'url': url, 'destination': dest, 'description': f'Clone {url} to {dest}' if dest else f'Clone {url}'}

            # No URL found
            return {'type': 'clone', 'description': description}

        elif 'install' in desc_lower and ('dependencies' in desc_lower or 'requirements' in desc_lower or 'packages' in desc_lower):
            return {'type': 'install', 'file': 'requirements.txt', 'description': description}

        elif 'check for' in desc_lower or 'look for' in desc_lower:
            return {'type': 'check', 'description': description}

        # Default: treat as shell command
        return {'type': 'general', 'description': description}

    def _infer_steps_from_text(self, text: str) -> list:
        """Infer steps from unstructured text"""
        steps = []
        text_lower = text.lower()

        # Parse the full text to extract directory, URL, etc.
        # Use _parse_step_description to intelligently parse the user's request

        # Check for directory creation
        if 'create' in text_lower and 'directory' in text_lower:
            step = self._parse_step_description(text)
            if step:
                steps.append(step)

        # Check for clone operation
        if 'clone' in text_lower:
            step = self._parse_step_description(text)
            if step and step.get('type') == 'clone':
                steps.append(step)

        # Check for install operation
        if 'install' in text_lower and ('dependencies' in text_lower or 'requirements' in text_lower):
            step = self._parse_step_description(text)
            if step:
                steps.append(step)

        return steps

    def _execute_step(self, step: dict):
        """Execute a single step based on its type"""
        step_type = step.get('type')

        if step_type == 'mkdir':
            path = step.get('path', '~/project')
            return self.shell_manager.create_directory(path)

        elif step_type == 'clone':
            url = step.get('url')
            dest = step.get('destination')
            if url:
                result = self.git_manager.clone_repository(url, dest)
                # Store the destination for later steps (like install)
                if result.get('success') and dest:
                    self._last_clone_dest = dest
                return result
            else:
                return {'success': False, 'error': 'No repository URL provided'}

        elif step_type == 'install':
            # Try to find requirements.txt in the last cloned directory
            cwd = getattr(self, '_last_clone_dest', None)
            if cwd:
                # Install in the cloned directory
                return self.shell_manager.install_requirements(cwd=cwd)
            else:
                # Fall back to workspace
                return self.shell_manager.install_requirements()

        elif step_type == 'check':
            # For check operations, just acknowledge
            return {'success': True}

        else:
            # Try to execute as general command
            return self.process_command(step['description'])

    def shutdown(self):
        """Clean shutdown with automatic junk file cleanup"""
        print("\nCleaning up workspace...")

        # Clean up junk files
        cleanup_result = self.cleanup_manager.cleanup_workspace()
        if cleanup_result.get('success') and cleanup_result.get('cleaned') > 0:
            print(f"✓ Removed {cleanup_result['cleaned']} junk file(s)")
            for file in cleanup_result['files']:
                print(f"  - {file}")

        # Save state
        self.memory.save_memory()
        self.todo_planner._save_todos()

        # Unload model
        self.model_manager.unload_model()
