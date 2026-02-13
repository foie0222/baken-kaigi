"""レースデータ取得ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# strandsモジュールが利用できない場合はスキップ
try:
    # agentcoreモジュールをインポートできるようにパスを追加
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

    from tools.race_data import get_race_data, get_race_runners, _extract_race_conditions
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


def _make_race_data(race_overrides=None):
    """テスト用レースデータを生成するヘルパー."""
    race = {
        "race_id": "20260125_06_11",
        "race_name": "テストレース",
        "venue": "東京",
        "track_type": "芝",
        "distance": 1600,
        "horse_count": 16,
        "grade_class": "",
        "age_condition": "",
        "is_obstacle": False,
    }
    if race_overrides:
        race.update(race_overrides)
    return race


def _make_runners():
    """テスト用出走馬リストを生成するヘルパー."""
    return [
        {"horse_number": 1, "horse_name": "テスト馬1", "odds": 2.5, "popularity": 1,
         "jockey_name": "テスト騎手1", "waku_ban": 1},
        {"horse_number": 2, "horse_name": "テスト馬2", "odds": 5.0, "popularity": 2,
         "jockey_name": "テスト騎手2", "waku_ban": 1},
        {"horse_number": 3, "horse_name": "テスト馬3", "odds": 10.0, "popularity": 3,
         "jockey_name": "テスト騎手3", "waku_ban": 2},
    ]


class TestGetRaceData:
    """get_race_dataテスト."""

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_正常にraceとrunnersを返す(self, mock_get_race, mock_get_runners):
        mock_get_race.return_value = _make_race_data()
        mock_get_runners.return_value = _make_runners()

        result = get_race_data("20260125_06_11")

        assert "race" in result
        assert "runners" in result
        assert result["race"]["race_name"] == "テストレース"
        assert result["race"]["distance"] == 1600
        assert len(result["runners"]) == 3
        assert result["runners"][0]["horse_name"] == "テスト馬1"

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_レースが存在しない場合空raceを返す(self, mock_get_race, mock_get_runners):
        mock_get_race.return_value = None
        mock_get_runners.return_value = []

        result = get_race_data("20260125_06_11")

        assert result["race"] == {}
        assert result["runners"] == []

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_例外時にエラーを返す(self, mock_get_race, mock_get_runners):
        mock_get_race.side_effect = Exception("DynamoDB error")

        result = get_race_data("20260125_06_11")

        assert "error" in result
        assert "データ取得に失敗しました" in result["error"]

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_正しい引数でDynamoDBを呼び出す(self, mock_get_race, mock_get_runners):
        mock_get_race.return_value = {}
        mock_get_runners.return_value = []

        get_race_data("20260125_06_11")

        mock_get_race.assert_called_once_with("20260125_06_11")
        mock_get_runners.assert_called_once_with("20260125_06_11")


class TestExtractRaceConditions:
    """_extract_race_conditions のテスト."""

    def test_G1レースを検出する(self):
        race = {"grade_class": "G1", "age_condition": "", "race_name": "", "is_obstacle": False}
        assert "g1" in _extract_race_conditions(race)

    def test_G2レースを検出する(self):
        race = {"grade_class": "G2", "age_condition": "", "race_name": "", "is_obstacle": False}
        assert "g2" in _extract_race_conditions(race)

    def test_G3レースを検出する(self):
        race = {"grade_class": "G3", "age_condition": "", "race_name": "", "is_obstacle": False}
        assert "g3" in _extract_race_conditions(race)

    def test_新馬戦を検出する(self):
        race = {"grade_class": "", "age_condition": "新馬", "race_name": "", "is_obstacle": False}
        assert "maiden_new" in _extract_race_conditions(race)

    def test_未勝利戦を検出する(self):
        race = {"grade_class": "", "age_condition": "未勝利", "race_name": "", "is_obstacle": False}
        assert "maiden" in _extract_race_conditions(race)

    def test_ハンデ戦を検出する(self):
        race = {"grade_class": "", "age_condition": "", "race_name": "テストハンデ", "is_obstacle": False}
        assert "handicap" in _extract_race_conditions(race)

    def test_牝馬限定戦を検出する(self):
        race = {"grade_class": "", "age_condition": "", "race_name": "牝馬ステークス", "is_obstacle": False}
        assert "fillies_mares" in _extract_race_conditions(race)

    def test_障害戦を検出する(self):
        race = {"grade_class": "", "age_condition": "", "race_name": "", "is_obstacle": True}
        assert "hurdle" in _extract_race_conditions(race)

    def test_複数条件を同時に検出する(self):
        race = {"grade_class": "G1", "age_condition": "", "race_name": "牝馬ハンデG1", "is_obstacle": False}
        conditions = _extract_race_conditions(race)
        assert "g1" in conditions
        assert "handicap" in conditions
        assert "fillies_mares" in conditions

    def test_条件なしで空リストを返す(self):
        race = {"grade_class": "", "age_condition": "", "race_name": "通常レース", "is_obstacle": False}
        assert _extract_race_conditions(race) == []


class TestGetRaceRunners:
    """get_race_runners のテスト."""

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_正常に分析用データを返す(self, mock_get_race, mock_get_runners):
        mock_get_race.return_value = _make_race_data()
        mock_get_runners.return_value = _make_runners()

        result = get_race_runners("20260125_06_11")

        assert "runners_data" in result
        assert "race_conditions" in result
        assert "venue" in result
        assert "surface" in result
        assert "distance" in result
        assert "total_runners" in result
        assert "race_name" in result
        assert "error" not in result

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_runners_dataに出走馬情報を含む(self, mock_get_race, mock_get_runners):
        mock_get_race.return_value = _make_race_data()
        mock_get_runners.return_value = _make_runners()

        result = get_race_runners("20260125_06_11")

        assert len(result["runners_data"]) == 3
        runner = result["runners_data"][0]
        assert runner["horse_number"] == 1
        assert runner["horse_name"] == "テスト馬1"
        assert runner["odds"] == 2.5
        assert runner["popularity"] == 1

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_レース情報を正しく返す(self, mock_get_race, mock_get_runners):
        mock_get_race.return_value = _make_race_data()
        mock_get_runners.return_value = _make_runners()

        result = get_race_runners("20260125_06_11")

        assert result["venue"] == "東京"
        assert result["surface"] == "芝"
        assert result["distance"] == 1600
        assert result["total_runners"] == 16
        assert result["race_name"] == "テストレース"

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_G1レースのrace_conditionsを抽出する(self, mock_get_race, mock_get_runners):
        mock_get_race.return_value = _make_race_data({"grade_class": "G1"})
        mock_get_runners.return_value = _make_runners()

        result = get_race_runners("20260125_06_11")

        assert "g1" in result["race_conditions"]

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_ハンデ新馬戦のrace_conditionsを抽出する(self, mock_get_race, mock_get_runners):
        mock_get_race.return_value = _make_race_data({
            "race_name": "テストハンデ",
            "age_condition": "新馬",
        })
        mock_get_runners.return_value = _make_runners()

        result = get_race_runners("20260125_06_11")

        assert "handicap" in result["race_conditions"]
        assert "maiden_new" in result["race_conditions"]

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_空のデータでもエラーなく返す(self, mock_get_race, mock_get_runners):
        mock_get_race.return_value = None
        mock_get_runners.return_value = []

        result = get_race_runners("20260125_06_11")

        assert result["runners_data"] == []
        assert result["race_conditions"] == []
        assert result["venue"] == ""
        assert result["surface"] == ""
        assert result["total_runners"] == 0

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_例外時にエラーを返す(self, mock_get_race, mock_get_runners):
        mock_get_race.side_effect = Exception("Connection error")

        result = get_race_runners("20260125_06_11")

        assert "error" in result
        assert "データ取得に失敗しました" in result["error"]

    @patch("tools.dynamodb_client.get_runners")
    @patch("tools.dynamodb_client.get_race")
    def test_horse_countがない場合runnersの長さをtotal_runnersにする(self, mock_get_race, mock_get_runners):
        race = _make_race_data()
        del race["horse_count"]
        mock_get_race.return_value = race
        mock_get_runners.return_value = _make_runners()

        result = get_race_runners("20260125_06_11")

        assert result["total_runners"] == 3  # runnersが3頭
