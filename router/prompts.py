"""Prompt templates for intent classification"""

# System prompt for the intent router model
INTENT_ROUTER_SYSTEM = """You are an intent classifier for a coding assistant. Analyze the user's request and respond with JSON only.

Your job is to classify the intent and extract parameters. Output valid JSON in this exact format:

{
  "intent": "<one of: tool_call, simple_answer, coding_task, algorithm_task>",
  "confidence": <0.0 to 1.0>,
  "tool": "<git|shell|file|null>",
  "params": {<extracted parameters>},
  "escalate": "<coder|algorithm|null>"
}

Intent Types:
- tool_call: Direct command (git, shell, file operations)
- simple_answer: Quick question answerable without code
- coding_task: Write/edit code, implement features
- algorithm_task: Complex algorithms, data structures, performance

Tool Types (for tool_call intent):
- git: Git operations (status, commit, push, pull, clone)
- shell: Shell commands (mkdir, run, install, execute)
- file: File operations (read, write, delete, list)

Escalation:
- coder: For coding_task intent
- algorithm: For algorithm_task intent
- null: Handle directly (tool_call, simple_answer)

Examples:

User: "git status"
{"intent": "tool_call", "confidence": 0.99, "tool": "git", "params": {"action": "status"}, "escalate": null}

User: "create a file test.py with hello world"
{"intent": "coding_task", "confidence": 0.95, "tool": null, "params": {"filename": "test.py", "task": "hello world"}, "escalate": "coder"}

User: "implement quicksort algorithm"
{"intent": "algorithm_task", "confidence": 0.98, "tool": null, "params": {"algorithm": "quicksort"}, "escalate": "algorithm"}

User: "what is python?"
{"intent": "simple_answer", "confidence": 0.92, "tool": null, "params": {}, "escalate": null}

Now classify this request:"""


INTENT_CLASSIFICATION_TEMPLATE = """{system_prompt}

User: {user_input}

Classification:"""


PARAMETER_EXTRACTION_TEMPLATE = """Extract parameters from this request as JSON.

User: {user_input}
Intent: {intent}

Extract relevant details (filenames, commands, descriptions, etc.) as JSON:"""


# Fallback regex patterns when model classification is uncertain
REGEX_PATTERNS = {
    "tool_call_git": [
        r"^git\s+(status|diff|log|add|commit|push|pull|clone|init)",
        r"^(status|commit|push|pull|clone|init)(\s|$)",
    ],

    "tool_call_shell": [
        r"^(mkdir|run|execute|install|pip|python|node|npm)\s+",
        r"^(ls|pwd|cd|cat|echo|tree)\s+",
    ],

    "tool_call_file": [
        r"^(read|show|display|cat|view)\s+.*\.(py|js|java|cpp|c|go|rs)",
        r"^(list|show)\s+files",
        r"^(delete|remove|rm)\s+.*\.(py|js|java|cpp|c|go|rs)",
    ],

    "coding_task": [
        r"(create|write|generate|make)\s+.*\.(py|js|java|cpp|c|go|rs)",
        r"(edit|modify|update|change|fix)\s+.*\.(py|js|java|cpp|c|go|rs)",
        r"(refactor|improve|optimize)\s+",
        r"(add|implement|build)\s+(function|class|method|feature)",
    ],

    "algorithm_task": [
        r"(binary search|quicksort|mergesort|heapsort|bubble sort)",
        r"(graph|tree|heap|stack|queue|linked list|hash table)",
        r"(dynamic programming|greedy|divide and conquer)",
        r"(algorithm|data structure|complexity|O\(n\))",
        r"(parse|lex|compile|optimize performance)",
    ],

    "simple_answer": [
        r"^(what is|what are|what's|how do|how does|why|explain)\s+",
        r"^(can you|could you)\s+(tell|explain|describe)",
        r"^(help|guide|show me how)",
    ],
}


def get_intent_prompt(user_input: str, context: str = None) -> str:
    """Generate intent classification prompt

    Args:
        user_input: The user's request
        context: Optional context from previous interactions

    Returns:
        Formatted prompt for the router model
    """
    # For now, ignore context (can be added in future iterations)
    return INTENT_CLASSIFICATION_TEMPLATE.format(
        system_prompt=INTENT_ROUTER_SYSTEM,
        user_input=user_input
    )


def get_parameter_extraction_prompt(user_input: str, intent: str) -> str:
    """Generate parameter extraction prompt

    Args:
        user_input: The user's request
        intent: Classified intent type

    Returns:
        Formatted prompt for parameter extraction
    """
    return PARAMETER_EXTRACTION_TEMPLATE.format(
        user_input=user_input,
        intent=intent
    )
