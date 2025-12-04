"""Advanced debugging agent with Perplexity integration"""
import re
import ast
import sys
from typing import Dict, Any, Optional, List

class DebugAgent:
    """Intelligent debugging system with local and online assistance"""

    def __init__(self, model_manager, file_tools, perplexity_api=None):
        self.model = model_manager
        self.tools = file_tools
        self.perplexity = perplexity_api

    def analyze_file(self, filename: str) -> Dict[str, Any]:
        """Analyze a Python file for potential issues"""
        read_result = self.tools.read_file(filename)

        if not read_result['success']:
            return {
                'success': False,
                'error': read_result['error'],
                'issues': []
            }

        code = read_result['content']
        issues = []

        # Basic syntax check
        syntax_check = self._check_syntax(code, filename)
        if not syntax_check['valid']:
            issues.append({
                'type': 'syntax_error',
                'severity': 'high',
                'message': syntax_check['error'],
                'line': syntax_check.get('line')
            })

        # Static analysis
        static_issues = self._static_analysis(code)
        issues.extend(static_issues)

        return {
            'success': True,
            'file': filename,
            'issues': issues,
            'issue_count': len(issues)
        }

    def _check_syntax(self, code: str, filename: str) -> Dict[str, Any]:
        """Check Python syntax"""
        try:
            ast.parse(code)
            return {'valid': True}
        except SyntaxError as e:
            return {
                'valid': False,
                'error': str(e),
                'line': e.lineno,
                'offset': e.offset
            }

    def _static_analysis(self, code: str) -> List[Dict[str, Any]]:
        """Perform static analysis for common issues"""
        issues = []

        # Check for common issues
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            # Unused imports (basic check)
            if 'import' in line and line.strip().startswith('import'):
                # This is a simplified check
                pass

            # TODO/FIXME comments
            if 'TODO' in line or 'FIXME' in line:
                issues.append({
                    'type': 'todo',
                    'severity': 'low',
                    'message': f"TODO/FIXME comment: {line.strip()}",
                    'line': i
                })

            # Bare except
            if re.search(r'except\s*:', line):
                issues.append({
                    'type': 'bare_except',
                    'severity': 'medium',
                    'message': "Bare except clause - should specify exception type",
                    'line': i
                })

            # Print statements (potential debug code)
            if re.search(r'\bprint\s*\(', line) and 'def ' not in line:
                issues.append({
                    'type': 'debug_print',
                    'severity': 'low',
                    'message': "Debug print statement found",
                    'line': i
                })

        return issues

    def debug_error(self, filename: str, error_message: Optional[str] = None) -> Dict[str, Any]:
        """Debug an error in a file"""
        # Read the file
        read_result = self.tools.read_file(filename)

        if not read_result['success']:
            return {
                'success': False,
                'error': read_result['error']
            }

        code = read_result['content']

        # Try local debugging first
        analysis = self.analyze_file(filename)

        # If we have Perplexity and an error message, get deeper insights
        perplexity_help = None
        if self.perplexity and error_message:
            perplexity_help = self.perplexity.debug_with_perplexity(
                code,
                error_message,
                language='python'
            )

        return {
            'success': True,
            'file': filename,
            'local_analysis': analysis,
            'perplexity_help': perplexity_help,
            'has_fixes': perplexity_help and perplexity_help.get('has_fix', False)
        }

    def auto_fix(self, filename: str, error_message: Optional[str] = None) -> Dict[str, Any]:
        """Attempt to automatically fix issues"""
        # Get debugging information
        debug_result = self.debug_error(filename, error_message)

        if not debug_result['success']:
            return debug_result

        # Read current code
        read_result = self.tools.read_file(filename)
        current_code = read_result['content']

        # Build fix prompt
        prompt = self._build_fix_prompt(
            filename,
            current_code,
            debug_result.get('local_analysis'),
            debug_result.get('perplexity_help'),
            error_message
        )

        try:
            # Generate fixed code
            fixed_code = self.model.generate(prompt, max_tokens=2048, temperature=0.2)

            # Extract code
            fixed_code = self._extract_code(fixed_code)

            # Write fixed code
            write_result = self.tools.write_file(filename, fixed_code, overwrite=True)

            if write_result['success']:
                return {
                    'success': True,
                    'file': filename,
                    'fixed': True,
                    'backup': write_result.get('backup'),
                    'changes_made': True
                }
            else:
                return {
                    'success': False,
                    'error': write_result['error']
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _build_fix_prompt(self, filename, code, local_analysis, perplexity_help, error_message):
        """Build prompt for fixing code"""
        prompt = f"""You are a debugging expert. Fix the issues in this Python code.

File: {filename}

Current code:
```python
{code}
```

"""
        if error_message:
            prompt += f"Error message:\n{error_message}\n\n"

        if local_analysis and local_analysis.get('issues'):
            issues_text = "\n".join([
                f"- Line {issue.get('line', '?')}: {issue['message']}"
                for issue in local_analysis['issues']
            ])
            prompt += f"Identified issues:\n{issues_text}\n\n"

        if perplexity_help and perplexity_help.get('analysis'):
            prompt += f"Expert analysis:\n{perplexity_help['analysis']}\n\n"

        prompt += """Generate the complete fixed code. Requirements:
- Fix all identified issues
- Maintain functionality
- Add proper error handling
- Keep the same structure
- Include necessary imports

Provide ONLY the fixed code:

```python
"""
        return prompt

    def _extract_code(self, response: str) -> str:
        """Extract code from response"""
        # Remove markdown code blocks
        code_block = re.search(r'```(?:python)?\n(.*?)```', response, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()

        # Clean response
        cleaned = re.sub(r'^(Here\'s|Here is|Fixed code:|Code:)\s*', '', response, flags=re.IGNORECASE)
        return cleaned.strip()

    def suggest_improvements(self, filename: str) -> Dict[str, Any]:
        """Suggest code improvements"""
        read_result = self.tools.read_file(filename)

        if not read_result['success']:
            return {
                'success': False,
                'error': read_result['error']
            }

        code = read_result['content']

        # Get suggestions from Perplexity if available
        suggestions = []

        if self.perplexity:
            best_practices = self.perplexity.get_best_practices(
                f"reviewing and improving this code:\n{code[:500]}",  # First 500 chars
                language="python"
            )
            if best_practices:
                suggestions.append({
                    'source': 'perplexity',
                    'suggestion': best_practices
                })

        # Local analysis
        analysis = self.analyze_file(filename)
        if analysis['success'] and analysis['issues']:
            suggestions.append({
                'source': 'local',
                'issues': analysis['issues']
            })

        return {
            'success': True,
            'file': filename,
            'suggestions': suggestions
        }
