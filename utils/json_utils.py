"""JSON Utilities - Robust JSON extraction from noisy LLM outputs

Handles common issues with LLM-generated JSON:
- Stray tokens before/after JSON (e.g., "JSON", "Here is the response:", etc.)
- Nested objects with proper bracket matching
- YAML-style outputs that need conversion
- Validation of required keys
"""
import json
import re
import logging
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


def extract_json(text: str, required_keys: Optional[List[str]] = None) -> Tuple[Optional[Dict], str]:
    """Extract valid JSON from potentially noisy text

    This function implements a defensive extraction strategy:
    1. Try parsing the entire text as JSON
    2. Find and extract the first valid {...} block with bracket matching
    3. Try to parse YAML-style output as fallback
    4. Return None if all methods fail

    Args:
        text: Raw text that may contain JSON
        required_keys: List of keys that must be present in extracted JSON

    Returns:
        Tuple of (parsed dict or None, extraction method used)
    """
    if not text or not text.strip():
        return None, "empty_input"

    text = text.strip()

    # Method 1: Try parsing entire text as JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if _validate_keys(data, required_keys):
                return data, "direct_parse"
    except json.JSONDecodeError:
        pass

    # Method 2: Extract first valid {...} block with bracket matching
    json_block = _extract_json_block(text)
    if json_block:
        try:
            data = json.loads(json_block)
            if isinstance(data, dict):
                if _validate_keys(data, required_keys):
                    return data, "block_extraction"
        except json.JSONDecodeError:
            pass

    # Method 3: Try to parse YAML-style output
    yaml_result = _parse_yaml_style(text, required_keys)
    if yaml_result:
        return yaml_result, "yaml_conversion"

    # Method 4: Try to extract key-value pairs from text
    kv_result = _extract_key_values(text, required_keys)
    if kv_result:
        return kv_result, "kv_extraction"

    return None, "parse_failed"


def _extract_json_block(text: str) -> Optional[str]:
    """Extract first valid JSON block using bracket matching

    Args:
        text: Text potentially containing JSON

    Returns:
        Extracted JSON string or None
    """
    # Find first opening brace
    start_idx = text.find('{')
    if start_idx == -1:
        return None

    # Use bracket matching to find corresponding closing brace
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start_idx, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start_idx:i+1]

    return None


def _parse_yaml_style(text: str, required_keys: Optional[List[str]] = None) -> Optional[Dict]:
    """Try to parse YAML-style output (key: value format)

    Handles outputs like:
    - intent: tool_call
    - confidence: 0.95
    - tool: git

    Args:
        text: Text in YAML-like format
        required_keys: Keys that must be present

    Returns:
        Parsed dict or None
    """
    result = {}

    # Pattern for YAML-style key-value pairs
    # Matches: "- key: value" or "key: value"
    pattern = r'[-*]?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+?)(?=\n[-*]?\s*[a-zA-Z_]|\n\n|\Z)'

    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)

    for key, value in matches:
        key = key.strip().lower()
        value = value.strip()

        # Try to parse value as JSON (for nested objects)
        try:
            parsed_value = json.loads(value)
            result[key] = parsed_value
        except json.JSONDecodeError:
            # Handle common value types
            if value.lower() in ('null', 'none', '~'):
                result[key] = None
            elif value.lower() == 'true':
                result[key] = True
            elif value.lower() == 'false':
                result[key] = False
            elif re.match(r'^-?\d+\.?\d*$', value):
                result[key] = float(value) if '.' in value else int(value)
            else:
                # Strip quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                result[key] = value

    if result and _validate_keys(result, required_keys):
        return result

    return None


def _extract_key_values(text: str, required_keys: Optional[List[str]] = None) -> Optional[Dict]:
    """Last resort: extract key-value patterns from text

    Args:
        text: Text containing key-value patterns
        required_keys: Keys that must be present

    Returns:
        Extracted dict or None
    """
    result = {}

    # Try to find common intent-related values in text
    intent_patterns = {
        'tool_call': r'\b(tool_call|tool call)\b',
        'coding_task': r'\b(coding_task|coding task|code generation)\b',
        'algorithm_task': r'\b(algorithm_task|algorithm task)\b',
        'simple_answer': r'\b(simple_answer|simple answer|simple question)\b',
    }

    text_lower = text.lower()
    for intent, pattern in intent_patterns.items():
        if re.search(pattern, text_lower):
            result['intent'] = intent
            break

    # Try to extract confidence
    conf_match = re.search(r'confidence[:\s]+(\d*\.?\d+)', text_lower)
    if conf_match:
        try:
            result['confidence'] = float(conf_match.group(1))
        except ValueError:
            pass

    # Try to extract tool type
    tool_patterns = {
        'git': r'\btool[:\s]+(git)\b',
        'shell': r'\btool[:\s]+(shell)\b',
        'file': r'\btool[:\s]+(file)\b',
    }

    for tool, pattern in tool_patterns.items():
        if re.search(pattern, text_lower):
            result['tool'] = tool
            break

    # Only return if we found at least one meaningful key (not just confidence)
    meaningful_keys = {'intent', 'tool', 'escalate', 'action', 'command'}
    has_meaningful_data = any(key in result for key in meaningful_keys)

    if has_meaningful_data:
        # Set default confidence if not found
        if 'confidence' not in result:
            result['confidence'] = 0.5

        if _validate_keys(result, required_keys):
            return result

    return None


def _validate_keys(data: Dict, required_keys: Optional[List[str]]) -> bool:
    """Validate that required keys are present

    Args:
        data: Dict to validate
        required_keys: Keys that must be present (None means no validation)

    Returns:
        True if valid
    """
    if not required_keys:
        return True

    return all(key in data for key in required_keys)


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Safely parse JSON with fallback to default

    Args:
        text: JSON string
        default: Value to return on parse failure

    Returns:
        Parsed JSON or default
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default
