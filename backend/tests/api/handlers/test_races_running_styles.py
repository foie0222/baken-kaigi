"""脚質データAPI ハンドラーテスト."""
from unittest.mock import MagicMock

import pytest

from src.api.handlers.races import get_running_styles
from src.domain.ports import RunningStyleData


@pytest.fixture
def mock_provider(monkeypatch):
    """モックプロバイダーをセットアップする."""
    mock = MagicMock()
    monkeypatch.setattr(
        "src.api.handlers.races.Dependencies.get_race_data_provider",
        lambda: mock,
    )
    return mock


class TestGetRunningStyles:
    """get_running_styles ハンドラーのテスト."""

    def test_race_idがない場合は400を返す(self, mock_provider):
        """race_idがない場合は400エラーを返す."""
        event = {"pathParameters": {}}
        result = get_running_styles(event, None)
        assert result["statusCode"] == 400

    def test_空リストを返す(self, mock_provider):
        """脚質データがない場合は空リストを返す."""
        mock_provider.get_running_styles.return_value = []
        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_running_styles(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert body == []

    def test_正常な脚質データを返す(self, mock_provider):
        """正常な脚質データを返す."""
        mock_provider.get_running_styles.return_value = [
            RunningStyleData(
                horse_number=1,
                horse_name="テスト馬A",
                running_style="逃げ",
                running_style_tendency="逃げ",
            ),
            RunningStyleData(
                horse_number=2,
                horse_name="テスト馬B",
                running_style="差し",
                running_style_tendency="先行",
            ),
        ]

        event = {"pathParameters": {"race_id": "202401010101"}}
        result = get_running_styles(event, None)

        assert result["statusCode"] == 200
        import json

        body = json.loads(result["body"])
        assert len(body) == 2
        assert body[0]["horse_number"] == 1
        assert body[0]["horse_name"] == "テスト馬A"
        assert body[0]["running_style"] == "逃げ"
        assert body[0]["running_style_tendency"] == "逃げ"
        assert body[1]["horse_number"] == 2
        assert body[1]["running_style"] == "差し"
        assert body[1]["running_style_tendency"] == "先行"
