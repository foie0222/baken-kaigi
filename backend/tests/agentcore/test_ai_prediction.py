"""AI予想データ取得ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# agentcoreモジュールをインポートできるようにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.ai_prediction import (
    get_ai_prediction,
    list_ai_predictions_for_date,
    _analyze_consensus,
    _anonymize_sources,
    _build_source_label_map,
)


@pytest.fixture
def mock_dynamodb_table():
    """DynamoDBテーブルのモック."""
    with patch("tools.ai_prediction.get_dynamodb_table") as mock:
        table = MagicMock()
        mock.return_value = table
        yield table


class TestGetAiPrediction:
    """get_ai_prediction ツールのテスト."""

    def test_正常なデータ取得(self, mock_dynamodb_table):
        """正常系: DynamoDBからデータを取得できる."""
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "race_id": "202601310511",
                "source": "ai-shisu",
                "venue": "東京",
                "race_number": 11,
                "predictions": [
                    {"rank": 1, "score": 691, "horse_number": 8, "horse_name": "ピースワンデュック"},
                    {"rank": 2, "score": 650, "horse_number": 3, "horse_name": "テスト馬"},
                ],
                "scraped_at": "2026-01-31T06:00:00+09:00",
                "ttl": 1738483200,
            }
        }

        result = get_ai_prediction(race_id="202601310511", source="ai-shisu")

        assert result["race_id"] == "202601310511"
        assert result["source"] == "AI-A"  # 匿名化される
        assert result["venue"] == "東京"
        assert result["race_number"] == 11
        assert len(result["predictions"]) == 2
        assert result["predictions"][0]["rank"] == 1
        assert result["predictions"][0]["score"] == 691
        assert "ttl" not in result  # TTLは返さない
        assert "error" not in result

    def test_データが見つからない場合(self, mock_dynamodb_table):
        """異常系: データが存在しない場合はエラーメッセージを返す."""
        mock_dynamodb_table.get_item.return_value = {}

        result = get_ai_prediction(race_id="202601310599", source="ai-shisu")

        assert result["race_id"] == "202601310599"
        assert result["source"] == "AI-A"  # 匿名化される
        assert "error" in result
        assert "AI予想データが見つかりません" in result["error"]
        assert result["predictions"] == []

    def test_DynamoDBエラー時(self, mock_dynamodb_table):
        """異常系: DynamoDBでエラーが発生した場合."""
        from botocore.exceptions import ClientError
        mock_dynamodb_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
            "GetItem"
        )

        result = get_ai_prediction(race_id="202601310511", source="ai-shisu")

        assert "error" in result
        assert "DynamoDBエラー" in result["error"]
        assert result["predictions"] == []

    def test_カスタムソース指定(self, mock_dynamodb_table):
        """正常系: カスタムソースを指定した場合."""
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "race_id": "202601310511",
                "source": "custom-source",
                "venue": "東京",
                "race_number": 11,
                "predictions": [],
                "scraped_at": "2026-01-31T06:00:00+09:00",
            }
        }

        result = get_ai_prediction(race_id="202601310511", source="custom-source")

        mock_dynamodb_table.get_item.assert_called_once_with(
            Key={"race_id": "202601310511", "source": "custom-source"}
        )
        assert result["source"] == "AI-A"  # 匿名化される


class TestListAiPredictionsForDate:
    """list_ai_predictions_for_date ツールのテスト."""

    def test_日付でデータ一覧取得(self, mock_dynamodb_table):
        """正常系: 指定日のデータ一覧を取得できる."""
        mock_dynamodb_table.scan.return_value = {
            "Items": [
                {
                    "race_id": "202601310511",
                    "source": "ai-shisu",
                    "venue": "東京",
                    "race_number": 11,
                    "predictions": [
                        {"rank": 1, "score": 691, "horse_number": 8, "horse_name": "馬A"},
                        {"rank": 2, "score": 650, "horse_number": 3, "horse_name": "馬B"},
                        {"rank": 3, "score": 600, "horse_number": 5, "horse_name": "馬C"},
                        {"rank": 4, "score": 550, "horse_number": 1, "horse_name": "馬D"},
                    ],
                    "scraped_at": "2026-01-31T06:00:00+09:00",
                },
                {
                    "race_id": "202601310812",
                    "source": "ai-shisu",
                    "venue": "京都",
                    "race_number": 12,
                    "predictions": [
                        {"rank": 1, "score": 700, "horse_number": 1, "horse_name": "馬X"},
                    ],
                    "scraped_at": "2026-01-31T06:00:00+09:00",
                },
            ]
        }

        result = list_ai_predictions_for_date(date="20260131")

        assert result["date"] == "20260131"
        assert result["source"] == "AI-A"  # 匿名化される
        assert result["total_count"] == 2
        assert len(result["races"]) == 2

        # top_predictionsは上位3頭のみ
        tokyo_race = next(r for r in result["races"] if r["venue"] == "東京")
        assert len(tokyo_race["top_predictions"]) == 3

        kyoto_race = next(r for r in result["races"] if r["venue"] == "京都")
        assert len(kyoto_race["top_predictions"]) == 1

    def test_データがない場合(self, mock_dynamodb_table):
        """正常系: 指定日のデータがない場合."""
        mock_dynamodb_table.scan.return_value = {"Items": []}

        result = list_ai_predictions_for_date(date="20260201")

        assert result["date"] == "20260201"
        assert result["total_count"] == 0
        assert result["races"] == []
        assert "error" not in result

    def test_レースがソートされる(self, mock_dynamodb_table):
        """正常系: レースが競馬場名・レース番号でソートされる."""
        mock_dynamodb_table.scan.return_value = {
            "Items": [
                {"race_id": "202601310512", "source": "ai-shisu", "venue": "東京", "race_number": 12, "predictions": []},
                {"race_id": "202601310811", "source": "ai-shisu", "venue": "京都", "race_number": 11, "predictions": []},
                {"race_id": "202601310511", "source": "ai-shisu", "venue": "東京", "race_number": 11, "predictions": []},
            ]
        }

        result = list_ai_predictions_for_date(date="20260131")

        # 京都が先（あいうえお順）、その後東京
        assert result["races"][0]["venue"] == "京都"
        assert result["races"][1]["venue"] == "東京"
        assert result["races"][1]["race_number"] == 11
        assert result["races"][2]["venue"] == "東京"
        assert result["races"][2]["race_number"] == 12


def _make_predictions(horse_numbers_scores):
    """テスト用の予想データを生成するヘルパー.

    Args:
        horse_numbers_scores: [(horse_number, score), ...] スコア降順を想定
    """
    return [
        {"rank": i + 1, "score": score, "horse_number": hn, "horse_name": f"馬{hn}号"}
        for i, (hn, score) in enumerate(horse_numbers_scores)
    ]


def _make_source_item(race_id, source, horse_numbers_scores, venue="東京", race_number=11):
    """テスト用のDynamoDBアイテムを生成するヘルパー."""
    return {
        "race_id": race_id,
        "source": source,
        "venue": venue,
        "race_number": race_number,
        "predictions": _make_predictions(horse_numbers_scores),
        "scraped_at": "2026-01-31T06:00:00+09:00",
    }


class TestGetAiPredictionMultiSource:
    """get_ai_prediction マルチソース取得のテスト."""

    def test_全ソース取得_2ソースある場合(self, mock_dynamodb_table):
        """source=None で呼ぶと全ソースを取得しコンセンサスを付加する."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                _make_source_item("202601310511", "ai-shisu", [(8, 691), (3, 650), (5, 600), (1, 550)]),
                _make_source_item("202601310511", "muryou-keiba-ai", [(8, 700), (3, 680), (5, 620), (1, 500)]),
            ]
        }

        result = get_ai_prediction(race_id="202601310511", source=None)

        assert result["race_id"] == "202601310511"
        assert len(result["sources"]) == 2
        # ソース名は匿名化される（ai-shisu→AI-A, muryou-keiba-ai→AI-B）
        source_names = {s["source"] for s in result["sources"]}
        assert source_names == {"AI-A", "AI-B"}
        assert "consensus" in result
        assert "error" not in result
        # queryが呼ばれること
        mock_dynamodb_table.query.assert_called_once()

    def test_全ソース取得_1ソースのみの場合(self, mock_dynamodb_table):
        """1ソースのみの場合、sourcesに1つ。consensusは付加しない."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                _make_source_item("202601310511", "ai-shisu", [(8, 691), (3, 650), (5, 600)]),
            ]
        }

        result = get_ai_prediction(race_id="202601310511", source=None)

        assert result["race_id"] == "202601310511"
        assert len(result["sources"]) == 1
        assert result["sources"][0]["source"] == "AI-A"  # 匿名化される
        assert "consensus" not in result
        assert "error" not in result

    def test_source指定時は従来通り単一ソース返却(self, mock_dynamodb_table):
        """source指定の場合、従来と同じ形式で返す（後方互換）."""
        mock_dynamodb_table.get_item.return_value = {
            "Item": _make_source_item("202601310511", "ai-shisu", [(8, 691), (3, 650)])
        }

        result = get_ai_prediction(race_id="202601310511", source="ai-shisu")

        # 従来形式: source, predictions がトップレベル
        assert result["race_id"] == "202601310511"
        assert result["source"] == "AI-A"  # 匿名化される
        assert "predictions" in result
        assert "sources" not in result
        assert "consensus" not in result
        # get_itemが呼ばれること（queryではない）
        mock_dynamodb_table.get_item.assert_called_once()

    def test_データなしの場合(self, mock_dynamodb_table):
        """全ソース取得でデータがない場合."""
        mock_dynamodb_table.query.return_value = {"Items": []}

        result = get_ai_prediction(race_id="202601310599", source=None)

        assert result["race_id"] == "202601310599"
        assert "error" in result
        assert result["sources"] == []

    def test_全ソース取得_DynamoDBエラー時(self, mock_dynamodb_table):
        """全ソース取得でDynamoDBエラーが発生した場合."""
        from botocore.exceptions import ClientError
        mock_dynamodb_table.query.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
            "Query"
        )

        result = get_ai_prediction(race_id="202601310511", source=None)

        assert "error" in result
        assert "DynamoDBエラー" in result["error"]
        assert result["sources"] == []

    def test_デフォルト引数はsourceなし(self, mock_dynamodb_table):
        """引数なしで呼んだ場合、source=None として全ソース取得になる."""
        mock_dynamodb_table.query.return_value = {
            "Items": [
                _make_source_item("202601310511", "ai-shisu", [(8, 691), (3, 650), (5, 600)]),
            ]
        }

        # source引数を省略して呼ぶ
        result = get_ai_prediction(race_id="202601310511")

        # queryが呼ばれる（全ソース取得）
        mock_dynamodb_table.query.assert_called_once()
        assert "sources" in result


class TestAnalyzeConsensus:
    """コンセンサス分析のテスト."""

    def test_コンセンサス_完全合意(self):
        """top3の馬番・順位が完全一致."""
        sources = [
            {"source": "ai-shisu", "predictions": _make_predictions([(8, 700), (3, 650), (5, 600), (1, 550)])},
            {"source": "muryou-keiba-ai", "predictions": _make_predictions([(8, 710), (3, 660), (5, 610), (1, 540)])},
        ]

        result = _analyze_consensus(sources)

        assert result["consensus_level"] == "完全合意"
        assert set(result["agreed_top3"]) == {8, 3, 5}

    def test_コンセンサス_概ね合意(self):
        """top3の顔ぶれは一致するが順位が異なる."""
        sources = [
            {"source": "ai-shisu", "predictions": _make_predictions([(8, 700), (3, 650), (5, 600), (1, 550)])},
            {"source": "muryou-keiba-ai", "predictions": _make_predictions([(3, 710), (5, 660), (8, 610), (1, 540)])},
        ]

        result = _analyze_consensus(sources)

        assert result["consensus_level"] == "概ね合意"
        assert set(result["agreed_top3"]) == {8, 3, 5}

    def test_コンセンサス_部分合意(self):
        """top3中2頭が一致."""
        sources = [
            {"source": "ai-shisu", "predictions": _make_predictions([(8, 700), (3, 650), (5, 600), (1, 550)])},
            {"source": "muryou-keiba-ai", "predictions": _make_predictions([(8, 710), (3, 660), (1, 610), (5, 540)])},
        ]

        result = _analyze_consensus(sources)

        assert result["consensus_level"] == "部分合意"
        assert set(result["agreed_top3"]) == {8, 3}

    def test_コンセンサス_大きな乖離(self):
        """top3中1頭以下が一致."""
        sources = [
            {"source": "ai-shisu", "predictions": _make_predictions([(8, 700), (3, 650), (5, 600), (1, 550)])},
            {"source": "muryou-keiba-ai", "predictions": _make_predictions([(1, 710), (2, 660), (4, 610), (8, 540)])},
        ]

        result = _analyze_consensus(sources)

        assert result["consensus_level"] == "大きな乖離"
        assert len(result["agreed_top3"]) <= 1

    def test_乖離馬の検出(self):
        """ソース間で順位差が3以上の馬がdivergence_horsesに含まれる."""
        sources = [
            {"source": "ai-shisu", "predictions": _make_predictions([(8, 700), (3, 650), (5, 600), (1, 550)])},
            {"source": "muryou-keiba-ai", "predictions": _make_predictions([(1, 710), (3, 660), (8, 610), (5, 540)])},
        ]
        # 馬8: ai-shisu=1位, muryou=3位 → gap=2（乖離馬にならない）
        # 馬1: ai-shisu=4位, muryou=1位 → gap=3（乖離馬になる）

        result = _analyze_consensus(sources)

        divergence_numbers = [h["horse_number"] for h in result["divergence_horses"]]
        assert 1 in divergence_numbers  # gap=3
        # gap<3の馬は含まれない
        assert 3 not in divergence_numbers  # gap=0

    def test_乖離馬のランク情報(self):
        """乖離馬にはソースごとの順位とgapが含まれる."""
        sources = [
            {"source": "ai-shisu", "predictions": _make_predictions([(8, 700), (3, 650), (5, 600), (1, 550)])},
            {"source": "muryou-keiba-ai", "predictions": _make_predictions([(1, 710), (5, 660), (3, 610), (8, 540)])},
        ]
        # 馬8: ai-shisu=1位, muryou=4位 → gap=3
        # 馬1: ai-shisu=4位, muryou=1位 → gap=3

        result = _analyze_consensus(sources)

        divergence_map = {h["horse_number"]: h for h in result["divergence_horses"]}
        assert 8 in divergence_map
        assert divergence_map[8]["ranks"]["ai-shisu"] == 1
        assert divergence_map[8]["ranks"]["muryou-keiba-ai"] == 4
        assert divergence_map[8]["gap"] == 3


class TestBuildSourceLabelMap:
    """_build_source_label_map のテスト."""

    def test_2ソースのマッピング(self):
        """アルファベット順でAI-A, AI-Bが割り当てられる."""
        result = _build_source_label_map(["muryou-keiba-ai", "ai-shisu"])

        assert result == {"ai-shisu": "AI-A", "muryou-keiba-ai": "AI-B"}

    def test_1ソースのマッピング(self):
        """1ソースの場合はAI-A固定."""
        result = _build_source_label_map(["ai-shisu"])

        assert result == {"ai-shisu": "AI-A"}

    def test_3ソースのマッピング(self):
        """3ソースの場合はAI-A, AI-B, AI-C."""
        result = _build_source_label_map(["z-source", "a-source", "m-source"])

        assert result == {"a-source": "AI-A", "m-source": "AI-B", "z-source": "AI-C"}

    def test_重複ソース名は1つにまとめる(self):
        """重複するソース名がある場合は1つにまとめる."""
        result = _build_source_label_map(["ai-shisu", "ai-shisu", "muryou-keiba-ai"])

        assert result == {"ai-shisu": "AI-A", "muryou-keiba-ai": "AI-B"}

    def test_空リスト(self):
        """空リストの場合は空の辞書を返す."""
        result = _build_source_label_map([])

        assert result == {}


class TestAnonymizeSources:
    """_anonymize_sources のテスト."""

    def test_全ソース結果の匿名化(self):
        """sources[].sourceとconsensus.divergence_horses[].ranksが匿名化される."""
        result = {
            "race_id": "202601310511",
            "sources": [
                {"source": "ai-shisu", "predictions": []},
                {"source": "muryou-keiba-ai", "predictions": []},
            ],
            "consensus": {
                "agreed_top3": [8, 3, 5],
                "consensus_level": "完全合意",
                "divergence_horses": [
                    {"horse_number": 1, "ranks": {"ai-shisu": 4, "muryou-keiba-ai": 1}, "gap": 3},
                ],
            },
        }

        anonymized = _anonymize_sources(result)

        assert anonymized["sources"][0]["source"] == "AI-A"
        assert anonymized["sources"][1]["source"] == "AI-B"
        assert anonymized["consensus"]["divergence_horses"][0]["ranks"] == {"AI-A": 4, "AI-B": 1}

    def test_consensusなしの場合(self):
        """1ソースでconsensusがない場合もsourceは匿名化される."""
        result = {
            "race_id": "202601310511",
            "sources": [
                {"source": "ai-shisu", "predictions": []},
            ],
        }

        anonymized = _anonymize_sources(result)

        assert anonymized["sources"][0]["source"] == "AI-A"
        assert "consensus" not in anonymized

    def test_空sourcesの場合(self):
        """sourcesが空の場合はそのまま返す."""
        result = {
            "race_id": "202601310511",
            "sources": [],
            "error": "データなし",
        }

        anonymized = _anonymize_sources(result)

        assert anonymized["sources"] == []
        assert anonymized["error"] == "データなし"

    def test_ソート順でラベルが安定する(self):
        """DynamoDBの返却順が変わってもラベルの割り当ては安定する."""
        # muryou-keiba-aiが先に来るケース
        result1 = {
            "race_id": "202601310511",
            "sources": [
                {"source": "muryou-keiba-ai", "predictions": []},
                {"source": "ai-shisu", "predictions": []},
            ],
        }
        # ai-shisuが先に来るケース
        result2 = {
            "race_id": "202601310511",
            "sources": [
                {"source": "ai-shisu", "predictions": []},
                {"source": "muryou-keiba-ai", "predictions": []},
            ],
        }

        anon1 = _anonymize_sources(result1)
        anon2 = _anonymize_sources(result2)

        # どちらの順でも ai-shisu→AI-A, muryou-keiba-ai→AI-B
        for anon in [anon1, anon2]:
            source_map = {s["source"]: True for s in anon["sources"]}
            assert "AI-A" in source_map
            assert "AI-B" in source_map
