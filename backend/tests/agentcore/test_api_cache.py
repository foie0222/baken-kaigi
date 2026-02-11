"""JRA-VAN APIセッション内キャッシュのテスト."""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.api_cache import SessionCache, _infer_data_type, get_session_cache


class TestSessionCache:
    """SessionCache のテスト."""

    def test_キャッシュ格納と取得(self):
        cache = SessionCache()
        cache.set("https://api.example.com/races/1", {"race": "data"})
        result = cache.get("https://api.example.com/races/1")
        assert result == {"race": "data"}

    def test_キャッシュミス時はNoneを返す(self):
        cache = SessionCache()
        result = cache.get("https://api.example.com/not-cached")
        assert result is None

    def test_パラメータ付きURLのキャッシュ(self):
        cache = SessionCache()
        params = {"year": "2026", "month": "02"}
        cache.set("https://api.example.com/races", {"data": 1}, params=params)
        assert cache.get("https://api.example.com/races", params=params) == {"data": 1}
        # パラメータなしではヒットしない
        assert cache.get("https://api.example.com/races") is None

    def test_異なるパラメータではキャッシュが分離される(self):
        cache = SessionCache()
        cache.set("https://api.example.com/races", {"data": "a"}, params={"id": "1"})
        cache.set("https://api.example.com/races", {"data": "b"}, params={"id": "2"})
        assert cache.get("https://api.example.com/races", params={"id": "1"}) == {"data": "a"}
        assert cache.get("https://api.example.com/races", params={"id": "2"}) == {"data": "b"}

    def test_TTL経過後はキャッシュが無効化される(self):
        cache = SessionCache()
        # TTL 0秒のデータ種別を使って即時期限切れを模擬
        with patch.object(SessionCache, "DEFAULT_TTL", {"test": 0, "default": 0}):
            cache.set("https://api.example.com/test", {"data": 1}, data_type="test")
            time.sleep(0.01)
            result = cache.get("https://api.example.com/test")
            assert result is None

    def test_TTL内はキャッシュが有効(self):
        cache = SessionCache()
        cache.set("https://api.example.com/test", {"data": 1}, data_type="race_info")
        result = cache.get("https://api.example.com/test")
        assert result == {"data": 1}

    def test_キャッシュ上書き(self):
        cache = SessionCache()
        cache.set("https://api.example.com/races/1", {"v": 1})
        cache.set("https://api.example.com/races/1", {"v": 2})
        assert cache.get("https://api.example.com/races/1") == {"v": 2}


class TestSessionCacheStats:
    """キャッシュ統計のテスト."""

    def test_初期状態の統計(self):
        cache = SessionCache()
        stats = cache.stats
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0
        assert stats["cache_size"] == 0

    def test_ヒット率の計算(self):
        cache = SessionCache()
        cache.set("https://api.example.com/test", {"data": 1})
        cache.get("https://api.example.com/test")  # hit
        cache.get("https://api.example.com/test")  # hit
        cache.get("https://api.example.com/miss")  # miss
        stats = cache.stats
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert abs(stats["hit_rate"] - 2 / 3) < 0.001

    def test_キャッシュサイズ(self):
        cache = SessionCache()
        cache.set("https://api.example.com/a", {"data": 1})
        cache.set("https://api.example.com/b", {"data": 2})
        assert cache.stats["cache_size"] == 2


class TestInferDataType:
    """_infer_data_type のテスト."""

    def test_オッズURL(self):
        assert _infer_data_type("https://api.example.com/odds/123") == "odds"

    def test_レース結果URL(self):
        assert _infer_data_type("https://api.example.com/race/123/result") == "results"

    def test_騎手URL(self):
        assert _infer_data_type("https://api.example.com/jockey/456") == "jockey_info"

    def test_調教師URL(self):
        assert _infer_data_type("https://api.example.com/trainer/789") == "trainer_info"

    def test_馬URL(self):
        assert _infer_data_type("https://api.example.com/horse/001") == "horse_info"

    def test_種牡馬URL(self):
        assert _infer_data_type("https://api.example.com/stallion/002") == "horse_info"

    def test_レースURL(self):
        assert _infer_data_type("https://api.example.com/race/123") == "race_info"

    def test_不明なURL(self):
        assert _infer_data_type("https://api.example.com/unknown") == "default"


class TestCacheKeyGeneration:
    """キャッシュキー生成のテスト."""

    def test_同じURLは同じキー(self):
        cache = SessionCache()
        key1 = cache._make_key("https://api.example.com/test")
        key2 = cache._make_key("https://api.example.com/test")
        assert key1 == key2

    def test_異なるURLは異なるキー(self):
        cache = SessionCache()
        key1 = cache._make_key("https://api.example.com/a")
        key2 = cache._make_key("https://api.example.com/b")
        assert key1 != key2

    def test_同じURLでも異なるパラメータは異なるキー(self):
        cache = SessionCache()
        key1 = cache._make_key("https://api.example.com/test", {"id": "1"})
        key2 = cache._make_key("https://api.example.com/test", {"id": "2"})
        assert key1 != key2

    def test_パラメータの順序が違っても同じキー(self):
        cache = SessionCache()
        key1 = cache._make_key("https://api.example.com/test", {"a": "1", "b": "2"})
        key2 = cache._make_key("https://api.example.com/test", {"b": "2", "a": "1"})
        assert key1 == key2

    def test_パラメータNoneとパラメータなしは同じキー(self):
        cache = SessionCache()
        key1 = cache._make_key("https://api.example.com/test", None)
        key2 = cache._make_key("https://api.example.com/test")
        assert key1 == key2


class TestGetSessionCache:
    """get_session_cache のテスト."""

    def test_同一インスタンスを返す(self):
        cache1 = get_session_cache()
        cache2 = get_session_cache()
        assert cache1 is cache2

    def test_SessionCacheインスタンスを返す(self):
        cache = get_session_cache()
        assert isinstance(cache, SessionCache)
