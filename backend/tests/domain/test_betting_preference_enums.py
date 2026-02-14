"""好み設定列挙型のテスト."""
import pytest

from src.domain.enums import BetTypePreference, TargetStyle, BettingPriority


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


class TestTargetStyle:
    """狙い方列挙型のテスト."""

    def test_全ての値が定義されている(self):
        assert TargetStyle.HONMEI.value == "honmei"
        assert TargetStyle.MEDIUM_LONGSHOT.value == "medium_longshot"
        assert TargetStyle.BIG_LONGSHOT.value == "big_longshot"


class TestBettingPriority:
    """重視ポイント列挙型のテスト."""

    def test_全ての値が定義されている(self):
        assert BettingPriority.HIT_RATE.value == "hit_rate"
        assert BettingPriority.ROI.value == "roi"
        assert BettingPriority.BALANCED.value == "balanced"


from src.domain.value_objects import BettingPreference


class TestBettingPreference:
    """BettingPreference値オブジェクトのテスト."""

    def test_デフォルト値で作成できる(self):
        pref = BettingPreference.default()
        assert pref.bet_type_preference == BetTypePreference.AUTO
        assert pref.target_style == TargetStyle.MEDIUM_LONGSHOT
        assert pref.priority == BettingPriority.BALANCED

    def test_指定した値で作成できる(self):
        pref = BettingPreference(
            bet_type_preference=BetTypePreference.TRIO_FOCUSED,
            target_style=TargetStyle.BIG_LONGSHOT,
            priority=BettingPriority.ROI,
        )
        assert pref.bet_type_preference == BetTypePreference.TRIO_FOCUSED

    def test_to_dictで辞書に変換できる(self):
        pref = BettingPreference.default()
        d = pref.to_dict()
        assert d == {
            "bet_type_preference": "auto",
            "target_style": "medium_longshot",
            "priority": "balanced",
        }

    def test_from_dictで復元できる(self):
        data = {
            "bet_type_preference": "trio_focused",
            "target_style": "big_longshot",
            "priority": "roi",
        }
        pref = BettingPreference.from_dict(data)
        assert pref.bet_type_preference == BetTypePreference.TRIO_FOCUSED
        assert pref.target_style == TargetStyle.BIG_LONGSHOT
        assert pref.priority == BettingPriority.ROI

    def test_from_dictで空辞書はデフォルト(self):
        pref = BettingPreference.from_dict({})
        assert pref == BettingPreference.default()

    def test_from_dictでNoneはデフォルト(self):
        pref = BettingPreference.from_dict(None)
        assert pref == BettingPreference.default()
