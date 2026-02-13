"""GAMBLE-OS オッズAPIクライアント（AgentCoreツール用）.

RealtimeOddsClient の簡易版。AgentCore Runtime から呼び出す。
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

_API_BASE_URL = None
API_TIMEOUT_SECONDS = 30


def _get_api_base_url() -> str:
    """API Base URLを取得する（キャッシュ付き）."""
    global _API_BASE_URL
    if _API_BASE_URL is None:
        _API_BASE_URL = os.environ.get(
            "GAMBLEOS_API_URL", "https://api.gamble-os.net"
        )
    return _API_BASE_URL


def get_odds_history(race_id: str) -> list[dict]:
    """オッズ変動履歴を取得する."""
    try:
        response = requests.get(
            f"{_get_api_base_url()}/races/{race_id}/odds-history",
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


def get_win_odds(race_id: str) -> list[dict]:
    """単勝・複勝オッズを取得する."""
    try:
        response = requests.get(
            f"{_get_api_base_url()}/races/{race_id}/odds",
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("ret") != "0":
            logger.warning(f"Odds API error: {data.get('msg')}")
            return []
        return data.get("odds", [])
    except Exception as e:
        logger.error(f"Failed to get win odds: {e}")
        return []
