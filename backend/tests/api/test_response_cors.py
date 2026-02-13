"""CORSレスポンスヘルパーのテスト."""
import json
import os
from unittest.mock import patch

from src.api.response import (
    bad_request_response,
    error_response,
    forbidden_response,
    get_cors_origin,
    internal_error_response,
    not_found_response,
    success_response,
    unauthorized_response,
)


def _make_event(origin: str) -> dict:
    """Origin ヘッダー付きのイベントを生成する."""
    return {"headers": {"origin": origin}}


class TestGetCorsOrigin:
    """get_cors_originのテスト."""

    def test_eventなしの場合デフォルトオリジンを返す(self):
        result = get_cors_origin()
        assert result == "https://bakenkaigi.com"

    def test_eventがNoneの場合デフォルトオリジンを返す(self):
        result = get_cors_origin(None)
        assert result == "https://bakenkaigi.com"

    def test_許可オリジンbakenkaigi(self):
        event = _make_event("https://bakenkaigi.com")
        result = get_cors_origin(event)
        assert result == "https://bakenkaigi.com"

    def test_許可オリジンwww_bakenkaigi(self):
        event = _make_event("https://www.bakenkaigi.com")
        result = get_cors_origin(event)
        assert result == "https://www.bakenkaigi.com"

    def test_非許可オリジンはデフォルトを返す(self):
        event = _make_event("https://evil.example.com")
        result = get_cors_origin(event)
        assert result == "https://bakenkaigi.com"

    def test_空のOriginヘッダーはデフォルトを返す(self):
        event = {"headers": {"origin": ""}}
        result = get_cors_origin(event)
        assert result == "https://bakenkaigi.com"

    def test_headersがNoneの場合デフォルトを返す(self):
        event = {"headers": None}
        result = get_cors_origin(event)
        assert result == "https://bakenkaigi.com"

    def test_headersキーがない場合デフォルトを返す(self):
        event = {}
        result = get_cors_origin(event)
        assert result == "https://bakenkaigi.com"

    def test_Originヘッダー大文字始まり(self):
        event = {"headers": {"Origin": "https://www.bakenkaigi.com"}}
        result = get_cors_origin(event)
        assert result == "https://www.bakenkaigi.com"


class TestSuccessResponseCors:
    """success_responseのCORSテスト."""

    def test_eventなしの場合デフォルトオリジン(self):
        resp = success_response({"ok": True})
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://bakenkaigi.com"

    def test_許可オリジン指定時にそのオリジンを返す(self):
        event = _make_event("https://www.bakenkaigi.com")
        resp = success_response({"ok": True}, event=event)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://www.bakenkaigi.com"

    def test_非許可オリジン指定時にデフォルトを返す(self):
        event = _make_event("https://evil.example.com")
        resp = success_response({"ok": True}, event=event)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://bakenkaigi.com"


    def test_Allow_HeadersにX_Guest_Idとx_api_keyが含まれる(self):
        resp = success_response({"ok": True})
        tokens = {h.strip() for h in resp["headers"]["Access-Control-Allow-Headers"].split(",")}
        assert "X-Guest-Id" in tokens
        assert "x-api-key" in tokens


class TestErrorResponseCors:
    """error_responseのCORSテスト."""

    def test_eventなしの場合デフォルトオリジン(self):
        resp = error_response("error")
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://bakenkaigi.com"

    def test_許可オリジン指定時にそのオリジンを返す(self):
        event = _make_event("https://www.bakenkaigi.com")
        resp = error_response("error", event=event)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://www.bakenkaigi.com"

    def test_Allow_HeadersにX_Guest_Idとx_api_keyが含まれる(self):
        resp = error_response("error")
        tokens = {h.strip() for h in resp["headers"]["Access-Control-Allow-Headers"].split(",")}
        assert "X-Guest-Id" in tokens
        assert "x-api-key" in tokens


class TestWrapperResponseCors:
    """ラッパーレスポンス関数のCORSテスト."""

    def test_bad_request_responseにevent伝播(self):
        event = _make_event("https://www.bakenkaigi.com")
        resp = bad_request_response("bad", event=event)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://www.bakenkaigi.com"

    def test_not_found_responseにevent伝播(self):
        event = _make_event("https://www.bakenkaigi.com")
        resp = not_found_response("Resource", event=event)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://www.bakenkaigi.com"

    def test_unauthorized_responseにevent伝播(self):
        event = _make_event("https://www.bakenkaigi.com")
        resp = unauthorized_response(event=event)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://www.bakenkaigi.com"

    def test_forbidden_responseにevent伝播(self):
        event = _make_event("https://www.bakenkaigi.com")
        resp = forbidden_response(event=event)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://www.bakenkaigi.com"

    def test_internal_error_responseにevent伝播(self):
        event = _make_event("https://www.bakenkaigi.com")
        resp = internal_error_response(event=event)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://www.bakenkaigi.com"

    def test_ラッパーにeventなしの場合デフォルト(self):
        resp = bad_request_response("bad")
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://bakenkaigi.com"


class TestDevOrigins:
    """ALLOW_DEV_ORIGINS環境変数のテスト."""

    def test_dev_origins無効時はlocalhostを拒否(self):
        event = _make_event("http://localhost:5173")
        result = get_cors_origin(event)
        assert result == "https://bakenkaigi.com"

    @patch.dict(os.environ, {"ALLOW_DEV_ORIGINS": "true"})
    def test_dev_origins有効時はlocalhostを許可(self):
        # ALLOWED_ORIGINS はモジュールロード時に設定されるため、リロードが必要
        import importlib

        import src.api.response as response_mod
        importlib.reload(response_mod)
        try:
            event = _make_event("http://localhost:5173")
            result = response_mod.get_cors_origin(event)
            assert result == "http://localhost:5173"
        finally:
            # リロードして元に戻す
            if "ALLOW_DEV_ORIGINS" in os.environ:
                del os.environ["ALLOW_DEV_ORIGINS"]
            importlib.reload(response_mod)
