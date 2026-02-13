"""JRA-VAN API クライアント共通モジュールのテスト."""

import sys
from pathlib import Path

import pytest
import requests
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

# agentcore をパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "agentcore"))
from tools import jravan_client


@pytest.fixture(autouse=True)
def reset_cache():
    """各テスト前にキャッシュをリセット."""
    jravan_client._cached_api_key = None
    yield
    jravan_client._cached_api_key = None


class TestGetApiKey:
    """get_api_key 関数のテスト."""

    def test_returns_cached_key_if_available(self):
        """キャッシュされたAPIキーがある場合はそれを返す."""
        jravan_client._cached_api_key = "cached_key"

        result = jravan_client.get_api_key()

        assert result == "cached_key"

    @patch.object(jravan_client, 'JRAVAN_API_KEY', 'env_api_key')
    def test_returns_env_var_if_set(self):
        """環境変数が設定されている場合はそれを返す."""
        result = jravan_client.get_api_key()

        assert result == "env_api_key"
        assert jravan_client._cached_api_key == "env_api_key"

    @patch.object(jravan_client, 'JRAVAN_API_KEY', '')
    @patch('boto3.client')
    def test_fetches_from_api_gateway(self, mock_boto_client):
        """環境変数がない場合はAPI Gatewayから取得."""
        mock_apigateway = MagicMock()
        mock_boto_client.return_value = mock_apigateway
        mock_apigateway.get_api_key.return_value = {'value': 'gateway_api_key'}

        result = jravan_client.get_api_key()

        assert result == "gateway_api_key"
        assert jravan_client._cached_api_key == "gateway_api_key"
        mock_boto_client.assert_called_once_with("apigateway", region_name="ap-northeast-1")
        mock_apigateway.get_api_key.assert_called_once_with(
            apiKey=jravan_client.JRAVAN_API_KEY_ID,
            includeValue=True
        )

    @patch.object(jravan_client, 'JRAVAN_API_KEY', '')
    @patch('boto3.client')
    def test_returns_empty_on_client_error(self, mock_boto_client):
        """ClientErrorが発生した場合は空文字列を返す."""
        mock_apigateway = MagicMock()
        mock_boto_client.return_value = mock_apigateway
        mock_apigateway.get_api_key.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'API Key not found'}},
            'GetApiKey'
        )

        result = jravan_client.get_api_key()

        assert result == ""
        assert jravan_client._cached_api_key == ""


class TestGetHeaders:
    """get_headers 関数のテスト."""

    @patch.object(jravan_client, 'get_api_key')
    def test_includes_api_key_when_available(self, mock_get_api_key):
        """APIキーがある場合はヘッダーに含める."""
        mock_get_api_key.return_value = "test_api_key"

        headers = jravan_client.get_headers()

        assert headers == {"x-api-key": "test_api_key"}

    @patch.object(jravan_client, 'get_api_key')
    def test_returns_empty_dict_when_no_api_key(self, mock_get_api_key):
        """APIキーがない場合は空の辞書を返す."""
        mock_get_api_key.return_value = ""

        headers = jravan_client.get_headers()

        assert headers == {}


class TestGetApiUrl:
    """get_api_url 関数のテスト."""

    def test_returns_configured_url(self):
        """設定されたURLを返す."""
        url = jravan_client.get_api_url()

        assert url == jravan_client.JRAVAN_API_URL


class TestCachedGet:
    """cached_get 関数のテスト."""

    @pytest.fixture(autouse=True)
    def reset_session_cache(self):
        """テストごとにセッションキャッシュをリセット."""
        from tools.api_cache import get_session_cache
        cache = get_session_cache()
        cache._cache.clear()
        cache._hits = 0
        cache._misses = 0
        yield

    @patch("tools.jravan_client.requests.get")
    @patch.object(jravan_client, "get_headers", return_value={"x-api-key": "test"})
    def test_キャッシュミス時はrequests_getが呼ばれる(self, mock_headers, mock_get):
        """初回呼び出し時はAPIリクエストが実行される."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_get.return_value = mock_response

        result = jravan_client.cached_get("https://api.example.com/races/1")

        mock_get.assert_called_once()
        assert result is mock_response

    @patch("tools.jravan_client.requests.get")
    @patch.object(jravan_client, "get_headers", return_value={"x-api-key": "test"})
    def test_キャッシュヒット時はrequests_getが呼ばれない(self, mock_headers, mock_get):
        """2回目の同一URLではAPIリクエストが省略される."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_get.return_value = mock_response

        jravan_client.cached_get("https://api.example.com/races/1")
        mock_get.reset_mock()

        result = jravan_client.cached_get("https://api.example.com/races/1")

        mock_get.assert_not_called()
        assert result is mock_response

    @patch("tools.jravan_client.requests.get")
    @patch.object(jravan_client, "get_headers", return_value={"x-api-key": "test"})
    def test_異なるURLはキャッシュされない(self, mock_headers, mock_get):
        """異なるURLでは再度APIリクエストが実行される."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_get.return_value = mock_response

        jravan_client.cached_get("https://api.example.com/races/1")
        jravan_client.cached_get("https://api.example.com/races/2")

        assert mock_get.call_count == 2

    @patch("tools.jravan_client.requests.get")
    @patch.object(jravan_client, "get_headers", return_value={"x-api-key": "test"})
    def test_エラーレスポンスはキャッシュされない(self, mock_headers, mock_get):
        """APIエラー時はレスポンスをキャッシュしない."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        jravan_client.cached_get("https://api.example.com/races/1")
        jravan_client.cached_get("https://api.example.com/races/1")

        assert mock_get.call_count == 2

    @patch("tools.jravan_client.requests.get")
    @patch.object(jravan_client, "get_headers", return_value={"x-api-key": "test"})
    def test_パラメータがキャッシュキーに含まれる(self, mock_headers, mock_get):
        """同じURLでもパラメータが違えば別キャッシュ."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_get.return_value = mock_response

        jravan_client.cached_get("https://api.example.com/races", params={"id": "1"})
        jravan_client.cached_get("https://api.example.com/races", params={"id": "2"})

        assert mock_get.call_count == 2

    @patch("tools.jravan_client.requests.get")
    @patch.object(jravan_client, "get_headers", return_value={"x-api-key": "test"})
    def test_ヘッダーが正しく付与される(self, mock_headers, mock_get):
        """cached_getがget_headersのヘッダーを使用する."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_get.return_value = mock_response

        jravan_client.cached_get("https://api.example.com/races/1")

        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["headers"] == {"x-api-key": "test"}
