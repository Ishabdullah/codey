"""Perplexity API integration for enhanced reasoning and knowledge"""
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

class PerplexityAPI:
    """Interface to Perplexity API for deep knowledge and debugging"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.model = "llama-3.1-sonar-small-128k-online"  # Fast online model

    def _make_request(self, messages: list, max_tokens: int = 1024) -> Optional[str]:
        """Make a request to Perplexity API"""
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

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content']

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"Perplexity API HTTP Error: {e.code} - {error_body}")
            return None
        except urllib.error.URLError as e:
            print(f"Perplexity API URL Error: {e.reason}")
            return None
        except Exception as e:
            print(f"Perplexity API Error: {str(e)}")
            return None

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
