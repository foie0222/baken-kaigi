"""認証レスポンスヘルパーのテスト."""
import json

from src.api.response import forbidden_response, unauthorized_response


class TestUnauthorizedResponse:
    """unauthorized_responseのテスト."""

    def test_401ステータスコード(self):
        resp = unauthorized_response()
        assert resp["statusCode"] == 401

    def test_デフォルトメッセージ(self):
        resp = unauthorized_response()
        body = json.loads(resp["body"])
        assert body["error"]["message"] == "Authentication required"

    def test_カスタムメッセージ(self):
        resp = unauthorized_response("Token expired")
        body = json.loads(resp["body"])
        assert body["error"]["message"] == "Token expired"


class TestForbiddenResponse:
    """forbidden_responseのテスト."""

    def test_403ステータスコード(self):
        resp = forbidden_response()
        assert resp["statusCode"] == 403

    def test_デフォルトメッセージ(self):
        resp = forbidden_response()
        body = json.loads(resp["body"])
        assert body["error"]["message"] == "Access denied"
