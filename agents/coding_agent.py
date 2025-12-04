"""Coding agent with improved prompting and reasoning"""

class CodingAgent:
    """Agent specialized in code generation and manipulation"""

    def __init__(self, model_manager, file_tools, config):
        self.model = model_manager
        self.tools = file_tools
        self.config = config

    def create_file(self, filename, instructions):
        """Generate and create a new file"""
        # Check if file exists
        exists_result = self.tools.file_exists(filename)
        if exists_result['exists']:
            return {
                'success': False,
                'error': f"File {filename} already exists. Use edit command to modify it.",
                'content': None
            }

        # Generate code based on instructions
        code = self._generate_code(filename, instructions, existing_code=None)

        if code is None:
            return {
                'success': False,
                'error': "Failed to generate code",
                'content': None
            }

        # Write the file
        result = self.tools.write_file(filename, code)
        result['content'] = code
        return result

    def edit_file(self, filename, instructions):
        """Edit an existing file based on instructions"""
        # Read existing file
        read_result = self.tools.read_file(filename)

        if not read_result['success']:
            # File doesn't exist, create it instead
            return self.create_file(filename, instructions)

        existing_code = read_result['content']

        # Generate updated code
        updated_code = self._generate_code(filename, instructions, existing_code)

        if updated_code is None:
            return {
                'success': False,
                'error': "Failed to generate updated code",
                'content': None
            }

        # Write the updated file
        result = self.tools.write_file(filename, updated_code, overwrite=True)
        result['content'] = updated_code
        return result

    def _generate_code(self, filename, instructions, existing_code=None):
        """Generate code using the model"""
        extension = filename.split('.')[-1] if '.' in filename else 'py'
        language = self._infer_language(extension)

        if existing_code:
            prompt = self._build_edit_prompt(filename, language, existing_code, instructions)
        else:
            prompt = self._build_create_prompt(filename, language, instructions)

        try:
            # Generate with the model
            response = self.model.generate(
                prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stop=["```\n\n", "\n\nUser:", "\n\nHuman:"]
            )

            # Extract code from response
            code = self._extract_code(response)
            return code

        except Exception as e:
            print(f"Error generating code: {e}")
            return None

    def _build_create_prompt(self, filename, language, instructions):
        """Build prompt for creating new code"""
        prompt = f"""You are Codey, an expert coding assistant. Create a new {language} file.

Filename: {filename}
Task: {instructions}

Requirements:
- Write clean, well-structured {language} code
- Include necessary imports
- Add brief comments only where logic is complex
- Follow best practices for {language}
- Make the code functional and ready to run

Generate ONLY the code, no explanations. Start directly with the code:

```{language}
"""
        return prompt

    def _build_edit_prompt(self, filename, language, existing_code, instructions):
        """Build prompt for editing existing code"""
        prompt = f"""You are Codey, an expert coding assistant. Modify the existing {language} code.

Filename: {filename}
Current code:
```{language}
{existing_code}
```

Task: {instructions}

Requirements:
- Preserve existing functionality unless instructed to change it
- Maintain the same code style
- Add or modify code as needed
- Keep necessary imports
- Ensure the code remains functional

Generate the complete updated code, no explanations. Start directly with the code:

```{language}
"""
        return prompt

    def _extract_code(self, response):
        """Extract code from model response"""
        # Remove markdown code blocks if present
        import re

        # Try to find code block
        code_block = re.search(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()

        # If no code block, return cleaned response
        # Remove common prefixes
        cleaned = re.sub(r'^(Here\'s|Here is|The code|Code:|Output:)\s*', '', response, flags=re.IGNORECASE)
        return cleaned.strip()

    def _infer_language(self, extension):
        """Infer programming language from file extension"""
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'go': 'go',
            'rs': 'rust',
            'rb': 'ruby',
            'php': 'php',
            'sh': 'bash',
            'html': 'html',
            'css': 'css',
            'md': 'markdown',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml'
        }
        return language_map.get(extension.lower(), 'code')

    def explain_code(self, filename):
        """Explain what code in a file does"""
        read_result = self.tools.read_file(filename)

        if not read_result['success']:
            return {
                'success': False,
                'error': read_result['error'],
                'explanation': None
            }

        code = read_result['content']
        extension = filename.split('.')[-1] if '.' in filename else 'py'
        language = self._infer_language(extension)

        prompt = f"""You are Codey, an expert coding assistant. Explain this {language} code clearly and concisely.

Code from {filename}:
```{language}
{code}
```

Provide a clear explanation of:
1. What this code does
2. Key functions or classes
3. Important logic or algorithms

Keep it concise and practical:
"""

        try:
            explanation = self.model.generate(prompt, max_tokens=512)
            return {
                'success': True,
                'explanation': explanation
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'explanation': None
            }
