"""Intent Router - Low-latency intent classification using small model"""
import json
import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path

from models.base import BaseModel
from models.lifecycle import GGUFModel
from router.prompts import get_intent_prompt, REGEX_PATTERNS
from utils.json_utils import extract_json

logger = logging.getLogger(__name__)


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

        # PRE-CHECK: Prioritize regex for obvious coding tasks to prevent router hallucination
        user_lower = user_input.lower().strip()
        for pattern in REGEX_PATTERNS["coding_task"]:
            if re.search(pattern, user_lower):
                filename = self._extract_filename(user_input)
                logger.debug(f"Pre-check matched coding task: {pattern}")
                return IntentResult(
                    intent="coding_task",
                    confidence=1.0,
                    params={"filename": filename, "task": user_input},
                    escalate_to="coder",
                    raw_response="regex_precheck",
                    used_fallback=True
                )

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

            # Normalize tool name
            if intent_result.tool:
                intent_result.tool = self._normalize_tool(intent_result.tool)

            # Validation: If tool_call has no tool, it's invalid -> fallback
            if intent_result.is_tool_call() and not intent_result.tool:
                logger.warning("Model predicted tool_call but missing tool. Falling back to regex.")
                intent_result = self._fallback_regex(user_input)

            # If confidence is too low, try fallback
            elif intent_result.confidence < 0.5:
                intent_result = self._fallback_regex(user_input)

            return intent_result

        except Exception as e:
            print(f"Intent classification error: {e}")
            # Fall back to regex
            return self._fallback_regex(user_input)

    def _parse_response(self, response: str, user_input: str) -> IntentResult:
        """Parse model JSON output into IntentResult

        Uses robust JSON extraction that handles:
        - Stray tokens before/after JSON
        - YAML-style outputs
        - Nested objects with proper bracket matching
        - Malformed responses with graceful fallback

        Args:
            response: Raw model output
            user_input: Original user input (for fallback)

        Returns:
            Parsed IntentResult
        """
        # Use robust JSON extraction with required keys
        required_keys = ['intent']  # confidence can be defaulted
        data, extraction_method = extract_json(response, required_keys)

        if data is not None:
            # Log extraction method for debugging
            logger.debug(f"JSON extracted via: {extraction_method}")

            # Normalize intent value (handle variations)
            intent = self._normalize_intent(data.get('intent', 'simple_answer'))

            # Extract confidence with default
            try:
                confidence = float(data.get('confidence', 0.5))
                # Clamp to valid range
                confidence = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                confidence = 0.5

            # Determine escalation based on intent
            escalate_to = data.get('escalate')
            if escalate_to is None:
                if intent == 'coding_task':
                    escalate_to = 'coder'
                elif intent == 'algorithm_task':
                    escalate_to = 'algorithm'

            return IntentResult(
                intent=intent,
                confidence=confidence,
                params=data.get('params', {}),
                escalate_to=escalate_to,
                tool=data.get('tool'),
                raw_response=response,
                used_fallback=False
            )

        # Log malformed response for debugging
        logger.warning(f"Failed to extract JSON from response: {response[:200]}...")
        logger.debug(f"Full response: {response}")

        # Fall back to regex
        return self._fallback_regex(user_input)

    def _normalize_tool(self, tool: str) -> Optional[str]:
        """Normalize tool name to standard format

        Args:
            tool: Raw tool name

        Returns:
            Normalized tool name or None if invalid
        """
        tool = str(tool).lower().strip()

        if tool in ('git', 'github'):
            return 'git'
        
        if tool in ('shell', 'bash', 'terminal', 'cmd', 'command', 'dir', 'directory'):
            return 'shell'
        
        if tool in ('file', 'read', 'write', 'filesystem', 'fs'):
            return 'file'
            
        return tool

    def _normalize_intent(self, intent: str) -> str:
        """Normalize intent value to standard format

        Handles variations like:
        - "tool_call" / "tool call" / "toolcall"
        - "coding_task" / "coding task" / "code"
        - etc.

        Args:
            intent: Raw intent string

        Returns:
            Normalized intent string
        """
        intent = str(intent).lower().strip()

        # Normalize tool_call variations
        if intent in ('tool_call', 'tool call', 'toolcall', 'tool'):
            return 'tool_call'

        # Normalize coding_task variations
        if intent in ('coding_task', 'coding task', 'codingtask', 'code', 'coding', 'code_generation', 'code_task'):
            return 'coding_task'

        # Normalize algorithm_task variations
        if intent in ('algorithm_task', 'algorithm task', 'algorithmtask', 'algorithm', 'algo'):
            return 'algorithm_task'

        # Normalize simple_answer variations
        if intent in ('simple_answer', 'simple answer', 'simpleanswer', 'answer', 'simple', 'question', 'error'):
            # Note: 'error' intent from model usually means it didn't understand, so we treat as simple Q&A
            return 'simple_answer'

        # Default to simple_answer for unknown intents
        logger.warning(f"Unknown intent '{intent}', defaulting to simple_answer")
        return 'simple_answer'

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
