"""リアルタイムオッズクライアント.

GAMBLE-OS APIからリアルタイムのオッズデータを取得する。
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

DEFAULT_API_BASE_URL = "https://api.gamble-os.net"
API_TIMEOUT_SECONDS = 30


class RealtimeOddsClient:
    """GAMBLE-OSリアルタイムオッズAPIクライアント."""

    def __init__(self, api_base_url: str | None = None):
        self._api_base_url = api_base_url or os.environ.get(
            "GAMBLEOS_API_URL", DEFAULT_API_BASE_URL
        )

    def get_win_odds(self, race_id: str) -> list[dict]:
        """単勝・複勝オッズを取得する."""
        try:
            response = requests.get(
                f"{self._api_base_url}/races/{race_id}/odds",
                timeout=API_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("ret") != "0":
                logger.warning(f"Odds API error: {data.get('msg')}")
                return []
            return data.get("odds", [])
        except Exception as e:
            logger.error(f"Failed to get odds: {e}")
            return []

    def get_odds_history(self, race_id: str) -> list[dict]:
        """オッズ変動履歴を取得する."""
        try:
            response = requests.get(
                f"{self._api_base_url}/races/{race_id}/odds-history",
                timeout=API_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("ret") != "0":
                logger.warning(f"Odds history API error: {data.get('msg')}")
                return []
            return data.get("history", [])
        except Exception as e:
            logger.error(f"Failed to get odds history: {e}")
            return []
