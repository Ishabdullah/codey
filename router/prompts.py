"""Prompt templates for intent classification"""

# System prompt for the intent router model
INTENT_ROUTER_SYSTEM = """Classify user requests as JSON. Output ONLY valid JSON, nothing else.

Format (JSON only, no explanation):
{"intent": "<type>", "confidence": <0-1>, "tool": "<tool|null>", "params": {}, "escalate": "<escalate|null>"}

Intent types: tool_call, simple_answer, coding_task, algorithm_task
Tools: git, shell, file
Escalate: coder, algorithm

Examples:
User: git status
{"intent": "tool_call", "confidence": 0.99, "tool": "git", "params": {"action": "status"}, "escalate": null}

User: create test.py with hello world
{"intent": "coding_task", "confidence": 0.95, "tool": null, "params": {"filename": "test.py"}, "escalate": "coder"}

User: write code that prints hello world
{"intent": "coding_task", "confidence": 0.90, "tool": null, "params": {"task": "print hello world"}, "escalate": "coder"}

User: open calculator.py file
{"intent": "tool_call", "confidence": 0.95, "tool": "file", "params": {"filename": "calculator.py", "action": "read"}, "escalate": null}

Classify (JSON only):"""


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
        r"^(read|show|display|cat|view|open)\s+.*\.(py|js|java|cpp|c|go|rs)",
        r"^(list|show)\s+files",
        r"^(delete|remove|rm)\s+.*\.(py|js|java|cpp|c|go|rs)",
        r"open\s+(the\s+)?.*\.(py|js|java|cpp|c|go|rs)",
        r"read\s+(the\s+)?.*file",
    ],

    "coding_task": [
        r"(create|write|generate|make)\s+.*\.(py|js|java|cpp|c|go|rs)",
        r"(edit|modify|update|change|fix)\s+.*\.(py|js|java|cpp|c|go|rs)",
        r"(refactor|improve|optimize)\s+",
        r"(add|implement|build|create|write|generate)\s+(a\s+)?(python|js|java|cpp|c|go|rs)?\s*(function|class|method|feature|script|app|program)",
        r"(write|create|make).*code",
        r"code\s+(that|for|to)\s+",
        r"(create|write).*calculator",
        r"prints?\s+hello\s+world",
        r"fibonacci",
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
