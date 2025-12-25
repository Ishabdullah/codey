"""Intent Router - Low-latency intent classification using small model"""
import json
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path

from models.base import BaseModel
from models.lifecycle import GGUFModel
from router.prompts import get_intent_prompt, REGEX_PATTERNS


@dataclass
class IntentResult:
    """Result of intent classification

    Attributes:
        intent: Classification type (tool_call, simple_answer, coding_task, algorithm_task)
        confidence: Confidence score (0.0 - 1.0)
        params: Extracted parameters from user input
        escalate_to: Which model to escalate to (None, "coder", "algorithm")
        tool: Tool type for tool_call intent ("git", "shell", "file", None)
        raw_response: Raw model output for debugging
        used_fallback: Whether regex fallback was used
    """
    intent: str
    confidence: float
    params: Dict[str, Any] = field(default_factory=dict)
    escalate_to: Optional[str] = None
    tool: Optional[str] = None
    raw_response: str = ""
    used_fallback: bool = False

    def should_escalate(self) -> bool:
        """Check if this intent requires escalation to a larger model"""
        return self.escalate_to is not None

    def is_tool_call(self) -> bool:
        """Check if this is a direct tool call"""
        return self.intent == "tool_call"

    def is_simple_answer(self) -> bool:
        """Check if router can handle this directly"""
        return self.intent == "simple_answer"

    def is_coding_task(self) -> bool:
        """Check if this requires the coding model"""
        return self.intent == "coding_task"

    def is_algorithm_task(self) -> bool:
        """Check if this requires the algorithm specialist"""
        return self.intent == "algorithm_task"


