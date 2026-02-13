"""DynamoDB共通ユーティリティ."""

from decimal import Decimal
from typing import Any


def convert_floats(obj: Any) -> Any:
    """DynamoDB用にfloatをDecimalに再帰的に変換."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj
