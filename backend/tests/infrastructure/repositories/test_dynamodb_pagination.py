"""DynamoDBリポジトリのページネーションテスト."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.domain.enums import LossLimitChangeStatus, LossLimitChangeType, PurchaseStatus
from src.infrastructure.repositories.dynamodb_loss_limit_change_repository import (
    DynamoDBLossLimitChangeRepository,
)
from src.infrastructure.repositories.dynamodb_purchase_order_repository import (
    DynamoDBPurchaseOrderRepository,
)


def _make_purchase_order_item(purchase_id: str, user_id: str = "usr_001") -> dict:
    """テスト用DynamoDBアイテムを生成する."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "purchase_id": purchase_id,
        "user_id": user_id,
        "cart_id": "cart_001",
        "status": PurchaseStatus.COMPLETED.value,
        "total_amount": 1000,
        "created_at": now,
        "updated_at": now,
        "bet_lines": [
            {
                "opdt": "20260201",
                "venue_code": "05",
                "race_number": 1,
                "bet_type": "tansyo",
                "number": "01",
                "amount": 1000,
            }
        ],
    }


def _make_loss_limit_change_item(change_id: str, user_id: str = "usr_001", status: str = "pending") -> dict:
    """テスト用DynamoDBアイテムを生成する."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "change_id": change_id,
        "user_id": user_id,
        "current_limit": 50000,
        "requested_limit": 100000,
        "change_type": LossLimitChangeType.INCREASE.value,
        "status": status,
        "effective_at": now,
        "requested_at": now,
    }


class TestPurchaseOrderPagination:
    """DynamoDBPurchaseOrderRepositoryのページネーションテスト."""

    @patch.object(DynamoDBPurchaseOrderRepository, "__init__", lambda self: None)
    def test_find_by_user_idは複数ページを結合する(self):
        repo = DynamoDBPurchaseOrderRepository()
        mock_table = MagicMock()
        repo._table = mock_table

        page1_items = [_make_purchase_order_item(f"pur_{i:03d}") for i in range(3)]
        page2_items = [_make_purchase_order_item(f"pur_{i:03d}") for i in range(3, 5)]

        mock_table.query.side_effect = [
            {"Items": page1_items, "LastEvaluatedKey": {"purchase_id": "pur_002"}},
            {"Items": page2_items},
        ]

        from src.domain.identifiers import UserId
        results = repo.find_by_user_id(UserId("usr_001"))
        assert len(results) == 5
        assert mock_table.query.call_count == 2


class TestLossLimitChangePagination:
    """DynamoDBLossLimitChangeRepositoryのページネーションテスト."""

    @patch.object(DynamoDBLossLimitChangeRepository, "__init__", lambda self: None)
    def test_find_by_user_idは複数ページを結合する(self):
        repo = DynamoDBLossLimitChangeRepository()
        mock_table = MagicMock()
        repo._table = mock_table

        page1_items = [_make_loss_limit_change_item(f"chg_{i:03d}") for i in range(3)]
        page2_items = [_make_loss_limit_change_item(f"chg_{i:03d}") for i in range(3, 5)]

        mock_table.query.side_effect = [
            {"Items": page1_items, "LastEvaluatedKey": {"change_id": "chg_002"}},
            {"Items": page2_items},
        ]

        from src.domain.identifiers import UserId
        results = repo.find_by_user_id(UserId("usr_001"))
        assert len(results) == 5
        assert mock_table.query.call_count == 2

    @patch.object(DynamoDBLossLimitChangeRepository, "__init__", lambda self: None)
    def test_find_pending_by_user_idは複数ページを結合する(self):
        repo = DynamoDBLossLimitChangeRepository()
        mock_table = MagicMock()
        repo._table = mock_table

        page1_items = [_make_loss_limit_change_item(f"chg_{i:03d}", status="pending") for i in range(2)]
        page2_items = [_make_loss_limit_change_item(f"chg_{i:03d}", status="pending") for i in range(2, 4)]

        mock_table.query.side_effect = [
            {"Items": page1_items, "LastEvaluatedKey": {"change_id": "chg_001"}},
            {"Items": page2_items},
        ]

        from src.domain.identifiers import UserId
        results = repo.find_pending_by_user_id(UserId("usr_001"))
        assert len(results) == 4
        assert mock_table.query.call_count == 2
