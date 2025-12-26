"""Unit tests for JSON utilities - robust extraction from noisy LLM outputs"""
import unittest
from utils.json_utils import (
    extract_json,
    _extract_json_block,
    _parse_yaml_style,
    _extract_key_values,
    safe_json_loads
)


class TestExtractJson(unittest.TestCase):
    """Tests for the main extract_json function"""

    def test_clean_json(self):
        """Test extraction from clean JSON"""
        text = '{"intent": "coding_task", "confidence": 0.95}'
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'coding_task')
        self.assertEqual(data['confidence'], 0.95)
        self.assertEqual(method, 'direct_parse')

    def test_json_with_prefix(self):
        """Test extraction with text before JSON"""
        text = 'Here is the response:\n{"intent": "tool_call", "confidence": 0.99}'
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'tool_call')
        self.assertEqual(method, 'block_extraction')

    def test_json_with_suffix(self):
        """Test extraction with text after JSON"""
        text = '{"intent": "simple_answer", "confidence": 0.80}\n\nI hope this helps!'
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'simple_answer')

    def test_json_with_stray_tokens(self):
        """Test extraction with 'JSON' prefix token"""
        text = 'JSON\n{"intent": "coding_task", "confidence": 0.90}'
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'coding_task')

    def test_nested_json(self):
        """Test extraction with nested objects"""
        text = '{"intent": "tool_call", "confidence": 0.95, "params": {"action": "status", "flags": ["--short"]}}'
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'tool_call')
        self.assertEqual(data['params']['action'], 'status')
        self.assertIn('--short', data['params']['flags'])

    def test_yaml_style_output(self):
        """Test extraction from YAML-style output"""
        text = """- intent: coding_task
- confidence: 0.85
- tool: null
- escalate: coder"""
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'coding_task')
        self.assertEqual(data['confidence'], 0.85)
        self.assertEqual(method, 'yaml_conversion')

    def test_yaml_without_bullets(self):
        """Test extraction from YAML without bullet points"""
        text = """intent: tool_call
confidence: 0.99
tool: git"""
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'tool_call')
        self.assertEqual(data['tool'], 'git')

    def test_required_keys_present(self):
        """Test required keys validation - present"""
        text = '{"intent": "coding_task", "confidence": 0.90}'
        data, method = extract_json(text, required_keys=['intent', 'confidence'])
        self.assertIsNotNone(data)

    def test_required_keys_missing(self):
        """Test required keys validation - missing"""
        text = '{"intent": "coding_task"}'
        data, method = extract_json(text, required_keys=['intent', 'tool'])
        self.assertIsNone(data)
        self.assertEqual(method, 'parse_failed')

    def test_empty_input(self):
        """Test with empty input"""
        data, method = extract_json('')
        self.assertIsNone(data)
        self.assertEqual(method, 'empty_input')

    def test_whitespace_only(self):
        """Test with whitespace only"""
        data, method = extract_json('   \n\t  ')
        self.assertIsNone(data)
        self.assertEqual(method, 'empty_input')

    def test_no_json_content(self):
        """Test with no JSON content"""
        text = 'This is just plain text without any JSON'
        data, method = extract_json(text)
        self.assertIsNone(data)
        self.assertEqual(method, 'parse_failed')

    def test_kv_extraction_fallback(self):
        """Test key-value extraction as fallback"""
        text = 'The intent is coding_task with confidence 0.85'
        data, method = extract_json(text, required_keys=['intent'])
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'coding_task')
        self.assertEqual(method, 'kv_extraction')

    def test_malformed_json(self):
        """Test with malformed JSON (missing closing brace)"""
        text = '{"intent": "coding_task", "confidence": 0.90'
        # Should fall back to YAML or KV extraction
        data, method = extract_json(text)
        # May or may not extract depending on fallback methods
        # The key is it doesn't crash
        self.assertIn(method, ['yaml_conversion', 'kv_extraction', 'parse_failed'])


class TestExtractJsonBlock(unittest.TestCase):
    """Tests for bracket-matched JSON block extraction"""

    def test_simple_block(self):
        """Test simple JSON block extraction"""
        text = 'prefix {"key": "value"} suffix'
        result = _extract_json_block(text)
        self.assertEqual(result, '{"key": "value"}')

    def test_nested_block(self):
        """Test nested JSON block extraction"""
        text = '{"outer": {"inner": "value"}}'
        result = _extract_json_block(text)
        self.assertEqual(result, '{"outer": {"inner": "value"}}')

    def test_deeply_nested(self):
        """Test deeply nested JSON"""
        text = '{"a": {"b": {"c": {"d": "value"}}}}'
        result = _extract_json_block(text)
        self.assertEqual(result, text)

    def test_string_with_braces(self):
        """Test JSON with braces inside strings"""
        text = '{"code": "if (x) { return y; }"}'
        result = _extract_json_block(text)
        self.assertEqual(result, '{"code": "if (x) { return y; }"}')

    def test_escaped_quotes(self):
        """Test JSON with escaped quotes"""
        text = '{"message": "He said \\"hello\\""}'
        result = _extract_json_block(text)
        self.assertEqual(result, '{"message": "He said \\"hello\\""}')

    def test_no_json_block(self):
        """Test text without JSON block"""
        text = 'No JSON here'
        result = _extract_json_block(text)
        self.assertIsNone(result)

    def test_unclosed_block(self):
        """Test unclosed JSON block"""
        text = '{"key": "value"'
        result = _extract_json_block(text)
        self.assertIsNone(result)


