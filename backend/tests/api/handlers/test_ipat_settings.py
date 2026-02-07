"""IPAT設定APIハンドラーのテスト."""
import json

from src.api.dependencies import Dependencies
from src.api.handlers.ipat_settings import (
    delete_ipat_credentials_handler,
    get_ipat_status_handler,
    save_ipat_credentials_handler,
)
from src.domain.identifiers import UserId
from src.domain.value_objects import IpatCredentials
from src.infrastructure.providers.in_memory_credentials_provider import InMemoryCredentialsProvider


def _auth_event(user_id: str = "user-001", body: dict | None = None) -> dict:
    event = {
        "requestContext": {
            "authorizer": {
                "claims": {"sub": user_id}
            }
        },
    }
    if body is not None:
        event["body"] = json.dumps(body)
    return event


def _setup_deps():
    Dependencies.reset()
    cred_provider = InMemoryCredentialsProvider()
    Dependencies.set_credentials_provider(cred_provider)
    return cred_provider


class TestSaveIpatCredentialsHandler:
    """save_ipat_credentials_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {"body": json.dumps({})}
        result = save_ipat_credentials_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常保存(self) -> None:
        cred_provider = _setup_deps()
        event = _auth_event(body={
            "card_number": "123456789012",
            "birthday": "19900101",
            "pin": "1234",
            "dummy_pin": "5678",
        })
        result = save_ipat_credentials_handler(event, None)
        assert result["statusCode"] == 200
        assert cred_provider.has_credentials(UserId("user-001"))

    def test_必須パラメータ不足で400(self) -> None:
        _setup_deps()
        event = _auth_event(body={"card_number": "123456789012"})
        result = save_ipat_credentials_handler(event, None)
        assert result["statusCode"] == 400

    def test_バリデーションエラーで400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "card_number": "invalid",
            "birthday": "19900101",
            "pin": "1234",
            "dummy_pin": "5678",
        })
        result = save_ipat_credentials_handler(event, None)
        assert result["statusCode"] == 400


class TestGetIpatStatusHandler:
    """get_ipat_status_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {}
        result = get_ipat_status_handler(event, None)
        assert result["statusCode"] == 401

    def test_設定済み(self) -> None:
        cred_provider = _setup_deps()
        cred_provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                card_number="123456789012",
                birthday="19900101",
                pin="1234",
                dummy_pin="5678",
            ),
        )
        event = _auth_event()
        result = get_ipat_status_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["configured"] is True

    def test_未設定(self) -> None:
        _setup_deps()
        event = _auth_event()
        result = get_ipat_status_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["configured"] is False


class TestDeleteIpatCredentialsHandler:
    """delete_ipat_credentials_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {}
        result = delete_ipat_credentials_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常削除(self) -> None:
        cred_provider = _setup_deps()
        cred_provider.save_credentials(
            UserId("user-001"),
            IpatCredentials(
                card_number="123456789012",
                birthday="19900101",
                pin="1234",
                dummy_pin="5678",
            ),
        )
        event = _auth_event()
        result = delete_ipat_credentials_handler(event, None)
        assert result["statusCode"] == 200
        assert not cred_provider.has_credentials(UserId("user-001"))
