"""JRA-VAN APIレスポンスのセッション内キャッシュ.

AgentCore Runtimeは各セッションを独立したmicroVMで実行するため、
このキャッシュはセッションスコープ（リクエスト完了で破棄）。
"""

import hashlib
import json
import logging
import time

logger = logging.getLogger("agentcore.tools.api_cache")


def _infer_data_type(url: str) -> str:
    """URLからデータ種別を推定."""
    if "/odds" in url:
        return "odds"
    if "/race" in url and "/result" in url:
        return "results"
    if "/jockey" in url:
        return "jockey_info"
    if "/trainer" in url:
        return "trainer_info"
    if "/horse" in url or "/stallion" in url:
        return "horse_info"
    if "/race" in url:
        return "race_info"
    return "default"


class SessionCache:
    """TTL付きセッション内メモリキャッシュ."""

    DEFAULT_TTL = {
        "race_info": 3600,
        "horse_info": 86400,
        "jockey_info": 86400,
        "trainer_info": 86400,
        "odds": 300,
        "results": 86400,
        "default": 1800,
    }

    def __init__(self):
        self._cache: dict[str, tuple[float, object]] = {}
        self._hits = 0
        self._misses = 0

    def _make_key(self, url: str, params: dict | None = None) -> str:
        """URLとパラメータからキャッシュキーを生成."""
        key_data = url
        if params:
            key_data += json.dumps(params, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, url: str, params: dict | None = None) -> object | None:
        """キャッシュからデータを取得. ヒット時はデータ、ミス時はNone."""
        key = self._make_key(url, params)
        if key in self._cache:
            expiry, data = self._cache[key]
            if time.time() < expiry:
                self._hits += 1
                logger.debug("Cache hit: %s", url)
                return data
            del self._cache[key]
        self._misses += 1
        return None

    def set(
        self,
        url: str,
        data: object,
        params: dict | None = None,
        data_type: str | None = None,
    ) -> None:
        """キャッシュにデータを保存."""
        if data_type is None:
            data_type = _infer_data_type(url)
        key = self._make_key(url, params)
        ttl = self.DEFAULT_TTL.get(data_type, self.DEFAULT_TTL["default"])
        self._cache[key] = (time.time() + ttl, data)

    @property
    def stats(self) -> dict:
        """キャッシュ統計を返す."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0,
            "cache_size": len(self._cache),
        }


_session_cache = SessionCache()


def get_session_cache() -> SessionCache:
    """グローバルキャッシュインスタンスを取得."""
    return _session_cache