class TestParseYamlStyle(unittest.TestCase):
    """Tests for YAML-style parsing"""

    def test_bullet_style(self):
        """Test bullet point YAML style"""
        text = """- intent: coding_task
- confidence: 0.85"""
        result = _parse_yaml_style(text)
        self.assertIsNotNone(result)
        self.assertEqual(result['intent'], 'coding_task')
        self.assertEqual(result['confidence'], 0.85)

    def test_asterisk_style(self):
        """Test asterisk YAML style"""
        text = """* intent: tool_call
* tool: git"""
        result = _parse_yaml_style(text)
        self.assertIsNotNone(result)
        self.assertEqual(result['intent'], 'tool_call')
        self.assertEqual(result['tool'], 'git')

    def test_plain_style(self):
        """Test plain key: value style"""
        text = """intent: simple_answer
confidence: 0.70"""
        result = _parse_yaml_style(text)
        self.assertIsNotNone(result)
        self.assertEqual(result['intent'], 'simple_answer')

    def test_boolean_values(self):
        """Test YAML boolean values"""
        text = """enabled: true
disabled: false"""
        result = _parse_yaml_style(text)
        self.assertIsNotNone(result)
        self.assertTrue(result['enabled'])
        self.assertFalse(result['disabled'])

    def test_null_values(self):
        """Test YAML null values"""
        text = """tool: null
escalate: none"""
        result = _parse_yaml_style(text)
        self.assertIsNotNone(result)
        self.assertIsNone(result['tool'])
        self.assertIsNone(result['escalate'])

    def test_quoted_values(self):
        """Test quoted string values"""
        text = """intent: "coding_task"
description: 'create a file'"""
        result = _parse_yaml_style(text)
        self.assertIsNotNone(result)
        self.assertEqual(result['intent'], 'coding_task')
        self.assertEqual(result['description'], 'create a file')


class TestExtractKeyValues(unittest.TestCase):
    """Tests for key-value pattern extraction"""

    def test_intent_detection(self):
        """Test intent detection from text"""
        text = 'This is a coding task'
        result = _extract_key_values(text, required_keys=['intent'])
        self.assertIsNotNone(result)
        self.assertEqual(result['intent'], 'coding_task')

    def test_tool_call_detection(self):
        """Test tool_call detection"""
        text = 'This is a tool call for git'
        result = _extract_key_values(text, required_keys=['intent'])
        self.assertIsNotNone(result)
        self.assertEqual(result['intent'], 'tool_call')

    def test_confidence_extraction(self):
        """Test confidence extraction"""
        text = 'coding task with confidence 0.85'
        result = _extract_key_values(text)
        self.assertIsNotNone(result)
        self.assertEqual(result['confidence'], 0.85)

    def test_tool_extraction(self):
        """Test tool extraction"""
        text = 'tool: git command'
        result = _extract_key_values(text)
        self.assertIsNotNone(result)
        self.assertEqual(result['tool'], 'git')

    def test_default_confidence(self):
        """Test default confidence when not found"""
        text = 'This is a simple answer'
        result = _extract_key_values(text, required_keys=['intent'])
        self.assertIsNotNone(result)
        self.assertEqual(result['confidence'], 0.5)


class TestSafeJsonLoads(unittest.TestCase):
    """Tests for safe JSON loading"""

    def test_valid_json(self):
        """Test with valid JSON"""
        result = safe_json_loads('{"key": "value"}')
        self.assertEqual(result, {'key': 'value'})

    def test_invalid_json(self):
        """Test with invalid JSON returns default"""
        result = safe_json_loads('not json', default={})
        self.assertEqual(result, {})

    def test_none_input(self):
        """Test with None input"""
        result = safe_json_loads(None, default='fallback')
        self.assertEqual(result, 'fallback')


class TestRealWorldCases(unittest.TestCase):
    """Tests based on real-world malformed outputs observed from FunctionGemma"""

    def test_yaml_with_intent_confidence(self):
        """Test actual FunctionGemma YAML-style output"""
        text = """- intent: tool_call, simple_answer
- confidence: 0.90
- tool: git"""
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        # Should extract first value before comma
        self.assertIn(data['intent'], ['tool_call', 'tool_call, simple_answer'])

    def test_mixed_format(self):
        """Test mixed JSON and text"""
        text = 'Classification: {"intent": "coding_task", "confidence": 0.90} Done.'
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'coding_task')

    def test_json_prefix_token(self):
        """Test 'JSON' token before actual JSON"""
        text = 'JSON {"intent": "tool_call", "confidence": 0.95, "tool": "git"}'
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['intent'], 'tool_call')
        self.assertEqual(data['tool'], 'git')

    def test_multiple_json_blocks(self):
        """Test extraction picks first valid block"""
        text = '{"first": true} {"second": true}'
        data, method = extract_json(text)
        self.assertIsNotNone(data)
        self.assertTrue(data.get('first'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
