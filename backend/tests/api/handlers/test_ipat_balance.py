"""IPAT残高APIハンドラーのテスト."""
import json

from src.api.dependencies import Dependencies
from src.api.handlers.ipat_balance import get_ipat_balance_handler
from src.domain.identifiers import UserId
from src.domain.ports import IpatGatewayError
from src.domain.value_objects import IpatCredentials
from src.infrastructure.providers.in_memory_credentials_provider import InMemoryCredentialsProvider
from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway


def _auth_event(user_id: str = "user-001") -> dict:
    return {
        "requestContext": {
            "authorizer": {
                "claims": {"sub": user_id}
            }
        },
    }


def _setup_deps():
    Dependencies.reset()
    cred_provider = InMemoryCredentialsProvider()
    gateway = MockIpatGateway()
    Dependencies.set_credentials_provider(cred_provider)
    Dependencies.set_ipat_gateway(gateway)
    return cred_provider, gateway


class TestGetIpatBalanceHandler:
    """get_ipat_balance_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {}
        result = get_ipat_balance_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常取得(self) -> None:
        cred_provider, _ = _setup_deps()
        cred_provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            ),
        )
        event = _auth_event()
        result = get_ipat_balance_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["bet_balance"] == 100000

    def test_認証情報なしで400(self) -> None:
        _setup_deps()
        event = _auth_event()
        result = get_ipat_balance_handler(event, None)
        assert result["statusCode"] == 400

    def test_IpatGatewayError発生時に500(self) -> None:
        cred_provider, gateway = _setup_deps()
        cred_provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            ),
        )
        gateway.set_balance_error(IpatGatewayError("IPAT通信エラー"))

        event = _auth_event()
        result = get_ipat_balance_handler(event, None)
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "IPAT通信エラー" in body["error"]["message"]
