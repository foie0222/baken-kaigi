"""エージェントスタイル列挙型."""
from enum import Enum


class AgentStyle(str, Enum):
    """エージェントのベーススタイル."""

    SOLID = "solid"  # 堅実型（本命重視、的中率優先）
    LONGSHOT = "longshot"  # 一発型（穴馬重視、回収率優先）
    DATA = "data"  # データ型（数字・指数重視）
    PACE = "pace"  # 展開型（馬場・脚質・枠順重視）
