"""クライアント実装."""
# ClaudeAIClient は anthropic に依存するため、必要な時に直接インポートする
# from .claude_ai_client import ClaudeAIClient
from .mock_ai_client import MockAIClient

__all__ = ["MockAIClient"]
