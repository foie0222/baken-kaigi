"""スピード指数データ取得ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.speed_index import get_speed_index, list_speed_indices_for_date, _analyze_consensus


@pytest.fixture
def mock_dynamodb_table():
    """DynamoDBテーブルのモック."""
    with patch("tools.speed_index.get_dynamodb_table") as mock:
        table = MagicMock()
        mock.return_value = table
        yield table


def _make_indices(horse_numbers_scores):
    """テスト用のスピード指数データを生成するヘルパー.

    Args:
        horse_numbers_scores: [(horse_number, score), ...] スコア降順を想定
    """
    return [
        {"rank": i + 1, "speed_index": score, "horse_number": hn, "horse_name": f"馬{hn}号"}
        for i, (hn, score) in enumerate(horse_numbers_scores)
    ]


def _make_source_item(race_id, source, horse_numbers_scores, venue="東京", race_number=11):
    """テスト用のDynamoDBアイテムを生成するヘルパー."""
    return {
        "race_id": race_id,
        "source": source,
        "venue": venue,
        "race_number": race_number,
        "indices": _make_indices(horse_numbers_scores),
        "scraped_at": "2026-02-08T06:00:00+09:00",
    }


class TestGetSpeedIndex:
    """get_speed_index ツールのテスト."""

    def test_正常なデータ取得_単一ソース(self, mock_dynamodb_table):
        """正常系: DynamoDBからデータを取得できる."""
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "race_id": "202602080511",
                "source": "jiro8-speed",
                "venue": "東京",
                "race_number": 11,
                "indices": [
                    {"rank": 1, "speed_index": 90.2, "horse_number": 5, "horse_name": "馬A"},
                    {"rank": 2, "speed_index": 85.5, "horse_number": 3, "horse_name": "馬B"},
                ],
                "scraped_at": "2026-02-08T06:00:00+09:00",
                "ttl": 1739000000,
            }
        }

        result = get_speed_index(race_id="202602080511", source="jiro8-speed")

        assert result["race_id"] == "202602080511"
        assert result["source"] == "jiro8-speed"
        assert result["venue"] == "東京"
        assert result["race_number"] == 11
        assert len(result["indices"]) == 2
        assert result["indices"][0]["rank"] == 1
        assert result["indices"][0]["speed_index"] == 90.2
        assert "ttl" not in result
        assert "error" not in result

    def test_データが見つからない場合(self, mock_dynamodb_table):
        """異常系: データが存在しない場合はエラーメッセージを返す."""
        mock_dynamodb_table.get_item.return_value = {}

        result = get_speed_index(race_id="202602080599", source="jiro8-speed")

        assert result["race_id"] == "202602080599"
        assert result["source"] == "jiro8-speed"
        assert "error" in result
        assert "スピード指数データが見つかりません" in result["error"]
        assert result["indices"] == []

    def test_DynamoDBエラー時(self, mock_dynamodb_table):
        """異常系: DynamoDBでエラーが発生した場合."""
        from botocore.exceptions import ClientError
        mock_dynamodb_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
            "GetItem"
        )

        result = get_speed_index(race_id="202602080511", source="jiro8-speed")

        assert "error" in result
        assert "DynamoDBエラー" in result["error"]
        assert result["indices"] == []


class TestGetSpeedIndexMultiSource:
    """get_speed_index マルチソース取得のテスト."""

    def test_全ソース取得_2ソースある場合(self, mock_dynamodb_table):
        """source=None で呼ぶと全ソースを取得しコンセンサスを付加する."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                _make_source_item("202602080511", "jiro8-speed", [(5, 90.2), (3, 85.5), (8, 80.0), (1, 75.0)]),
                _make_source_item("202602080511", "kichiuma-speed", [(5, 92.0), (3, 88.0), (8, 82.0), (1, 70.0)]),
            ]
        }

        result = get_speed_index(race_id="202602080511", source=None)

        assert result["race_id"] == "202602080511"
        assert len(result["sources"]) == 2
        assert "consensus" in result
        assert "error" not in result
        mock_dynamodb_table.query.assert_called_once()

    def test_全ソース取得_1ソースのみの場合(self, mock_dynamodb_table):
        """1ソースのみの場合、sourcesに1つ。consensusは付加しない."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                _make_source_item("202602080511", "jiro8-speed", [(5, 90.2), (3, 85.5), (8, 80.0)]),
            ]
        }

        result = get_speed_index(race_id="202602080511", source=None)

        assert result["race_id"] == "202602080511"
        assert len(result["sources"]) == 1
        assert "consensus" not in result
        assert "error" not in result

    def test_source指定時は従来通り単一ソース返却(self, mock_dynamodb_table):
        """source指定の場合、従来と同じ形式で返す（後方互換）."""
        mock_dynamodb_table.get_item.return_value = {
            "Item": _make_source_item("202602080511", "jiro8-speed", [(5, 90.2), (3, 85.5)])
        }

        result = get_speed_index(race_id="202602080511", source="jiro8-speed")

        assert result["race_id"] == "202602080511"
        assert result["source"] == "jiro8-speed"
        assert "indices" in result
        assert "sources" not in result
        assert "consensus" not in result
        mock_dynamodb_table.get_item.assert_called_once()

    def test_データなしの場合(self, mock_dynamodb_table):
        """全ソース取得でデータがない場合."""
        mock_dynamodb_table.query.return_value = {"Items": []}

        result = get_speed_index(race_id="202602080599", source=None)

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

        result = get_speed_index(race_id="202602080511", source=None)

        assert "error" in result
        assert "DynamoDBエラー" in result["error"]
        assert result["sources"] == []

    def test_デフォルト引数はsourceなし(self, mock_dynamodb_table):
        """引数なしで呼んだ場合、source=None として全ソース取得になる."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                _make_source_item("202602080511", "jiro8-speed", [(5, 90.2), (3, 85.5), (8, 80.0)]),
            ]
        }

        result = get_speed_index(race_id="202602080511")

        mock_dynamodb_table.query.assert_called_once()
        assert "sources" in result


