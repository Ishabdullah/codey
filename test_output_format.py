"""Unit tests for output format detection"""
import unittest
import sys
sys.path.insert(0, '.')


class MockOrchestrator:
    """Mock orchestrator with just the format detection methods"""

    def _determine_output_format(self, user_input: str) -> tuple:
        """Determine output file format based on user input"""
        import re
        user_lower = user_input.lower()

        base_name = self._extract_base_name(user_input)

        html_keywords = [
            'html', 'webpage', 'web page', 'website', 'web site',
            'html page', 'html file', 'html document'
        ]
        js_keywords = [
            'javascript', 'js file', 'node.js', 'nodejs',
            'react', 'vue', 'angular', 'frontend'
        ]
        ts_keywords = ['typescript', 'ts file', '.ts']
        css_keywords = ['css file', 'stylesheet', 'css stylesheet']
        shell_keywords = ['bash', 'shell script', 'sh file', '.sh']
        go_keywords = ['golang', 'go file', '.go', 'in go']
        rust_keywords = ['rust', '.rs', 'in rust']
        java_keywords = ['java', '.java', 'in java']
        cpp_keywords = ['c++', 'cpp', '.cpp', 'in c++']

        if any(kw in user_lower for kw in html_keywords):
            return (f'{base_name}.html', 'html')

        if any(kw in user_lower for kw in ts_keywords):
            return (f'{base_name}.ts', 'typescript')

        if any(kw in user_lower for kw in js_keywords):
            return (f'{base_name}.js', 'javascript')

        if any(kw in user_lower for kw in css_keywords):
            return (f'{base_name}.css', 'css')

        if any(kw in user_lower for kw in shell_keywords):
            return (f'{base_name}.sh', 'bash')

        if any(kw in user_lower for kw in go_keywords):
            return (f'{base_name}.go', 'go')

        if any(kw in user_lower for kw in rust_keywords):
            return (f'{base_name}.rs', 'rust')

        if any(kw in user_lower for kw in java_keywords):
            return (f'{base_name}.java', 'java')

        if any(kw in user_lower for kw in cpp_keywords):
            return (f'{base_name}.cpp', 'cpp')

        return (f'{base_name}.py', 'python')

    def _extract_base_name(self, user_input: str) -> str:
        """Extract a descriptive base filename from user input"""
        import re
        user_lower = user_input.lower()

        # Known key nouns to prioritize - check these first
        key_nouns = [
            'calculator', 'game', 'server', 'client', 'api', 'database', 'db',
            'parser', 'compiler', 'lexer', 'interpreter', 'scheduler',
            'handler', 'manager', 'controller', 'service', 'util', 'utils',
            'helper', 'test', 'config', 'settings', 'main', 'index',
            'todo', 'chat', 'login', 'auth', 'user', 'admin', 'dashboard',
            'timer', 'counter', 'converter', 'validator', 'generator'
        ]
        for noun in key_nouns:
            if noun in user_lower:
                return noun

        # Skip words
        skip_words = {
            'a', 'an', 'the', 'some', 'simple', 'basic', 'small', 'new',
            'file', 'code', 'script', 'program', 'app', 'application',
            'function', 'class', 'module', 'that', 'which', 'for', 'to'
        }

        # Find words after action verbs
        pattern = r'(?:create|write|make|build|generate|implement)\s+(.+?)(?:\s+(?:in|for|that|which|with)|$)'
        match = re.search(pattern, user_lower)
        if match:
            words = match.group(1).split()
            for word in words:
                word = re.sub(r'[^a-z]', '', word)
                if word and word not in skip_words and len(word) > 2:
                    return word

        return 'generated_code'


