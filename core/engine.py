"""Main Codey engine - orchestrates all components"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import config
from models.manager import ModelManager
from core.tools import FileTools
from core.parser import CommandParser
from agents.coding_agent import CodingAgent
from memory.store import MemoryStore

class CodeyEngine:
    """Main engine that coordinates all Codey components"""

    def __init__(self):
        self.config = config
        self.model_manager = ModelManager(self.config)
        self.file_tools = FileTools(self.config)
        self.parser = CommandParser()
        self.memory = MemoryStore(self.config)
        self.coding_agent = CodingAgent(self.model_manager, self.file_tools, self.config)

        self.memory.start_session()

    def process_command(self, user_input):
        """Process a natural language command"""
        if not user_input or not user_input.strip():
            return "Please enter a command."

        # Parse the command
        parsed = self.parser.parse(user_input)
        action = parsed['action']
        filename = parsed['filename']
        instructions = parsed['instructions']

        # Execute based on action
        result = None
        response = None

        try:
            if action == 'create':
                if not filename:
                    filename = self.parser.extract_filename(user_input)
                    if not filename:
                        return "I couldn't determine the filename. Please specify a filename, e.g., 'create hello.py that prints hello world'"

                result = self.coding_agent.create_file(filename, instructions)

                if result['success']:
                    self.memory.add_file_action(filename, 'created', {'instructions': instructions})
                    response = f"Created {filename}"
                    if self.config.require_confirmation:
                        response += f"\n\n{self._show_preview(result['content'])}"
                else:
                    response = f"Error: {result['error']}"

            elif action == 'edit':
                if not filename:
                    return "Please specify which file to edit."

                result = self.coding_agent.edit_file(filename, instructions)

                if result['success']:
                    self.memory.add_file_action(filename, 'edited', {'instructions': instructions})
                    response = f"Updated {filename}"
                    if result.get('backup'):
                        response += f"\n(Backup saved to {result['backup']})"
                    if self.config.require_confirmation:
                        response += f"\n\n{self._show_preview(result['content'])}"
                else:
                    response = f"Error: {result['error']}"

            elif action == 'read':
                if not filename:
                    return "Please specify which file to read."

                result = self.file_tools.read_file(filename)

                if result['success']:
                    response = f"Contents of {filename}:\n\n{result['content']}"
                else:
                    response = f"Error: {result['error']}"

            elif action == 'delete':
                if not filename:
                    return "Please specify which file to delete."

                # Confirmation for delete
                if self.config.require_confirmation:
                    confirm = input(f"Are you sure you want to delete {filename}? (yes/no): ")
                    if confirm.lower() not in ['yes', 'y']:
                        return "Delete cancelled."

                result = self.file_tools.delete_file(filename)

                if result['success']:
                    self.memory.add_file_action(filename, 'deleted')
                    response = f"Deleted {filename}"
                    if result.get('backup'):
                        response += f"\n(Backup saved to {result['backup']})"
                else:
                    response = f"Error: {result['error']}"

            elif action == 'list':
                result = self.file_tools.list_files()

                if result['success']:
                    if result['files']:
                        response = "Files in workspace:\n" + "\n".join(f"  - {f}" for f in result['files'])
                    else:
                        response = "No files in workspace."
                else:
                    response = f"Error: {result['error']}"

            elif action == 'general':
                # Try to infer what the user wants
                intent = self.parser.infer_intent(user_input)

                if intent == 'code_explanation':
                    # Look for filename in input
                    filename = self.parser.extract_filename(user_input)
                    if filename:
                        result = self.coding_agent.explain_code(filename)
                        if result['success']:
                            response = result['explanation']
                        else:
                            response = f"Error: {result['error']}"
                    else:
                        response = "Which file would you like me to explain?"
                else:
                    response = self._handle_general_query(user_input)

            else:
                response = f"I'm not sure how to handle that command. Try: create, edit, read, delete, or list files."

        except Exception as e:
            response = f"An error occurred: {str(e)}"

        # Store in memory
        self.memory.add_conversation(user_input, response, action)

        return response

    def _handle_general_query(self, query):
        """Handle general queries or conversations"""
        # For general questions, use the model directly
        prompt = f"""You are Codey, a helpful coding assistant running locally. Answer this question concisely:

User: {query}

Codey:"""

        try:
            response = self.model_manager.generate(prompt, max_tokens=512)
            return response
        except Exception as e:
            return f"I encountered an error: {str(e)}"

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
        self.model_manager.unload_model()