class IntentRouter(GGUFModel):
    """Low-latency intent classification using FunctionGemma 270M

    This model is always-resident and provides fast classification of user intents.
    It determines whether to:
    - Execute a tool directly (git, shell, file)
    - Answer a simple question
    - Escalate to the coder model
    - Escalate to the algorithm specialist
    """

    def __init__(self, model_path: Path, config: Dict[str, Any]):
        """Initialize intent router

        Args:
            model_path: Path to router GGUF model
            config: Router-specific configuration
        """
        super().__init__(model_path, config)
        self.confidence_thresholds = config.get('confidence_thresholds', {
            'tool': 0.90,
            'simple': 0.85,
            'code': 0.70,
        })

    def classify(self, user_input: str, context: Optional[Dict] = None) -> IntentResult:
        """Classify user intent

        Args:
            user_input: The user's request
            context: Optional context from previous interactions

        Returns:
            IntentResult with classification and extracted parameters
        """
        # Ensure model is loaded
        self._ensure_loaded()

        # Generate classification prompt
        prompt = get_intent_prompt(user_input, context)

        try:
            # Get model response
            response = self.generate(
                prompt,
                max_tokens=150,
                temperature=0.1,  # Low temperature for classification
                stop=["User:", "\n\n", "```"]
            )

            # Parse JSON response
            intent_result = self._parse_response(response, user_input)

            # If confidence is too low, try fallback
            if intent_result.confidence < 0.5:
                intent_result = self._fallback_regex(user_input)

            return intent_result

        except Exception as e:
            print(f"Intent classification error: {e}")
            # Fall back to regex
            return self._fallback_regex(user_input)

    def _parse_response(self, response: str, user_input: str) -> IntentResult:
        """Parse model JSON output into IntentResult

        Args:
            response: Raw model output
            user_input: Original user input (for fallback)

        Returns:
            Parsed IntentResult
        """
        try:
            # Try to extract JSON from response
            # Look for JSON block in response
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
            else:
                # Try parsing entire response
                data = json.loads(response)

            # Validate required fields
            if 'intent' not in data or 'confidence' not in data:
                raise ValueError("Missing required fields in response")

            # Build IntentResult
            return IntentResult(
                intent=data.get('intent', 'simple_answer'),
                confidence=float(data.get('confidence', 0.5)),
                params=data.get('params', {}),
                escalate_to=data.get('escalate'),
                tool=data.get('tool'),
                raw_response=response,
                used_fallback=False
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"JSON parse error: {e}")
            print(f"Response was: {response[:200]}")
            # Fall back to regex
            return self._fallback_regex(user_input)

    def _fallback_regex(self, user_input: str) -> IntentResult:
        """Fallback to regex-based classification

        Args:
            user_input: User's request

        Returns:
            IntentResult based on regex matching
        """
        user_lower = user_input.lower().strip()

        # Check git commands
        for pattern in REGEX_PATTERNS["tool_call_git"]:
            if re.search(pattern, user_lower):
                action = self._extract_git_action(user_input)
                return IntentResult(
                    intent="tool_call",
                    confidence=0.95,
                    tool="git",
                    params={"action": action, "raw_command": user_input},
                    escalate_to=None,
                    raw_response="regex_fallback",
                    used_fallback=True
                )

        # Check shell commands
        for pattern in REGEX_PATTERNS["tool_call_shell"]:
            if re.search(pattern, user_lower):
                return IntentResult(
                    intent="tool_call",
                    confidence=0.90,
                    tool="shell",
                    params={"command": user_input},
                    escalate_to=None,
                    raw_response="regex_fallback",
                    used_fallback=True
                )

        # Check file operations
        for pattern in REGEX_PATTERNS["tool_call_file"]:
            if re.search(pattern, user_lower):
                filename = self._extract_filename(user_input)
                return IntentResult(
                    intent="tool_call",
                    confidence=0.88,
                    tool="file",
                    params={"filename": filename, "raw_input": user_input},
                    escalate_to=None,
                    raw_response="regex_fallback",
                    used_fallback=True
                )

        # Check coding tasks
        for pattern in REGEX_PATTERNS["coding_task"]:
            if re.search(pattern, user_lower):
                filename = self._extract_filename(user_input)
                return IntentResult(
                    intent="coding_task",
                    confidence=0.75,
                    params={"filename": filename, "task": user_input},
                    escalate_to="coder",
                    raw_response="regex_fallback",
                    used_fallback=True
                )

        # Check algorithm tasks
        for pattern in REGEX_PATTERNS["algorithm_task"]:
            if re.search(pattern, user_lower):
                return IntentResult(
                    intent="algorithm_task",
                    confidence=0.80,
                    params={"task": user_input},
                    escalate_to="algorithm",
                    raw_response="regex_fallback",
                    used_fallback=True
                )

        # Check simple answer
        for pattern in REGEX_PATTERNS["simple_answer"]:
            if re.search(pattern, user_lower):
                return IntentResult(
                    intent="simple_answer",
                    confidence=0.70,
                    params={"question": user_input},
                    escalate_to=None,
                    raw_response="regex_fallback",
                    used_fallback=True
                )

        # Default to simple_answer with low confidence
        return IntentResult(
            intent="simple_answer",
            confidence=0.50,
            params={"question": user_input},
            escalate_to=None,
            raw_response="regex_fallback_default",
            used_fallback=True
        )

    def _extract_git_action(self, user_input: str) -> str:
        """Extract git action from input

        Args:
            user_input: User's git command

        Returns:
            Git action (status, commit, push, etc.)
        """
        actions = ['status', 'diff', 'log', 'add', 'commit', 'push', 'pull', 'clone', 'init']
        user_lower = user_input.lower()

        for action in actions:
            if action in user_lower:
                return action

        return 'status'  # Default

    def _extract_filename(self, user_input: str) -> Optional[str]:
        """Extract filename from input

        Args:
            user_input: User's request

        Returns:
            Extracted filename or None
        """
        # Look for common file extensions
        extensions = ['.py', '.js', '.java', '.cpp', '.c', '.go', '.rs', '.ts', '.rb', '.php']
        for ext in extensions:
            match = re.search(r'([a-zA-Z0-9_-]+' + re.escape(ext) + r')', user_input)
            if match:
                return match.group(1)

        # Look for filename pattern
        match = re.search(r'file\s+(?:called\s+)?([a-zA-Z0-9_.-]+)', user_input, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def should_escalate_confidence(self, confidence: float, intent: str) -> bool:
        """Determine if confidence is too low and should escalate

        Args:
            confidence: Classification confidence
            intent: Classified intent type

        Returns:
            True if should escalate to larger model
        """
        threshold = self.confidence_thresholds.get('code', 0.70)

        if intent == "tool_call":
            threshold = self.confidence_thresholds.get('tool', 0.90)
        elif intent == "simple_answer":
            threshold = self.confidence_thresholds.get('simple', 0.85)

        return confidence < threshold
