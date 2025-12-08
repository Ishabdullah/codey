"""Perplexity API integration with retry logic and fallback (v2.1)"""
import json
import urllib.request
import urllib.error
import time
from typing import Optional, Dict, Any
from pathlib import Path

class PerplexityAPI:
    """Interface to Perplexity API with enhanced robustness"""

    def __init__(self, api_key: str, config=None):
        self.api_key = api_key
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar"  # Lightweight, grounded search model (2025)

        # Load retry settings from config or use defaults
        self.retry_limit = 3
        self.timeout_seconds = 30
        self.fallback_to_local = True

        if config and hasattr(config, 'perplexity'):
            perplexity_config = config.perplexity
            self.retry_limit = perplexity_config.get('retry_limit', 3)
            self.timeout_seconds = perplexity_config.get('timeout_seconds', 30)
            self.fallback_to_local = perplexity_config.get('fallback_to_local', True)

        # Initialize error logger
        self.error_log = None
        if config and hasattr(config, 'log_dir'):
            self.error_log = Path(config.log_dir) / "perplexity_errors.log"
            self.error_log.parent.mkdir(parents=True, exist_ok=True)

    def _log_error(self, error_type: str, details: str, request_data: dict = None):
        """Log Perplexity API errors for debugging"""
        if not self.error_log:
            return

        try:
            import datetime
            log_entry = {
                'timestamp': datetime.datetime.now().isoformat(),
                'error_type': error_type,
                'details': details,
                'request': request_data
            }

            with open(self.error_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception:
            # Don't fail if logging fails
            pass

    def _make_request(self, messages: list, max_tokens: int = 1024, retry_count: int = 0) -> Optional[str]:
        """Make a request to Perplexity API with retry logic"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "top_p": 0.9
        }

        try:
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content']

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)

            # Handle rate limiting (HTTP 429)
            if e.code == 429:
                if retry_count < self.retry_limit:
                    wait_time = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s
                    print(f"⚠️  Perplexity rate limit hit. Retrying in {wait_time}s... (attempt {retry_count + 1}/{self.retry_limit})")
                    time.sleep(wait_time)
                    return self._make_request(messages, max_tokens, retry_count + 1)
                else:
                    self._log_error('RATE_LIMIT', f'Exceeded retry limit after {self.retry_limit} attempts', data)
                    print(f"❌ Perplexity rate limit exceeded. {self._fallback_message()}")
                    return None

            # Handle other HTTP errors
            self._log_error('HTTP_ERROR', f'HTTP {e.code}: {error_body}', data)
            print(f"❌ Perplexity API error (HTTP {e.code}). {self._fallback_message()}")
            return None

        except urllib.error.URLError as e:
            # Network errors (timeout, connection failed, etc.)
            if retry_count < self.retry_limit:
                wait_time = 2 ** retry_count
                print(f"⚠️  Network error connecting to Perplexity. Retrying in {wait_time}s... (attempt {retry_count + 1}/{self.retry_limit})")
                time.sleep(wait_time)
                return self._make_request(messages, max_tokens, retry_count + 1)
            else:
                self._log_error('NETWORK_ERROR', str(e.reason), data)
                print(f"❌ Perplexity network error. {self._fallback_message()}")
                return None

        except Exception as e:
            # Unexpected errors
            self._log_error('UNEXPECTED_ERROR', str(e), data)
            print(f"❌ Perplexity unexpected error: {str(e)[:100]}. {self._fallback_message()}")
            return None

    def _fallback_message(self) -> str:
        """Get fallback message"""
        if self.fallback_to_local:
            return "Falling back to local model..."
        else:
            return "Perplexity unavailable."

    def ask_perplexity(self, question: str) -> Optional[str]:
        """Ask Perplexity a general question"""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful coding assistant. Provide clear, concise, and accurate answers."
            },
            {
                "role": "user",
                "content": question
            }
        ]

        return self._make_request(messages)

    def get_code_from_perplexity(self, description: str, language: str = "python") -> Optional[str]:
        """Request code generation from Perplexity"""
        messages = [
            {
                "role": "system",
                "content": f"You are an expert {language} developer. Generate clean, production-ready code with proper error handling and comments."
            },
            {
                "role": "user",
                "content": f"Write {language} code for: {description}\n\nProvide only the code without explanations."
            }
        ]

        return self._make_request(messages, max_tokens=2048)

    def debug_with_perplexity(self, code_snippet: str, error_message: str = None, language: str = "python") -> Optional[Dict[str, Any]]:
        """Get debugging help from Perplexity"""
        prompt = f"Debug this {language} code:\n\n```{language}\n{code_snippet}\n```\n\n"

        if error_message:
            prompt += f"Error: {error_message}\n\n"

        prompt += "Provide:\n1. The issue\n2. The fix\n3. Explanation (brief)"

        messages = [
            {
                "role": "system",
                "content": f"You are an expert {language} debugger. Analyze code issues and provide fixes."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = self._make_request(messages, max_tokens=1536)

        if response:
            return {
                'success': True,
                'analysis': response,
                'has_fix': True
            }
        else:
            return {
                'success': False,
                'analysis': None,
                'has_fix': False
            }

    def research_topic(self, topic: str, context: str = None) -> Optional[str]:
        """Research a coding topic or pattern"""
        prompt = f"Research and explain: {topic}"
        if context:
            prompt += f"\n\nContext: {context}"

        prompt += "\n\nProvide practical, actionable information for implementation."

        messages = [
            {
                "role": "system",
                "content": "You are a technical researcher. Provide accurate, up-to-date information about programming topics, libraries, and best practices."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        return self._make_request(messages)

    def explain_error(self, error_message: str, code_context: str = None) -> Optional[str]:
        """Explain an error message in detail"""
        prompt = f"Explain this error: {error_message}"

        if code_context:
            prompt += f"\n\nCode context:\n```\n{code_context}\n```"

        prompt += "\n\nProvide: what it means, common causes, and how to fix it."

        messages = [
            {
                "role": "system",
                "content": "You are a debugging expert. Explain errors clearly and provide solutions."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        return self._make_request(messages)

    def get_best_practices(self, task: str, language: str = "python") -> Optional[str]:
        """Get best practices for a specific task"""
        messages = [
            {
                "role": "system",
                "content": f"You are a {language} expert. Provide current best practices and patterns."
            },
            {
                "role": "user",
                "content": f"What are the best practices for {task} in {language}? Include modern approaches and common pitfalls to avoid."
            }
        ]

        return self._make_request(messages)

    def suggest_libraries(self, task: str, language: str = "python") -> Optional[str]:
        """Suggest appropriate libraries for a task"""
        messages = [
            {
                "role": "system",
                "content": "You are a technical advisor. Recommend appropriate, well-maintained libraries."
            },
            {
                "role": "user",
                "content": f"What are the best {language} libraries for: {task}?\n\nProvide 2-3 recommendations with brief descriptions."
            }
        ]

        return self._make_request(messages, max_tokens=512)
