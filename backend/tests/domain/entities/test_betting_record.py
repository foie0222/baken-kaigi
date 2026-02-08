"""BettingRecordのテスト."""
from datetime import date, datetime

import pytest

from src.domain.entities import BettingRecord
from src.domain.enums import BetType, BettingRecordStatus
from src.domain.identifiers import BettingRecordId, RaceId, UserId
from src.domain.value_objects import HorseNumbers, Money


def _make_record(**kwargs) -> BettingRecord:
    """テスト用のBettingRecordを生成する."""
    defaults = {
        "user_id": UserId("user-1"),
        "race_id": RaceId("202602010811"),
        "race_name": "東京11R フェブラリーS",
        "race_date": date(2026, 2, 1),
        "venue": "東京",
        "bet_type": BetType.WIN,
        "horse_numbers": HorseNumbers.of(3),
        "amount": Money.of(1000),
    }
    defaults.update(kwargs)
    return BettingRecord.create(**defaults)


class TestBettingRecordCreate:
    """BettingRecord.createのテスト."""

    def test_createで生成できる(self) -> None:
        """createファクトリメソッドでBettingRecordを生成できることを確認."""
        record = _make_record()

        assert record.user_id == UserId("user-1")
        assert record.race_id == RaceId("202602010811")
        assert record.race_name == "東京11R フェブラリーS"
        assert record.race_date == date(2026, 2, 1)
        assert record.venue == "東京"
        assert record.bet_type == BetType.WIN
        assert record.horse_numbers == HorseNumbers.of(3)
        assert record.amount == Money.of(1000)
        assert record.payout == Money.zero()
        assert record.profit == 0
        assert record.status == BettingRecordStatus.PENDING
        assert record.record_id is not None
        assert record.created_at is not None
        assert record.settled_at is None

    def test_三連単で生成できる(self) -> None:
        """三連単のBettingRecordを生成できることを確認."""
        record = _make_record(
            bet_type=BetType.TRIFECTA,
            horse_numbers=HorseNumbers.of(3, 5, 8),
            amount=Money.of(500),
        )

        assert record.bet_type == BetType.TRIFECTA
        assert record.horse_numbers == HorseNumbers.of(3, 5, 8)
        assert record.amount == Money.of(500)


class TestBettingRecordSettle:
    """BettingRecord.settleのテスト."""

    def test_settleでSETTLEDになり払戻と損益が設定される(self) -> None:
        """settleでステータスがSETTLEDになり、払戻額と損益が計算されることを確認."""
        record = _make_record(amount=Money.of(1000))

        record.settle(payout=Money.of(3000))

        assert record.status == BettingRecordStatus.SETTLED
        assert record.payout == Money.of(3000)
        assert record.profit == 2000
        assert record.settled_at is not None

    def test_settleでハズレの場合_払戻ゼロで損益がマイナスになる(self) -> None:
        """ハズレの場合、払戻がゼロで損益が投資額のマイナスになることを確認."""
        record = _make_record(amount=Money.of(1000))

        record.settle(payout=Money.of(0))

        assert record.status == BettingRecordStatus.SETTLED
        assert record.payout == Money.zero()
        assert record.profit == -1000
        assert record.settled_at is not None

    def test_SETTLED状態からsettleすると例外(self) -> None:
        """既にSETTLED状態のレコードにsettleすると例外が発生することを確認."""
        record = _make_record()
        record.settle(payout=Money.of(3000))

        with pytest.raises(ValueError, match="PENDING"):
            record.settle(payout=Money.of(5000))

    def test_CANCELLED状態からsettleすると例外(self) -> None:
        """CANCELLED状態のレコードにsettleすると例外が発生することを確認."""
        record = _make_record()
        record.cancel()

        with pytest.raises(ValueError, match="PENDING"):
            record.settle(payout=Money.of(3000))


class TestBettingRecordCancel:
    """BettingRecord.cancelのテスト."""

    def test_cancelでCANCELLEDになる(self) -> None:
        """cancelでステータスがCANCELLEDに変更されることを確認."""
        record = _make_record()

        record.cancel()

        assert record.status == BettingRecordStatus.CANCELLED

    def test_SETTLED状態からcancelすると例外(self) -> None:
        """既にSETTLED状態のレコードにcancelすると例外が発生することを確認."""
        record = _make_record()
        record.settle(payout=Money.of(3000))

        with pytest.raises(ValueError, match="PENDING"):
            record.cancel()

    def test_CANCELLED状態からcancelすると例外(self) -> None:
        """既にCANCELLED状態のレコードにcancelすると例外が発生することを確認."""
        record = _make_record()
        record.cancel()

        with pytest.raises(ValueError, match="PENDING"):
            record.cancel()


class TestBettingRecordProfit:
    """BettingRecordの損益計算テスト."""

    def test_的中時の純損益が正しい(self) -> None:
        """的中時の損益がpayout - amountであることを確認."""
        record = _make_record(amount=Money.of(500))
        record.settle(payout=Money.of(2500))

        assert record.profit == 2000

    def test_ハズレ時の純損益がマイナスになる(self) -> None:
        """ハズレ時の損益が投資額のマイナスになることを確認."""
        record = _make_record(amount=Money.of(1000))
        record.settle(payout=Money.of(0))

        assert record.profit == -1000

    def test_ハズレ時のprofitがマイナスになる(self) -> None:
        """payout < amountの場合にprofitがマイナスになることを確認."""
        record = _make_record(amount=Money.of(500))
        record.settle(payout=Money.of(200))

        assert record.profit == -300

    def test_金額ゼロで的中率に影響しない(self) -> None:
        """payout=0の場合、的中扱いにならないことを確認."""
        record = _make_record(amount=Money.of(100))
        record.settle(payout=Money.of(0))

        assert record.payout == Money.zero()
        assert record.profit == -100
        assert record.status == BettingRecordStatus.SETTLED
