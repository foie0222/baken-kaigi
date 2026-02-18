"""好み設定値オブジェクトのテスト."""
from src.domain.value_objects import BettingPreference


class TestBettingPreference:
    """BettingPreference値オブジェクトのテスト."""

    def test_デフォルト値で作成できる(self):
        pref = BettingPreference.default()
        assert pref.selected_bet_types == []

    def test_指定した券種で作成できる(self):
        pref = BettingPreference(
            selected_bet_types=["win", "trio"],
        )
        assert pref.selected_bet_types == ["win", "trio"]

    def test_to_dictで辞書に変換できる(self):
        pref = BettingPreference.default()
        d = pref.to_dict()
        assert d == {
            "selected_bet_types": [],
            "min_probability": 0.0,
            "min_ev": 0.0,
            "max_probability": None,
            "max_ev": None,
            "race_budget": 0,
        }

    def test_from_dictで復元できる(self):
        data = {
            "selected_bet_types": ["quinella", "trio"],
        }
        pref = BettingPreference.from_dict(data)
        assert pref.selected_bet_types == ["quinella", "trio"]

    def test_from_dictで空辞書はデフォルト(self):
        pref = BettingPreference.from_dict({})
        assert pref == BettingPreference.default()

    def test_from_dictでNoneはデフォルト(self):
        pref = BettingPreference.from_dict(None)
        assert pref == BettingPreference.default()

    def test_フィルターフィールド付きで作成できる(self):
        pref = BettingPreference(
            selected_bet_types=[],
            min_probability=0.05,
            min_ev=1.5,
        )
        assert pref.min_probability == 0.05
        assert pref.min_ev == 1.5

    def test_デフォルト値にフィルターフィールドが含まれる(self):
        pref = BettingPreference.default()
        assert pref.min_probability == 0.0
        assert pref.min_ev == 0.0
        assert pref.max_probability is None
        assert pref.max_ev is None

    def test_to_dictにフィルターフィールドが含まれる(self):
        pref = BettingPreference(
            selected_bet_types=["win"],
            min_probability=0.05,
            min_ev=1.5,
            max_probability=0.30,
            max_ev=5.0,
        )
        d = pref.to_dict()
        assert d == {
            "selected_bet_types": ["win"],
            "min_probability": 0.05,
            "min_ev": 1.5,
            "max_probability": 0.30,
            "max_ev": 5.0,
            "race_budget": 0,
        }

    def test_from_dictでフィルターフィールドを復元できる(self):
        data = {
            "selected_bet_types": ["trio"],
            "min_probability": 0.03,
            "min_ev": 1.2,
            "max_probability": 0.25,
            "max_ev": 4.0,
        }
        pref = BettingPreference.from_dict(data)
        assert pref.min_probability == 0.03
        assert pref.min_ev == 1.2
        assert pref.max_probability == 0.25
        assert pref.max_ev == 4.0

    def test_from_dictでフィルターフィールドなしはデフォルト値(self):
        data = {"selected_bet_types": []}
        pref = BettingPreference.from_dict(data)
        assert pref.min_probability == 0.0
        assert pref.min_ev == 0.0
        assert pref.max_probability is None
        assert pref.max_ev is None

    def test_from_dictでmaxがNoneの場合は上限なし(self):
        data = {
            "selected_bet_types": [],
            "min_probability": 0.05,
            "max_probability": None,
            "min_ev": 1.5,
            "max_ev": None,
        }
        pref = BettingPreference.from_dict(data)
        assert pref.max_probability is None
        assert pref.max_ev is None
