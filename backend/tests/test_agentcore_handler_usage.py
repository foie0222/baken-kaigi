"""agentcore_handler の利用制限テスト."""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """テスト用の環境変数を設定."""
    monkeypatch.setenv("AGENTCORE_AGENT_ARN", "arn:aws:bedrock-agentcore:ap-northeast-1:123456789012:runtime/test-agent")
    monkeypatch.setenv("USAGE_TRACKING_TABLE_NAME", "baken-kaigi-usage-tracking")
    monkeypatch.setenv("AWS_REGION", "ap-northeast-1")
    # モジュールレベル変数も直接パッチ（全テスト実行時にモジュールが先にインポートされるため）
    import agentcore_handler
    monkeypatch.setattr(agentcore_handler, "AGENTCORE_AGENT_ARN", "arn:aws:bedrock-agentcore:ap-northeast-1:123456789012:runtime/test-agent")
    monkeypatch.setattr(agentcore_handler, "USAGE_TRACKING_TABLE_NAME", "baken-kaigi-usage-tracking")
    # グローバルDynamoDBリソースをリセット（テスト間の分離）
    monkeypatch.setattr(agentcore_handler, "_dynamodb_resource", None)


def _make_jwt(sub: str, tier: str = "free") -> str:
    """テスト用JWTトークンを生成."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).rstrip(b"=").decode()
    payload_data = {"sub": sub}
    if tier:
        payload_data["custom:tier"] = tier
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
    signature = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=").decode()
    return f"{header}.{payload}.{signature}"


def _make_event(body: dict, headers: dict | None = None) -> dict:
    """API Gateway イベントを構築."""
    return {
        "body": json.dumps(body),
        "headers": headers or {},
    }


def _make_bet_proposal_body(race_id: str = "202502011201", session_id: str | None = None) -> dict:
    """買い目提案リクエストボディを構築."""
    body = {
        "prompt": f"レースID {race_id} について、予算3000円でgenerate_bet_proposalツールを使って買い目提案を生成してください。",
        "cart_items": [],
    }
    if session_id:
        body["session_id"] = session_id
    return body


class TestIdentifyUser:
    """_identify_user 関数のテスト."""

    def test_JWTからユーザーを特定できる(self):
        from agentcore_handler import _identify_user

        jwt = _make_jwt("user-123", "free")
        event = {"headers": {"Authorization": f"Bearer {jwt}"}}
        user_key, tier = _identify_user(event)

        assert user_key == "user:user-123"
        assert tier == "free"

    def test_premiumティアを正しく判定できる(self):
        from agentcore_handler import _identify_user

        jwt = _make_jwt("user-premium", "premium")
        event = {"headers": {"Authorization": f"Bearer {jwt}"}}
        user_key, tier = _identify_user(event)

        assert user_key == "user:user-premium"
        assert tier == "premium"

    def test_UUID形式のGuestIdからゲストを特定できる(self):
        from agentcore_handler import _identify_user

        event = {"headers": {"X-Guest-Id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}}
        user_key, tier = _identify_user(event)

        assert user_key == "guest:a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert tier == "anonymous"

    def test_不正な形式のGuestIdは拒否される(self):
        from agentcore_handler import _identify_user

        event = {"headers": {"X-Guest-Id": "malicious-string-<script>alert(1)</script>"}}
        user_key, tier = _identify_user(event)

        # 不正な形式は匿名扱い（guest:unknown）
        assert user_key == "guest:unknown"
        assert tier == "anonymous"

    def test_ヘッダーなしは匿名扱い(self):
        from agentcore_handler import _identify_user

        event = {"headers": {}}
        user_key, tier = _identify_user(event)

        assert user_key == "guest:unknown"
        assert tier == "anonymous"


class TestExtractRaceIds:
    """_extract_race_ids 関数のテスト."""

    def test_プロンプトからレースIDを抽出できる(self):
        from agentcore_handler import _extract_race_ids

        body = {"prompt": "レースID 202502011201 について、予算3000円で提案してください。"}
        result = _extract_race_ids(body)

        assert result == {"202502011201"}

    def test_カートアイテムからレースIDを抽出できる(self):
        from agentcore_handler import _extract_race_ids

        body = {
            "prompt": "分析してください",
            "cart_items": [
                {"raceId": "202502011201", "raceName": "test"},
                {"raceId": "202502011202", "raceName": "test2"},
            ],
        }
        result = _extract_race_ids(body)

        assert result == {"202502011201", "202502011202"}


class TestCheckAndRecordUsage:
    """_check_and_record_usage 関数のテスト."""

    @patch("agentcore_handler.boto3")
    def test_初回リクエストは成功する(self, mock_boto3):
        from agentcore_handler import _check_and_record_usage

        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # 既存レコードなし
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = _check_and_record_usage("guest:abc", "anonymous", {"race1"}, "2026-02-13")

        assert result is None  # 制限なし
        mock_table.put_item.assert_called_once()

    @patch("agentcore_handler.boto3")
    def test_ゲストが2レース目で制限超過(self, mock_boto3):
        from agentcore_handler import _check_and_record_usage

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"consulted_race_ids": {"race1"}}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = _check_and_record_usage("guest:abc", "anonymous", {"race2"}, "2026-02-13")

        assert result is not None
        assert result["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert result["usage"]["max_races"] == 1
        assert result["usage"]["remaining_races"] == 0

    @patch("agentcore_handler.boto3")
    def test_同一レースは制限にカウントしない(self, mock_boto3):
        from agentcore_handler import _check_and_record_usage

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"consulted_race_ids": {"race1"}}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = _check_and_record_usage("guest:abc", "anonymous", {"race1"}, "2026-02-13")

        assert result is None  # 同一レースなので制限なし

    @patch("agentcore_handler.boto3")
    def test_無料会員が3レースまで成功(self, mock_boto3):
        from agentcore_handler import _check_and_record_usage

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"consulted_race_ids": {"race1", "race2"}}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = _check_and_record_usage("user:u1", "free", {"race3"}, "2026-02-13")

        assert result is None  # 3レース目はOK

    @patch("agentcore_handler.boto3")
    def test_無料会員が4レース目で制限超過(self, mock_boto3):
        from agentcore_handler import _check_and_record_usage

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"consulted_race_ids": {"race1", "race2", "race3"}}
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = _check_and_record_usage("user:u1", "free", {"race4"}, "2026-02-13")

        assert result is not None
        assert result["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert result["usage"]["max_races"] == 3

    @patch("agentcore_handler.boto3")
    def test_有料会員は常に成功(self, mock_boto3):
        from agentcore_handler import _check_and_record_usage

        result = _check_and_record_usage("user:premium", "premium", {"race1"}, "2026-02-13")

        assert result is None  # premium は無制限

    def test_テーブル未設定時はスキップ(self, monkeypatch):
        import agentcore_handler
        monkeypatch.setattr(agentcore_handler, "USAGE_TRACKING_TABLE_NAME", "")

        result = agentcore_handler._check_and_record_usage("guest:abc", "anonymous", {"race1"}, "2026-02-13")
        assert result is None


class TestInvokeAgentcoreUsageLimit:
    """invoke_agentcore の利用制限統合テスト."""

    @patch("agentcore_handler._make_usage_info", return_value=None)
    @patch("agentcore_handler._check_and_record_usage", return_value=None)
    @patch("agentcore_handler.boto3")
    def test_ゲストが1レース目を予想_成功とusage返却(self, mock_boto3, mock_check, mock_usage_info):
        from agentcore_handler import invoke_agentcore

        # AgentCoreレスポンスをモック
        mock_response_body = MagicMock()
        mock_response_body.read.return_value = json.dumps({
            "message": "提案です",
            "session_id": "session-1",
        }).encode("utf-8")
        mock_response_body.close = MagicMock()

        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {
            "contentType": "application/json",
            "response": mock_response_body,
        }
        mock_boto3.client.return_value = mock_client

        # usage_info を返すように設定
        mock_usage_info.return_value = {
            "consulted_races": 1,
            "max_races": 1,
            "remaining_races": 0,
            "tier": "anonymous",
        }

        event = _make_event(
            _make_bet_proposal_body("202502011201"),
            headers={"X-Guest-Id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
        )

        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["message"] == "提案です"
        assert body["usage"]["tier"] == "anonymous"

    @patch("agentcore_handler._make_usage_info", return_value=None)
    @patch("agentcore_handler._check_and_record_usage")
    @patch("agentcore_handler.boto3")
    def test_ゲストが2レース目を予想_429エラー(self, mock_boto3, mock_check, mock_usage_info):
        from agentcore_handler import invoke_agentcore

        mock_check.return_value = {
            "error": {"message": "本日の予想枠を使い切りました", "code": "RATE_LIMIT_EXCEEDED"},
            "usage": {"consulted_races": 1, "max_races": 1, "remaining_races": 0, "tier": "anonymous"},
        }

        event = _make_event(
            _make_bet_proposal_body("202502011202"),
            headers={"X-Guest-Id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
        )

        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 429
        body = json.loads(result["body"])
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert body["usage"]["remaining_races"] == 0

    @patch("agentcore_handler._make_usage_info", return_value=None)
    @patch("agentcore_handler._check_and_record_usage")
    @patch("agentcore_handler.boto3")
    def test_session_id付きリクエストは制限チェックスキップ(self, mock_boto3, mock_check, mock_usage_info):
        from agentcore_handler import invoke_agentcore

        # AgentCoreレスポンスをモック
        mock_response_body = MagicMock()
        mock_response_body.read.return_value = json.dumps({
            "message": "続きの分析",
            "session_id": "existing-session",
        }).encode("utf-8")
        mock_response_body.close = MagicMock()

        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {
            "contentType": "application/json",
            "response": mock_response_body,
        }
        mock_boto3.client.return_value = mock_client

        event = _make_event(
            _make_bet_proposal_body("202502011202", session_id="existing-session"),
            headers={"X-Guest-Id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
        )

        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 200
        # _check_and_record_usage は呼ばれないことを確認
        mock_check.assert_not_called()

    @patch("agentcore_handler._make_usage_info", return_value=None)
    @patch("agentcore_handler._check_and_record_usage", return_value=None)
    @patch("agentcore_handler.boto3")
    def test_有料会員は常に成功(self, mock_boto3, mock_check, mock_usage_info):
        from agentcore_handler import invoke_agentcore

        jwt = _make_jwt("user-premium", "premium")

        # AgentCoreレスポンスをモック
        mock_response_body = MagicMock()
        mock_response_body.read.return_value = json.dumps({
            "message": "premium分析",
            "session_id": "s1",
        }).encode("utf-8")
        mock_response_body.close = MagicMock()

        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {
            "contentType": "application/json",
            "response": mock_response_body,
        }
        mock_boto3.client.return_value = mock_client

        event = _make_event(
            _make_bet_proposal_body("202502011201"),
            headers={"Authorization": f"Bearer {jwt}"},
        )

        result = invoke_agentcore(event, None)

        assert result["statusCode"] == 200
