"""README Generator - Automatic documentation after multi-step tasks

This module generates README.md files based on:
1. Generated files from multi-step task execution
2. Task description and context
3. File contents and structure

Part of Phase 6: CPU Optimization
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime


class ReadmeGenerator:
    """Generates README documentation for generated projects

    This class creates README.md files without model inference,
    using templates and file analysis to produce documentation.
    """

    def __init__(self, workspace_dir: Optional[Path] = None):
        """Initialize generator

        Args:
            workspace_dir: Workspace directory for file operations
        """
        self.workspace_dir = workspace_dir or Path.cwd()

    def generate(
        self,
        task_description: str,
        generated_files: List[str],
        project_name: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate README content based on task and files

        Args:
            task_description: Original task description
            generated_files: List of generated filenames
            project_name: Optional project name
            extra_context: Additional context information

        Returns:
            README.md content as string
        """
        # Infer project name from task or files
        if not project_name:
            project_name = self._infer_project_name(task_description, generated_files)

        # Analyze file structure
        structure = self._analyze_structure(generated_files)

        # Detect project type
        project_type = self._detect_project_type(generated_files, extra_context)

        # Build README sections
        sections = []

        # Title and description
        sections.append(f"# {project_name}\n")
        sections.append(self._generate_description(task_description, project_type))

        # Features section (if applicable)
        features = self._extract_features(task_description, extra_context)
        if features:
            sections.append("\n## Features\n")
            for feature in features:
                sections.append(f"- {feature}\n")

        # Project structure
        sections.append("\n## Project Structure\n")
        sections.append("```\n")
        sections.append(self._format_structure(structure))
        sections.append("```\n")

        # Requirements
        if 'requirements.txt' in generated_files or project_type in ['flask', 'fastapi', 'python']:
            sections.append("\n## Requirements\n")
            sections.append("- Python 3.8+\n")
            if project_type == 'flask':
                sections.append("- Flask\n")
            elif project_type == 'fastapi':
                sections.append("- FastAPI\n- Uvicorn\n")
            if extra_context and extra_context.get('has_database'):
                sections.append("- SQLite3\n")

        # Installation
        sections.append("\n## Installation\n")
        sections.append(self._generate_installation(project_type, generated_files))

        # Usage
        sections.append("\n## Usage\n")
        sections.append(self._generate_usage(project_type, generated_files))

        # API endpoints (if applicable)
        if project_type in ['flask', 'fastapi']:
            sections.append("\n## API Endpoints\n")
            sections.append(self._generate_api_docs(generated_files, extra_context))

        # File descriptions
        sections.append("\n## Files\n")
        sections.append(self._generate_file_descriptions(generated_files, project_type))

        # Footer
        sections.append("\n---\n")
        sections.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d')} by Codey Engine V3*\n")

        return "".join(sections)

    def _infer_project_name(self, task_description: str, files: List[str]) -> str:
        """Infer project name from task or files"""
        import re

        # Check for explicit project name in task
        patterns = [
            r'create (?:a )?([a-zA-Z0-9_-]+) (?:app|application|project)',
            r'build (?:a )?([a-zA-Z0-9_-]+)',
            r'([a-zA-Z0-9_-]+) (?:web )?app',
        ]

        for pattern in patterns:
            match = re.search(pattern, task_description, re.IGNORECASE)
            if match:
                name = match.group(1).replace('_', ' ').title().replace(' ', '')
                return name

        # Infer from main file
        main_files = ['app.py', 'main.py', 'server.py', 'index.py']
        for main in main_files:
            if main in files:
                return main.replace('.py', '').title() + "App"

        return "GeneratedProject"

    def _analyze_structure(self, files: List[str]) -> Dict[str, Any]:
        """Analyze file structure"""
        structure = {
            'root': [],
            'directories': {}
        }

        for filepath in files:
            path = Path(filepath)
            parts = path.parts

            if len(parts) == 1:
                structure['root'].append(parts[0])
            else:
                dir_name = parts[0]
                if dir_name not in structure['directories']:
                    structure['directories'][dir_name] = []
                structure['directories'][dir_name].append('/'.join(parts[1:]))

        return structure

    def _detect_project_type(self, files: List[str], context: Optional[Dict]) -> str:
        """Detect project type from files"""
        files_lower = [f.lower() for f in files]

        # Check context first
        if context:
            if context.get('is_fullstack'):
                if any('fastapi' in str(context).lower() for _ in [1]):
                    return 'fastapi'
                return 'flask'

        # Check for framework indicators in files
        if 'app.py' in files_lower:
            return 'flask'  # Default assumption for app.py
        elif 'main.py' in files_lower:
            return 'fastapi'  # FastAPI convention
        elif 'index.html' in files_lower and not any('.py' in f for f in files):
            return 'static'
        elif any('.py' in f for f in files):
            return 'python'
        elif any('.js' in f for f in files):
            return 'javascript'

        return 'unknown'

    def _generate_description(self, task_description: str, project_type: str) -> str:
        """Generate project description"""
        # Clean up task description
        desc = task_description.strip()

        # Limit length
        if len(desc) > 200:
            desc = desc[:200] + "..."

        type_descriptions = {
            'flask': "A Flask web application",
            'fastapi': "A FastAPI web application",
            'python': "A Python project",
            'static': "A static web project",
            'javascript': "A JavaScript project",
        }

        type_desc = type_descriptions.get(project_type, "A generated project")

        return f"\n{type_desc} created from the following specification:\n\n> {desc}\n"

    def _extract_features(self, task: str, context: Optional[Dict]) -> List[str]:
        """Extract features from task description"""
        features = []
        task_lower = task.lower()

        # Common feature keywords
        feature_patterns = {
            'crud': 'CRUD operations (Create, Read, Update, Delete)',
            'database': 'SQLite database integration',
            'api': 'RESTful API endpoints',
            'auth': 'User authentication',
            'login': 'Login/logout functionality',
            'form': 'Form handling and validation',
            'responsive': 'Responsive design',
            'realtime': 'Real-time updates',
        }

        for keyword, description in feature_patterns.items():
            if keyword in task_lower:
                features.append(description)

        # Add context-based features
        if context:
            if context.get('has_database'):
                if 'database' not in task_lower:
                    features.append('Database integration')
            if context.get('is_fullstack'):
                features.append('Full-stack architecture (frontend + backend)')

        return features

    def _format_structure(self, structure: Dict) -> str:
        """Format file structure as tree"""
        lines = []

        # Root files
        for f in sorted(structure['root']):
            lines.append(f"├── {f}")

        # Directories
        dirs = sorted(structure['directories'].keys())
        for i, dir_name in enumerate(dirs):
            is_last_dir = (i == len(dirs) - 1)
            prefix = "└──" if is_last_dir else "├──"
            lines.append(f"{prefix} {dir_name}/")

            files = sorted(structure['directories'][dir_name])
            for j, f in enumerate(files):
                is_last_file = (j == len(files) - 1)
                sub_prefix = "    └──" if is_last_file else "    ├──"
                if is_last_dir:
                    sub_prefix = "    " + ("└──" if is_last_file else "├──")
                lines.append(f"{sub_prefix} {f}")

        return "\n".join(lines)

    def _generate_installation(self, project_type: str, files: List[str]) -> str:
        """Generate installation instructions"""
        instructions = []

        instructions.append("1. Clone or download this project\n")

        if project_type in ['flask', 'fastapi', 'python']:
            instructions.append("2. Create a virtual environment (recommended):\n")
            instructions.append("   ```bash\n")
            instructions.append("   python -m venv venv\n")
            instructions.append("   source venv/bin/activate  # Linux/Mac\n")
            instructions.append("   # or: venv\\Scripts\\activate  # Windows\n")
            instructions.append("   ```\n\n")

            if 'requirements.txt' in files:
                instructions.append("3. Install dependencies:\n")
                instructions.append("   ```bash\n")
                instructions.append("   pip install -r requirements.txt\n")
                instructions.append("   ```\n")

        if 'init_db.py' in files:
            instructions.append("\n4. Initialize the database:\n")
            instructions.append("   ```bash\n")
            instructions.append("   python init_db.py\n")
            instructions.append("   ```\n")

        return "".join(instructions)

    def _generate_usage(self, project_type: str, files: List[str]) -> str:
        """Generate usage instructions"""
        usage = []

        if project_type == 'flask':
            usage.append("Start the Flask development server:\n\n")
            usage.append("```bash\n")
            usage.append("python app.py\n")
            usage.append("```\n\n")
            usage.append("Then open `http://localhost:5000` in your browser.\n")

        elif project_type == 'fastapi':
            usage.append("Start the FastAPI server:\n\n")
            usage.append("```bash\n")
            usage.append("uvicorn main:app --reload\n")
            usage.append("```\n\n")
            usage.append("Then open `http://localhost:8000` in your browser.\n")
            usage.append("API documentation available at `http://localhost:8000/docs`.\n")

        elif project_type == 'static':
            usage.append("Open `index.html` in your web browser.\n")

        elif project_type == 'python':
            main_file = 'main.py' if 'main.py' in files else (files[0] if files else 'main.py')
            usage.append(f"Run the main script:\n\n")
            usage.append("```bash\n")
            usage.append(f"python {main_file}\n")
            usage.append("```\n")

        return "".join(usage)

    def _generate_api_docs(self, files: List[str], context: Optional[Dict]) -> str:
        """Generate basic API documentation"""
        docs = []

        docs.append("| Method | Endpoint | Description |\n")
        docs.append("|--------|----------|-------------|\n")

        # Common CRUD endpoints
        if context and context.get('has_database'):
            resource = 'items'  # Default resource name
            docs.append(f"| GET | /{resource} | List all {resource} |\n")
            docs.append(f"| POST | /{resource} | Create new item |\n")
            docs.append(f"| GET | /{resource}/{{id}} | Get item by ID |\n")
            docs.append(f"| PUT | /{resource}/{{id}} | Update item |\n")
            docs.append(f"| DELETE | /{resource}/{{id}} | Delete item |\n")
        else:
            docs.append("| GET | / | Home page |\n")
            docs.append("| POST | /api/action | Perform action |\n")

        return "".join(docs)

    def _generate_file_descriptions(self, files: List[str], project_type: str) -> str:
        """Generate descriptions for each file"""
        descriptions = {
            'app.py': 'Main Flask application with routes and configuration',
            'main.py': 'Main application entry point',
            'models.py': 'Database models and schema definitions',
            'init_db.py': 'Database initialization script',
            'requirements.txt': 'Python package dependencies',
            'templates/index.html': 'Main HTML template',
            'static/css/style.css': 'Stylesheet for the application',
            'static/js/app.js': 'Client-side JavaScript logic',
            'index.html': 'Main HTML page',
            'style.css': 'Stylesheet',
            'script.js': 'JavaScript code',
        }

        lines = []
        for f in sorted(files):
            desc = descriptions.get(f, f"Generated {Path(f).suffix} file")
            lines.append(f"- **{f}**: {desc}\n")

        return "".join(lines)

    def generate_from_plan(self, plan, file_contents: Dict[str, str] = None) -> str:
        """Generate README from a completed TaskPlan

        Args:
            plan: Completed TaskPlan object
            file_contents: Optional dict mapping filename to content

        Returns:
            README.md content
        """
        # Extract information from plan
        generated_files = []
        for step in plan.steps:
            if step.params and step.params.get('file'):
                generated_files.append(step.params['file'])

        return self.generate(
            task_description=plan.original_request,
            generated_files=generated_files,
            extra_context=plan.metadata
        )


def generate_readme(
    task: str,
    files: List[str],
    context: Optional[Dict] = None,
    workspace: Optional[Path] = None
) -> str:
    """Convenience function to generate README

    Args:
        task: Task description
        files: List of generated files
        context: Optional context dict
        workspace: Optional workspace directory

    Returns:
        README.md content
    """
    generator = ReadmeGenerator(workspace)
    return generator.generate(task, files, extra_context=context)