class TestOutputFormatDetection(unittest.TestCase):
    """Tests for output format detection"""

    def setUp(self):
        self.orch = MockOrchestrator()

    def test_default_python(self):
        """Test that default output is Python"""
        filename, lang = self.orch._determine_output_format("write a calculator")
        self.assertEqual(lang, 'python')
        self.assertTrue(filename.endswith('.py'))

    def test_calculator_python(self):
        """Test 'write a calculator' produces Python"""
        filename, lang = self.orch._determine_output_format("write a calculator")
        self.assertEqual(filename, 'calculator.py')
        self.assertEqual(lang, 'python')

    def test_hello_world_python(self):
        """Test 'print hello world' produces Python"""
        filename, lang = self.orch._determine_output_format("write code that prints hello world")
        self.assertEqual(lang, 'python')
        self.assertTrue(filename.endswith('.py'))

    def test_explicit_html(self):
        """Test explicit HTML request"""
        filename, lang = self.orch._determine_output_format("create an HTML page for a calculator")
        self.assertEqual(lang, 'html')
        self.assertTrue(filename.endswith('.html'))

    def test_webpage(self):
        """Test 'webpage' keyword produces HTML"""
        filename, lang = self.orch._determine_output_format("create a webpage for my portfolio")
        self.assertEqual(lang, 'html')
        self.assertTrue(filename.endswith('.html'))

    def test_website(self):
        """Test 'website' keyword produces HTML"""
        filename, lang = self.orch._determine_output_format("build a website landing page")
        self.assertEqual(lang, 'html')
        self.assertTrue(filename.endswith('.html'))

    def test_javascript(self):
        """Test JavaScript detection"""
        filename, lang = self.orch._determine_output_format("create a javascript function")
        self.assertEqual(lang, 'javascript')
        self.assertTrue(filename.endswith('.js'))

    def test_react(self):
        """Test React produces JavaScript"""
        filename, lang = self.orch._determine_output_format("create a react component")
        self.assertEqual(lang, 'javascript')
        self.assertTrue(filename.endswith('.js'))

    def test_typescript(self):
        """Test TypeScript detection"""
        filename, lang = self.orch._determine_output_format("write a typescript interface")
        self.assertEqual(lang, 'typescript')
        self.assertTrue(filename.endswith('.ts'))

    def test_bash(self):
        """Test Bash script detection"""
        filename, lang = self.orch._determine_output_format("create a bash script")
        self.assertEqual(lang, 'bash')
        self.assertTrue(filename.endswith('.sh'))

    def test_rust(self):
        """Test Rust detection"""
        filename, lang = self.orch._determine_output_format("implement a parser in rust")
        self.assertEqual(lang, 'rust')
        self.assertTrue(filename.endswith('.rs'))

    def test_go(self):
        """Test Go detection"""
        filename, lang = self.orch._determine_output_format("create a web server in go")
        self.assertEqual(lang, 'go')
        self.assertTrue(filename.endswith('.go'))

    def test_java(self):
        """Test Java detection"""
        filename, lang = self.orch._determine_output_format("write a java class")
        self.assertEqual(lang, 'java')
        self.assertTrue(filename.endswith('.java'))

    def test_cpp(self):
        """Test C++ detection"""
        filename, lang = self.orch._determine_output_format("write a c++ program")
        self.assertEqual(lang, 'cpp')
        self.assertTrue(filename.endswith('.cpp'))

    def test_generic_task_python(self):
        """Test generic coding task defaults to Python"""
        filename, lang = self.orch._determine_output_format("write code to process data")
        self.assertEqual(lang, 'python')
        self.assertTrue(filename.endswith('.py'))

    def test_api_python(self):
        """Test API without explicit language defaults to Python"""
        filename, lang = self.orch._determine_output_format("create an api endpoint")
        self.assertEqual(lang, 'python')
        self.assertEqual(filename, 'api.py')

    def test_game_python(self):
        """Test game without explicit language defaults to Python"""
        filename, lang = self.orch._determine_output_format("create a simple game")
        self.assertEqual(lang, 'python')
        self.assertTrue('game' in filename)

    def test_server_python(self):
        """Test server without explicit language defaults to Python"""
        filename, lang = self.orch._determine_output_format("build a server")
        self.assertEqual(lang, 'python')
        self.assertEqual(filename, 'server.py')


class TestBaseNameExtraction(unittest.TestCase):
    """Tests for base name extraction"""

    def setUp(self):
        self.orch = MockOrchestrator()

    def test_create_calculator(self):
        """Test 'create a calculator' extracts 'calculator'"""
        name = self.orch._extract_base_name("create a calculator")
        self.assertEqual(name, 'calculator')

    def test_write_parser(self):
        """Test 'write a parser' extracts 'parser'"""
        name = self.orch._extract_base_name("write a parser")
        self.assertEqual(name, 'parser')

    def test_build_server(self):
        """Test 'build a server' extracts 'server'"""
        name = self.orch._extract_base_name("build a server")
        self.assertEqual(name, 'server')

    def test_generic_code(self):
        """Test generic 'write code' falls back to key noun or default"""
        name = self.orch._extract_base_name("write some code")
        # Should return 'generated_code' since 'code' is generic
        self.assertEqual(name, 'generated_code')

    def test_game_keyword(self):
        """Test keyword detection for 'game'"""
        name = self.orch._extract_base_name("I want a simple game")
        self.assertEqual(name, 'game')

    def test_database_keyword(self):
        """Test keyword detection for 'database'"""
        name = self.orch._extract_base_name("need a database manager")
        self.assertEqual(name, 'database')


if __name__ == '__main__':
    unittest.main(verbosity=2)
