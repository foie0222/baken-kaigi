"""競馬AI相談システムのドメインモデルパッケージ."""
from . import domain

# infrastructure は anthropic モジュールに依存するため、
# 必要な場所で明示的にインポートする
# from . import infrastructure

__all__ = ["domain"]
