"""InMemoryCredentialsProvider のテスト."""
import unittest

from src.domain.identifiers import UserId
from src.domain.value_objects import IpatCredentials
from src.infrastructure.providers.in_memory_credentials_provider import (
    InMemoryCredentialsProvider,
)


class TestInMemoryCredentialsProvider(unittest.TestCase):
    """InMemoryCredentialsProvider のテスト."""

    def setUp(self) -> None:
        self.provider = InMemoryCredentialsProvider()
        self.user_id = UserId("user-001")
        self.credentials = IpatCredentials(
            card_number="123456789012",
            birthday="19900101",
            pin="1234",
            dummy_pin="5678",
        )

    def test_保存と取得(self) -> None:
        self.provider.save_credentials(self.user_id, self.credentials)
        result = self.provider.get_credentials(self.user_id)
        assert result is not None
        assert result.card_number == "123456789012"

    def test_存在しないユーザーでNone(self) -> None:
        result = self.provider.get_credentials(UserId("not-exist"))
        assert result is None

    def test_認証情報の有無判定_あり(self) -> None:
        self.provider.save_credentials(self.user_id, self.credentials)
        assert self.provider.has_credentials(self.user_id) is True

    def test_認証情報の有無判定_なし(self) -> None:
        assert self.provider.has_credentials(self.user_id) is False

    def test_削除(self) -> None:
        self.provider.save_credentials(self.user_id, self.credentials)
        self.provider.delete_credentials(self.user_id)
        assert self.provider.has_credentials(self.user_id) is False
        assert self.provider.get_credentials(self.user_id) is None

    def test_存在しないユーザーの削除はエラーにならない(self) -> None:
        self.provider.delete_credentials(UserId("not-exist"))

    def test_上書き保存(self) -> None:
        self.provider.save_credentials(self.user_id, self.credentials)
        new_creds = IpatCredentials(
            card_number="999999999999",
            birthday="20000101",
            pin="9999",
            dummy_pin="0000",
        )
        self.provider.save_credentials(self.user_id, new_creds)
        result = self.provider.get_credentials(self.user_id)
        assert result is not None
        assert result.card_number == "999999999999"
