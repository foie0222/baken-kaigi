"""好み設定列挙型のテスト."""
import pytest

from src.domain.enums import BetTypePreference


class TestBetTypePreference:
    """券種好み列挙型のテスト."""

    def test_全ての値が定義されている(self):
        assert BetTypePreference.TRIO_FOCUSED.value == "trio_focused"
        assert BetTypePreference.EXACTA_FOCUSED.value == "exacta_focused"
        assert BetTypePreference.QUINELLA_FOCUSED.value == "quinella_focused"
        assert BetTypePreference.WIDE_FOCUSED.value == "wide_focused"
        assert BetTypePreference.AUTO.value == "auto"

    def test_文字列から変換できる(self):
        assert BetTypePreference("trio_focused") == BetTypePreference.TRIO_FOCUSED


from src.domain.value_objects import BettingPreference


class TestBettingPreference:
    """BettingPreference値オブジェクトのテスト."""

    def test_デフォルト値で作成できる(self):
        pref = BettingPreference.default()
        assert pref.bet_type_preference == BetTypePreference.AUTO

    def test_指定した値で作成できる(self):
        pref = BettingPreference(
            bet_type_preference=BetTypePreference.TRIO_FOCUSED,
        )
        assert pref.bet_type_preference == BetTypePreference.TRIO_FOCUSED

    def test_to_dictで辞書に変換できる(self):
        pref = BettingPreference.default()
        d = pref.to_dict()
        assert d == {
            "bet_type_preference": "auto",
            "min_probability": 0.01,
            "max_probability": 0.50,
            "min_ev": 1.0,
            "max_ev": 10.0,
        }

    def test_from_dictで復元できる(self):
        data = {
            "bet_type_preference": "trio_focused",
        }
        pref = BettingPreference.from_dict(data)
        assert pref.bet_type_preference == BetTypePreference.TRIO_FOCUSED

    def test_from_dictで空辞書はデフォルト(self):
        pref = BettingPreference.from_dict({})
        assert pref == BettingPreference.default()

    def test_from_dictでNoneはデフォルト(self):
        pref = BettingPreference.from_dict(None)
        assert pref == BettingPreference.default()

    def test_from_dictで旧データのtarget_styleとpriorityは無視される(self):
        data = {
            "bet_type_preference": "trio_focused",
            "target_style": "big_longshot",
            "priority": "roi",
        }
        pref = BettingPreference.from_dict(data)
        assert pref.bet_type_preference == BetTypePreference.TRIO_FOCUSED

    def test_フィルターフィールド付きで作成できる(self):
        pref = BettingPreference(
            bet_type_preference=BetTypePreference.AUTO,
            min_probability=0.05,
            max_probability=0.30,
            min_ev=1.5,
            max_ev=5.0,
        )
        assert pref.min_probability == 0.05
        assert pref.max_probability == 0.30
        assert pref.min_ev == 1.5
        assert pref.max_ev == 5.0

    def test_デフォルト値にフィルターフィールドが含まれる(self):
        pref = BettingPreference.default()
        assert pref.min_probability == 0.01
        assert pref.max_probability == 0.50
        assert pref.min_ev == 1.0
        assert pref.max_ev == 10.0

    def test_to_dictにフィルターフィールドが含まれる(self):
        pref = BettingPreference(
            bet_type_preference=BetTypePreference.AUTO,
            min_probability=0.05,
            max_probability=0.30,
            min_ev=1.5,
            max_ev=5.0,
        )
        d = pref.to_dict()
        assert d == {
            "bet_type_preference": "auto",
            "min_probability": 0.05,
            "max_probability": 0.30,
            "min_ev": 1.5,
            "max_ev": 5.0,
        }

    def test_from_dictでフィルターフィールドを復元できる(self):
        data = {
            "bet_type_preference": "trio_focused",
            "min_probability": 0.03,
            "max_probability": 0.25,
            "min_ev": 1.2,
            "max_ev": 8.0,
        }
        pref = BettingPreference.from_dict(data)
        assert pref.min_probability == 0.03
        assert pref.max_probability == 0.25
        assert pref.min_ev == 1.2
        assert pref.max_ev == 8.0

    def test_from_dictでフィルターフィールドなしはデフォルト値(self):
        data = {"bet_type_preference": "auto"}
        pref = BettingPreference.from_dict(data)
        assert pref.min_probability == 0.01
        assert pref.max_probability == 0.50
        assert pref.min_ev == 1.0
        assert pref.max_ev == 10.0
