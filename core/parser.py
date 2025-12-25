"""Natural language command parser for Codey

DEPRECATED: This module is deprecated in favor of router/intent_router.py
which provides model-based intent classification with better accuracy.

For new code, use:
    from router.intent_router import IntentRouter
    router = IntentRouter(model_path, config)
    result = router.classify(user_input)
"""
import re
import warnings


class CommandParser:
    """Parse natural language commands into structured actions

    DEPRECATED: Use router.IntentRouter instead for better accuracy.
    This class remains for backward compatibility only.
    """

    def __init__(self):
        warnings.warn(
            "CommandParser is deprecated. Use router.IntentRouter for "
            "model-based intent classification with better accuracy.",
            DeprecationWarning,
            stacklevel=2
        )

        self.action_patterns = {
            'create': [
                r'create\s+(?:a\s+)?(?:new\s+)?(?:file\s+)?(?:called\s+)?([^\s]+)',
                r'make\s+(?:a\s+)?(?:new\s+)?(?:file\s+)?([^\s]+)',
                r'write\s+(?:a\s+)?(?:new\s+)?(?:file\s+)?([^\s]+)'
            ],
            'edit': [
                r'edit\s+([^\s]+)',
                r'modify\s+([^\s]+)',
                r'update\s+([^\s]+)',
                r'change\s+([^\s]+)',
                r'fix\s+([^\s]+)'
            ],
            'read': [
                r'read\s+([^\s]+)',
                r'show\s+(?:me\s+)?([^\s]+)',
                r'display\s+([^\s]+)',
                r'cat\s+([^\s]+)',
                r'view\s+([^\s]+)'
            ],
            'delete': [
                r'delete\s+([^\s]+)',
                r'remove\s+([^\s]+)',
                r'rm\s+([^\s]+)'
            ],
            'list': [
                r'list\s+files',
                r'show\s+files',
                r'ls',
                r'what\s+files'
            ]
        }

    def parse(self, user_input):
        """Parse user input into a structured command"""
        user_input = user_input.strip().lower()

        # Check for each action type
        for action, patterns in self.action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, user_input)
                if match:
                    result = {
                        'action': action,
                        'raw_input': user_input,
                        'filename': None,
                        'instructions': user_input
                    }

                    # Extract filename if captured
                    if match.groups():
                        result['filename'] = match.group(1)

                    # Extract instructions (text after action)
                    if action in ['create', 'edit']:
                        # Get everything after the filename
                        parts = user_input.split(result['filename'], 1)
                        if len(parts) > 1:
                            instructions = parts[1].strip()
                            # Clean up common connecting words
                            instructions = re.sub(r'^(that|to|which|should|will|:)\s+', '', instructions)
                            result['instructions'] = instructions if instructions else user_input

                    return result

        # If no specific pattern matched, assume it's a general instruction
        return {
            'action': 'general',
            'raw_input': user_input,
            'filename': None,
            'instructions': user_input
        }

    def extract_filename(self, text, default_extension='.py'):
        """Extract or generate a filename from text"""
        # Look for common file extensions
        match = re.search(r'([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)', text)
        if match:
            return match.group(1)

        # Look for file names without extension
        match = re.search(r'([a-zA-Z0-9_-]+)(?:\s|$)', text)
        if match:
            name = match.group(1)
            # Don't add extension if it's a common word
            common_words = ['file', 'script', 'code', 'program', 'function', 'class']
            if name.lower() not in common_words:
                if '.' not in name:
                    return f"{name}{default_extension}"
                return name

        return None

    def infer_intent(self, user_input):
        """Infer the user's intent from their input"""
        user_input_lower = user_input.lower()

        intents = {
            'code_generation': ['write', 'create', 'generate', 'make', 'implement'],
            'code_explanation': ['explain', 'what does', 'how does', 'understand'],
            'debugging': ['fix', 'debug', 'error', 'bug', 'problem', 'issue'],
            'refactoring': ['refactor', 'improve', 'optimize', 'clean', 'reorganize'],
            'testing': ['test', 'unittest', 'pytest', 'check if'],
            'file_management': ['list', 'show files', 'delete', 'remove']
        }

        for intent, keywords in intents.items():
            if any(keyword in user_input_lower for keyword in keywords):
                return intent

        return 'general'