class TestAnalyzeConsensus:
    """コンセンサス分析のテスト."""

    def test_コンセンサス_完全合意(self):
        """top3の馬番・順位が完全一致."""
        sources = [
            {"source": "jiro8-speed", "indices": _make_indices([(5, 90), (3, 85), (8, 80), (1, 75)])},
            {"source": "kichiuma-speed", "indices": _make_indices([(5, 92), (3, 88), (8, 82), (1, 70)])},
        ]

        result = _analyze_consensus(sources)

        assert result["consensus_level"] == "完全合意"
        assert set(result["agreed_top3"]) == {5, 3, 8}

    def test_コンセンサス_概ね合意(self):
        """top3の顔ぶれは一致するが順位が異なる."""
        sources = [
            {"source": "jiro8-speed", "indices": _make_indices([(5, 90), (3, 85), (8, 80), (1, 75)])},
            {"source": "kichiuma-speed", "indices": _make_indices([(3, 92), (8, 88), (5, 82), (1, 70)])},
        ]

        result = _analyze_consensus(sources)

        assert result["consensus_level"] == "概ね合意"
        assert set(result["agreed_top3"]) == {5, 3, 8}

    def test_コンセンサス_部分合意(self):
        """top3中2頭が一致."""
        sources = [
            {"source": "jiro8-speed", "indices": _make_indices([(5, 90), (3, 85), (8, 80), (1, 75)])},
            {"source": "kichiuma-speed", "indices": _make_indices([(5, 92), (3, 88), (1, 82), (8, 70)])},
        ]

        result = _analyze_consensus(sources)

        assert result["consensus_level"] == "部分合意"
        assert set(result["agreed_top3"]) == {5, 3}

    def test_コンセンサス_大きな乖離(self):
        """top3中1頭以下が一致."""
        sources = [
            {"source": "jiro8-speed", "indices": _make_indices([(5, 90), (3, 85), (8, 80), (1, 75)])},
            {"source": "kichiuma-speed", "indices": _make_indices([(1, 92), (2, 88), (4, 82), (5, 70)])},
        ]

        result = _analyze_consensus(sources)

        assert result["consensus_level"] == "大きな乖離"
        assert len(result["agreed_top3"]) <= 1

    def test_乖離馬の検出(self):
        """ソース間で順位差が3以上の馬がdivergence_horsesに含まれる."""
        sources = [
            {"source": "jiro8-speed", "indices": _make_indices([(5, 90), (3, 85), (8, 80), (1, 75)])},
            {"source": "kichiuma-speed", "indices": _make_indices([(1, 92), (3, 88), (5, 82), (8, 70)])},
        ]
        # 馬5: jiro8=1位, kichiuma=3位 -> gap=2
        # 馬1: jiro8=4位, kichiuma=1位 -> gap=3

        result = _analyze_consensus(sources)

        divergence_numbers = [h["horse_number"] for h in result["divergence_horses"]]
        assert 1 in divergence_numbers  # gap=3
        assert 3 not in divergence_numbers  # gap=0

    def test_乖離馬のランク情報(self):
        """乖離馬にはソースごとの順位とgapが含まれる."""
        sources = [
            {"source": "jiro8-speed", "indices": _make_indices([(5, 90), (3, 85), (8, 80), (1, 75)])},
            {"source": "kichiuma-speed", "indices": _make_indices([(1, 92), (8, 88), (3, 82), (5, 70)])},
        ]
        # 馬5: jiro8=1位, kichiuma=4位 -> gap=3
        # 馬1: jiro8=4位, kichiuma=1位 -> gap=3

        result = _analyze_consensus(sources)

        divergence_map = {h["horse_number"]: h for h in result["divergence_horses"]}
        assert 5 in divergence_map
        assert divergence_map[5]["ranks"]["jiro8-speed"] == 1
        assert divergence_map[5]["ranks"]["kichiuma-speed"] == 4
        assert divergence_map[5]["gap"] == 3


