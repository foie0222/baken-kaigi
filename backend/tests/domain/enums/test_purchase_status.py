"""PurchaseStatusのテスト."""
import pytest

from src.domain.enums import PurchaseStatus


class TestPurchaseStatus:
    """PurchaseStatusの単体テスト."""

    def test_PENDINGの表示名(self) -> None:
        """PENDINGの日本語表示名が「投票準備中」であることを確認."""
        assert PurchaseStatus.PENDING.get_display_name() == "投票準備中"

    def test_SUBMITTEDの表示名(self) -> None:
        """SUBMITTEDの日本語表示名が「投票送信済」であることを確認."""
        assert PurchaseStatus.SUBMITTED.get_display_name() == "投票送信済"

    def test_COMPLETEDの表示名(self) -> None:
        """COMPLETEDの日本語表示名が「投票完了」であることを確認."""
        assert PurchaseStatus.COMPLETED.get_display_name() == "投票完了"

    def test_FAILEDの表示名(self) -> None:
        """FAILEDの日本語表示名が「投票失敗」であることを確認."""
        assert PurchaseStatus.FAILED.get_display_name() == "投票失敗"

    def test_全ステータスの値が一意(self) -> None:
        """全ステータスのvalue値が一意であることを確認."""
        values = [s.value for s in PurchaseStatus]
        assert len(values) == len(set(values))

    def test_ステータスは4種類(self) -> None:
        """ステータスが4種類であることを確認."""
        assert len(PurchaseStatus) == 4
