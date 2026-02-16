"""馬柱（過去成績）データ取得ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.past_performance import get_past_performance


@pytest.fixture
def mock_dynamodb_table():
    """DynamoDBテーブルのモック."""
    with patch("tools.past_performance.get_dynamodb_table") as mock:
        table = MagicMock()
        mock.return_value = table
        yield table


def _make_horse(horse_number, horse_name, sire="父馬", dam="母馬", dam_sire="母父馬"):
    """テスト用の馬データを生成するヘルパー."""
    return {
        "horse_number": horse_number,
        "horse_name": horse_name,
        "sire": sire,
        "dam": dam,
        "dam_sire": dam_sire,
        "past_races": [
            {
                "date": "20251123",
                "venue": "京都",
                "race_name": "マイルCS",
                "distance": 1600,
                "track": "芝",
                "finish_position": 1,
                "time": "1:32.6",
                "weight": 58.0,
                "jockey": "坂井瑠",
            }
        ],
    }


def _make_source_item(race_id, source, horses, venue="東京", race_number=11):
    """テスト用のDynamoDBアイテムを生成するヘルパー."""
    return {
        "race_id": race_id,
        "source": source,
        "venue": venue,
        "race_number": race_number,
        "horses": horses,
        "scraped_at": "2026-02-08T06:00:00+09:00",
    }


class TestGetPastPerformance:
    """get_past_performance ツールのテスト."""

    def test_正常なデータ取得_単一ソース(self, mock_dynamodb_table):
        """正常系: DynamoDBからデータを取得できる."""
        horses = [
            _make_horse(1, "テスト馬A"),
            _make_horse(5, "テスト馬B"),
        ]
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "race_id": "202602080511",
                "source": "keibagrant",
                "venue": "東京",
                "race_number": 11,
                "horses": horses,
                "scraped_at": "2026-02-08T06:00:00+09:00",
                "ttl": 1739000000,
            }
        }

        result = get_past_performance(race_id="202602080511", source="keibagrant")

        assert result["race_id"] == "202602080511"
        assert result["source"] == "keibagrant"
        assert result["venue"] == "東京"
        assert result["race_number"] == 11
        assert len(result["horses"]) == 2
        assert result["horses"][0]["horse_name"] == "テスト馬A"
        assert result["horses"][0]["sire"] == "父馬"
        assert len(result["horses"][0]["past_races"]) == 1
        assert "error" not in result

    def test_TTLが返されないことを確認(self, mock_dynamodb_table):
        """正常系: TTL属性は返却結果に含まれない."""
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "race_id": "202602080511",
                "source": "keibagrant",
                "venue": "東京",
                "race_number": 11,
                "horses": [],
                "scraped_at": "2026-02-08T06:00:00+09:00",
                "ttl": 1739000000,
            }
        }

        result = get_past_performance(race_id="202602080511", source="keibagrant")

        assert "ttl" not in result

    def test_データが見つからない場合(self, mock_dynamodb_table):
        """異常系: データが存在しない場合はエラーメッセージを返す."""
        mock_dynamodb_table.get_item.return_value = {}

        result = get_past_performance(race_id="202602080599", source="keibagrant")

        assert result["race_id"] == "202602080599"
        assert result["source"] == "keibagrant"
        assert "error" in result
        assert "馬柱データが見つかりません" in result["error"]
        assert result["horses"] == []

    def test_DynamoDBエラー時(self, mock_dynamodb_table):
        """異常系: DynamoDBでエラーが発生した場合."""
        from botocore.exceptions import ClientError
        mock_dynamodb_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
            "GetItem"
        )

        result = get_past_performance(race_id="202602080511", source="keibagrant")

        assert "error" in result
        assert "DynamoDBエラー" in result["error"]
        assert result["horses"] == []

    def test_horsesフィールドが正しく返される(self, mock_dynamodb_table):
        """正常系: horsesに馬番・馬名・血統・近走が含まれる."""
        horse = _make_horse(8, "テスト馬", sire="キングカメハメハ", dam="テスト母", dam_sire="サンデーサイレンス")
        mock_dynamodb_table.get_item.return_value = {
            "Item": _make_source_item("202602080511", "keibagrant", [horse])
        }

        result = get_past_performance(race_id="202602080511", source="keibagrant")

        h = result["horses"][0]
        assert h["horse_number"] == 8
        assert h["horse_name"] == "テスト馬"
        assert h["sire"] == "キングカメハメハ"
        assert h["dam"] == "テスト母"
        assert h["dam_sire"] == "サンデーサイレンス"
        assert h["past_races"][0]["venue"] == "京都"
        assert h["past_races"][0]["distance"] == 1600


class TestGetPastPerformanceMultiSource:
    """get_past_performance マルチソース取得のテスト."""

    def test_全ソース取得(self, mock_dynamodb_table):
        """source=None で呼ぶと全ソースを取得する."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                _make_source_item(
                    "202602080511",
                    "keibagrant",
                    [_make_horse(1, "馬A"), _make_horse(5, "馬B")],
                ),
            ]
        }

        result = get_past_performance(race_id="202602080511", source=None)

        assert result["race_id"] == "202602080511"
        assert len(result["sources"]) == 1
        assert result["sources"][0]["source"] == "keibagrant"
        assert len(result["sources"][0]["horses"]) == 2
        assert "error" not in result
        mock_dynamodb_table.query.assert_called_once()

    def test_全ソース取得_データなし(self, mock_dynamodb_table):
        """全ソース取得でデータがない場合."""
        mock_dynamodb_table.query.return_value = {"Items": []}

        result = get_past_performance(race_id="202602080599", source=None)

        assert result["race_id"] == "202602080599"
        assert "error" in result
        assert result["sources"] == []

    def test_全ソース取得_DynamoDBエラー時(self, mock_dynamodb_table):
        """全ソース取得でDynamoDBエラーが発生した場合."""
        from botocore.exceptions import ClientError
        mock_dynamodb_table.query.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
            "Query"
        )

        result = get_past_performance(race_id="202602080511", source=None)

        assert "error" in result
        assert "DynamoDBエラー" in result["error"]
        assert result["sources"] == []

    def test_source指定時は従来通り単一ソース返却(self, mock_dynamodb_table):
        """source指定の場合、従来と同じ形式で返す."""
        mock_dynamodb_table.get_item.return_value = {
            "Item": _make_source_item("202602080511", "keibagrant", [_make_horse(1, "馬A")])
        }

        result = get_past_performance(race_id="202602080511", source="keibagrant")

        assert result["race_id"] == "202602080511"
        assert result["source"] == "keibagrant"
        assert "horses" in result
        assert "sources" not in result
        mock_dynamodb_table.get_item.assert_called_once()

    def test_デフォルト引数はsourceなし(self, mock_dynamodb_table):
        """引数なしで呼んだ場合、source=None として全ソース取得になる."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                _make_source_item("202602080511", "keibagrant", [_make_horse(1, "馬A")]),
            ]
        }

        result = get_past_performance(race_id="202602080511")

        mock_dynamodb_table.query.assert_called_once()
        assert "sources" in result

    def test_全ソース取得でTTLが除去される(self, mock_dynamodb_table):
        """全ソース取得でもTTL属性は返却結果に含まれない."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                {
                    "race_id": "202602080511",
                    "source": "keibagrant",
                    "venue": "東京",
                    "race_number": 11,
                    "horses": [],
                    "scraped_at": "2026-02-08T06:00:00+09:00",
                    "ttl": 1739000000,
                },
            ]
        }

        result = get_past_performance(race_id="202602080511", source=None)

        # sourcesの各アイテムにttlがないこと
        for s in result["sources"]:
            assert "ttl" not in s