class TestListSpeedIndicesForDate:
    """list_speed_indices_for_date ツールのテスト."""

    def test_日付でデータ一覧取得(self, mock_dynamodb_table):
        """正常系: 指定日のデータ一覧を取得できる."""
        mock_dynamodb_table.scan.return_value = {
            "Items": [
                {
                    "race_id": "202602080511",
                    "source": "jiro8-speed",
                    "venue": "東京",
                    "race_number": 11,
                    "indices": [
                        {"rank": 1, "speed_index": 90.2, "horse_number": 5, "horse_name": "馬A"},
                        {"rank": 2, "speed_index": 85.5, "horse_number": 3, "horse_name": "馬B"},
                    ],
                    "scraped_at": "2026-02-08T06:00:00+09:00",
                },
                {
                    "race_id": "202602080812",
                    "source": "jiro8-speed",
                    "venue": "京都",
                    "race_number": 12,
                    "indices": [
                        {"rank": 1, "speed_index": 95.0, "horse_number": 1, "horse_name": "馬X"},
                    ],
                    "scraped_at": "2026-02-08T06:00:00+09:00",
                },
            ]
        }

        result = list_speed_indices_for_date(date="20260208")

        assert result["date"] == "20260208"
        assert result["source"] == "jiro8-speed"
        assert result["total_count"] == 2
        assert len(result["races"]) == 2

        # top_indicesは上位3頭のみ
        tokyo_race = next(r for r in result["races"] if r["venue"] == "東京")
        assert len(tokyo_race["top_indices"]) == 2  # データが2つなので2つ

        kyoto_race = next(r for r in result["races"] if r["venue"] == "京都")
        assert len(kyoto_race["top_indices"]) == 1

    def test_データがない場合(self, mock_dynamodb_table):
        """正常系: 指定日のデータがない場合."""
        mock_dynamodb_table.scan.return_value = {"Items": []}

        result = list_speed_indices_for_date(date="20260201")

        assert result["date"] == "20260201"
        assert result["total_count"] == 0
        assert result["races"] == []
        assert "error" not in result

    def test_レースがソートされる(self, mock_dynamodb_table):
        """正常系: レースが競馬場名・レース番号でソートされる."""
        mock_dynamodb_table.scan.return_value = {
            "Items": [
                {"race_id": "202602080512", "source": "jiro8-speed", "venue": "東京", "race_number": 12, "indices": []},
                {"race_id": "202602080811", "source": "jiro8-speed", "venue": "京都", "race_number": 11, "indices": []},
                {"race_id": "202602080511", "source": "jiro8-speed", "venue": "東京", "race_number": 11, "indices": []},
            ]
        }

        result = list_speed_indices_for_date(date="20260208")

        # 京都が先、その後東京
        assert result["races"][0]["venue"] == "京都"
        assert result["races"][1]["venue"] == "東京"
        assert result["races"][1]["race_number"] == 11
        assert result["races"][2]["venue"] == "東京"
        assert result["races"][2]["race_number"] == 12
