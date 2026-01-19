"""Messageのテスト."""
import pytest

from src.domain.entities import Message
from src.domain.enums import MessageType


class TestMessage:
    """Messageの単体テスト."""

    def test_create_user_messageでユーザーメッセージを生成(self) -> None:
        """create_user_messageでUSER種別のメッセージを生成できることを確認."""
        msg = Message.create_user_message("質問です")
        assert msg.type == MessageType.USER
        assert msg.content == "質問です"

    def test_create_ai_messageでAIメッセージを生成(self) -> None:
        """create_ai_messageでAI種別のメッセージを生成できることを確認."""
        msg = Message.create_ai_message("回答です")
        assert msg.type == MessageType.AI
        assert msg.content == "回答です"

    def test_create_system_messageでシステムメッセージを生成(self) -> None:
        """create_system_messageでSYSTEM種別のメッセージを生成できることを確認."""
        msg = Message.create_system_message("通知です")
        assert msg.type == MessageType.SYSTEM
        assert msg.content == "通知です"

    def test_message_idが自動生成される(self) -> None:
        """メッセージ作成時にmessage_idが自動生成されることを確認."""
        msg = Message.create_user_message("テスト")
        assert msg.message_id is not None
        assert len(msg.message_id.value) == 36

    def test_空の内容でエラー(self) -> None:
        """空の内容を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Message.create_user_message("")

    def test_is_from_userでユーザーメッセージはTrue(self) -> None:
        """is_from_userでユーザーメッセージに対してTrueが返ることを確認."""
        msg = Message.create_user_message("テスト")
        assert msg.is_from_user() is True
        assert msg.is_from_ai() is False
        assert msg.is_system() is False

    def test_is_from_aiでAIメッセージはTrue(self) -> None:
        """is_from_aiでAIメッセージに対してTrueが返ることを確認."""
        msg = Message.create_ai_message("テスト")
        assert msg.is_from_user() is False
        assert msg.is_from_ai() is True
        assert msg.is_system() is False

    def test_is_systemでシステムメッセージはTrue(self) -> None:
        """is_systemでシステムメッセージに対してTrueが返ることを確認."""
        msg = Message.create_system_message("テスト")
        assert msg.is_from_user() is False
        assert msg.is_from_ai() is False
        assert msg.is_system() is True

    def test_timestampが自動設定される(self) -> None:
        """メッセージ作成時にtimestampが自動設定されることを確認."""
        msg = Message.create_user_message("テスト")
        assert msg.timestamp is not None

    def test_不変オブジェクトである(self) -> None:
        """Messageは不変（frozen）であることを確認."""
        msg = Message.create_user_message("テスト")
        with pytest.raises(AttributeError):
            msg.content = "変更"  # type: ignore
