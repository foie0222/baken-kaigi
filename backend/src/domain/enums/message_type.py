"""メッセージ種別の列挙型."""
from enum import Enum


class MessageType(Enum):
    """メッセージの種別."""

    USER = "user"  # ユーザーからの入力
    AI = "ai"  # AIからの応答
    SYSTEM = "system"  # システムからの通知
