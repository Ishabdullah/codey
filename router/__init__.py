"""Intent Router Package

This package contains the intent classification system that determines
how to route user requests to the appropriate handler (tool, model, etc.)
"""

from router.intent_router import IntentRouter, IntentResult

__all__ = ['IntentRouter', 'IntentResult']
