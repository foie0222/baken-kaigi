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
