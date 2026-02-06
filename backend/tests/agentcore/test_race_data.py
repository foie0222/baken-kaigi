"""レースデータ取得ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

# strandsモジュールが利用できない場合はスキップ
try:
    # agentcoreモジュールをインポートできるようにパスを追加
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

    from tools.race_data import get_race_data, get_race_runners, _extract_race_conditions
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

pytestmark = pytest.mark.skipif(not STRANDS_AVAILABLE, reason="strands module not available")


@pytest.fixture(autouse=True)
def mock_get_headers():
    """全テストで get_headers をモック化してboto3呼び出しを防ぐ."""
    with patch("tools.race_data.get_headers", return_value={"x-api-key": "test-key"}):
        yield


@pytest.fixture(autouse=True)
def mock_get_api_url():
    """全テストで get_api_url をモック化."""
    with patch("tools.race_data.get_api_url", return_value="https://api.example.com"):
        yield


class TestGetRaceData:
    """get_race_data統合テスト."""

    @patch("tools.race_data.requests.get")
    def test_正常なAPI応答でraceとrunnersを返す(self, mock_get):
        """正常系: APIが成功した場合、raceとrunnersを含む辞書を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "race": {
                "race_id": "20260125_06_11",
                "race_name": "テストレース",
                "distance": 1600,
                "track_type": "芝",
            },
            "runners": [
                {"horse_number": 1, "horse_name": "テスト馬1", "odds": 2.5, "popularity": 1},
                {"horse_number": 2, "horse_name": "テスト馬2", "odds": 5.0, "popularity": 2},
            ],
        }
        mock_get.return_value = mock_response

        result = get_race_data("20260125_06_11")

        assert "race" in result
        assert "runners" in result
        assert result["race"]["race_name"] == "テストレース"
        assert result["race"]["distance"] == 1600
        assert len(result["runners"]) == 2
        assert result["runners"][0]["horse_name"] == "テスト馬1"

    @patch("tools.race_data.requests.get")
    def test_空のデータでも空の辞書を返す(self, mock_get):
        """空のレスポンスの場合、空のrace/runnersを返す."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        result = get_race_data("20260125_06_11")

        assert result["race"] == {}
        assert result["runners"] == []

    @patch("tools.race_data.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを含む辞書を返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = get_race_data("20260125_06_11")

        assert "error" in result
        assert "API呼び出しに失敗しました" in result["error"]
        assert "Connection failed" in result["error"]

    @patch("tools.race_data.requests.get")
    def test_タイムアウト時にエラーを返す(self, mock_get):
        """異常系: タイムアウト時はerrorを含む辞書を返す."""
        mock_get.side_effect = requests.Timeout("Request timed out")

        result = get_race_data("20260125_06_11")

        assert "error" in result
        assert "API呼び出しに失敗しました" in result["error"]

    @patch("tools.race_data.requests.get")
    def test_HTTPエラー時にエラーを返す(self, mock_get):
        """異常系: HTTPステータスエラー時はerrorを含む辞書を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_response

        result = get_race_data("20260125_06_11")

        assert "error" in result
        assert "API呼び出しに失敗しました" in result["error"]

    @patch("tools.race_data.requests.get")
    def test_正しいURLとヘッダーでAPIを呼び出す(self, mock_get):
        """APIが正しいURL、ヘッダー、タイムアウトで呼び出されることを確認."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"race": {}, "runners": []}
        mock_get.return_value = mock_response

        get_race_data("20260125_06_11")

        mock_get.assert_called_once_with(
            "https://api.example.com/races/20260125_06_11",
            headers={"x-api-key": "test-key"},
            timeout=10,
        )


def _make_api_response(race_overrides=None, runners=None):
    """テスト用APIレスポンスを生成するヘルパー."""
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
    if runners is None:
        runners = [
            {"horse_number": 1, "horse_name": "テスト馬1", "odds": 2.5, "popularity": 1,
             "jockey_name": "テスト騎手1", "waku_ban": 1},
            {"horse_number": 2, "horse_name": "テスト馬2", "odds": 5.0, "popularity": 2,
             "jockey_name": "テスト騎手2", "waku_ban": 1},
            {"horse_number": 3, "horse_name": "テスト馬3", "odds": 10.0, "popularity": 3,
             "jockey_name": "テスト騎手3", "waku_ban": 2},
        ]
    return {"race": race, "runners": runners}


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

    @patch("tools.race_data.requests.get")
    def test_正常なAPI応答で分析用データを返す(self, mock_get):
        """正常系: runners_data, race_conditions, venue, surface等を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_api_response()
        mock_get.return_value = mock_response

        result = get_race_runners("20260125_06_11")

        assert "runners_data" in result
        assert "race_conditions" in result
        assert "venue" in result
        assert "surface" in result
        assert "distance" in result
        assert "total_runners" in result
        assert "race_name" in result
        assert "error" not in result

    @patch("tools.race_data.requests.get")
    def test_runners_dataに出走馬情報を含む(self, mock_get):
        """runners_dataにhorse_number, horse_name, odds, popularityが含まれる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_api_response()
        mock_get.return_value = mock_response

        result = get_race_runners("20260125_06_11")

        assert len(result["runners_data"]) == 3
        runner = result["runners_data"][0]
        assert runner["horse_number"] == 1
        assert runner["horse_name"] == "テスト馬1"
        assert runner["odds"] == 2.5
        assert runner["popularity"] == 1

    @patch("tools.race_data.requests.get")
    def test_レース情報を正しく返す(self, mock_get):
        """venue, surface, distance, total_runnersを正しく返す."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_api_response()
        mock_get.return_value = mock_response

        result = get_race_runners("20260125_06_11")

        assert result["venue"] == "東京"
        assert result["surface"] == "芝"
        assert result["distance"] == 1600
        assert result["total_runners"] == 16
        assert result["race_name"] == "テストレース"

    @patch("tools.race_data.requests.get")
    def test_G1レースのrace_conditionsを抽出する(self, mock_get):
        """G1レースの場合、race_conditionsに'g1'が含まれる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_api_response(
            race_overrides={"grade_class": "G1"}
        )
        mock_get.return_value = mock_response

        result = get_race_runners("20260125_06_11")

        assert "g1" in result["race_conditions"]

    @patch("tools.race_data.requests.get")
    def test_ハンデ新馬戦のrace_conditionsを抽出する(self, mock_get):
        """ハンデ新馬戦の場合、handicapとmaiden_newが含まれる."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_api_response(
            race_overrides={
                "race_name": "テストハンデ",
                "age_condition": "新馬",
            }
        )
        mock_get.return_value = mock_response

        result = get_race_runners("20260125_06_11")

        assert "handicap" in result["race_conditions"]
        assert "maiden_new" in result["race_conditions"]

    @patch("tools.race_data.requests.get")
    def test_空のデータでもエラーなく返す(self, mock_get):
        """空のAPIレスポンスでもクラッシュしない."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        result = get_race_runners("20260125_06_11")

        assert result["runners_data"] == []
        assert result["race_conditions"] == []
        assert result["venue"] == ""
        assert result["surface"] == ""
        assert result["total_runners"] == 0

    @patch("tools.race_data.requests.get")
    def test_RequestException時にエラーを返す(self, mock_get):
        """異常系: RequestException発生時はerrorを含む辞書を返す."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = get_race_runners("20260125_06_11")

        assert "error" in result
        assert "API呼び出しに失敗しました" in result["error"]

    @patch("tools.race_data.requests.get")
    def test_HTTPエラー時にエラーを返す(self, mock_get):
        """異常系: HTTPステータスエラー時はerrorを含む辞書を返す."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = get_race_runners("20260125_06_11")

        assert "error" in result
        assert "API呼び出しに失敗しました" in result["error"]

    @patch("tools.race_data.requests.get")
    def test_horse_countがない場合runnersの長さをtotal_runnersにする(self, mock_get):
        """horse_countが未設定の場合、runnersリストの長さをtotal_runnersにする."""
        api_response = _make_api_response()
        del api_response["race"]["horse_count"]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response
        mock_get.return_value = mock_response

        result = get_race_runners("20260125_06_11")

        assert result["total_runners"] == 3  # runnersが3頭
