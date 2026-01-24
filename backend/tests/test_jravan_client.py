"""JRA-VAN API クライアント共通モジュールのテスト."""

import sys
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

# agentcore/tools をパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "agentcore" / "tools"))
from jravan_client import (
    get_api_key,
    get_headers,
    get_api_url,
    JRAVAN_API_URL,
    JRAVAN_API_KEY_ID,
)
import jravan_client


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
