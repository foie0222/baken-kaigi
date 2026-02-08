"""BettingSummaryのテスト."""
from datetime import date

from src.domain.entities import BettingRecord
from src.domain.enums import BetType
from src.domain.identifiers import RaceId, UserId
from src.domain.value_objects import BettingSummary, HorseNumbers, Money


def _make_settled_record(amount: int, payout: int) -> BettingRecord:
    """確定済みテスト用BettingRecordを生成する."""
    record = BettingRecord.create(
        user_id=UserId("user-1"),
        race_id=RaceId("202602010811"),
        race_name="東京11R テスト",
        race_date=date(2026, 2, 1),
        venue="東京",
        bet_type=BetType.WIN,
        horse_numbers=HorseNumbers.of(3),
        amount=Money.of(amount),
    )
    record.settle(payout=Money.of(payout))
    return record


class TestBettingSummaryFromRecords:
    """BettingSummary.from_recordsのテスト."""

    def test_空リストから生成するとゼロサマリー(self) -> None:
        """空リストからBettingSummaryを生成するとすべてゼロになることを確認."""
        summary = BettingSummary.from_records([])

        assert summary.total_investment == Money.zero()
        assert summary.total_payout == Money.zero()
        assert summary.net_profit == 0
        assert summary.win_rate == 0.0
        assert summary.record_count == 0
        assert summary.roi == 0.0

    def test_全的中の場合の集計が正しい(self) -> None:
        """全て的中した場合のサマリーが正しいことを確認."""
        records = [
            _make_settled_record(1000, 3000),
            _make_settled_record(500, 1500),
        ]

        summary = BettingSummary.from_records(records)

        assert summary.total_investment == Money.of(1500)
        assert summary.total_payout == Money.of(4500)
        assert summary.net_profit == 3000
        assert summary.win_rate == 1.0
        assert summary.record_count == 2
        assert summary.roi == 300.0

    def test_全ハズレの場合の集計が正しい(self) -> None:
        """全てハズレの場合のサマリーが正しいことを確認."""
        records = [
            _make_settled_record(1000, 0),
            _make_settled_record(500, 0),
        ]

        summary = BettingSummary.from_records(records)

        assert summary.total_investment == Money.of(1500)
        assert summary.total_payout == Money.zero()
        assert summary.net_profit == -1500
        assert summary.win_rate == 0.0
        assert summary.record_count == 2
        assert summary.roi == 0.0

    def test_的中とハズレ混在の集計が正しい(self) -> None:
        """的中とハズレが混在する場合のサマリーが正しいことを確認."""
        records = [
            _make_settled_record(1000, 5000),  # 的中
            _make_settled_record(1000, 0),      # ハズレ
            _make_settled_record(1000, 0),      # ハズレ
            _make_settled_record(1000, 2000),   # 的中
        ]

        summary = BettingSummary.from_records(records)

        assert summary.total_investment == Money.of(4000)
        assert summary.total_payout == Money.of(7000)
        assert summary.net_profit == 3000
        assert summary.win_rate == 0.5
        assert summary.record_count == 4
        assert summary.roi == 175.0

    def test_未確定レコードは集計から除外される(self) -> None:
        """未確定（PENDING）のレコードはサマリーから除外されることを確認."""
        settled = _make_settled_record(1000, 3000)
        pending = BettingRecord.create(
            user_id=UserId("user-1"),
            race_id=RaceId("202602010811"),
            race_name="東京11R テスト",
            race_date=date(2026, 2, 1),
            venue="東京",
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(5),
            amount=Money.of(500),
        )

        summary = BettingSummary.from_records([settled, pending])

        # PENDINGレコードは除外されるので確定済み1件分のみ
        assert summary.record_count == 1
        assert summary.total_investment == Money.of(1000)
        assert summary.total_payout == Money.of(3000)
        assert summary.net_profit == 2000

    def test_キャンセル済みレコードは集計から除外される(self) -> None:
        """キャンセル済みのレコードはサマリーから除外されることを確認."""
        settled = _make_settled_record(1000, 5000)
        cancelled = BettingRecord.create(
            user_id=UserId("user-1"),
            race_id=RaceId("202602010811"),
            race_name="東京11R テスト",
            race_date=date(2026, 2, 1),
            venue="東京",
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(7),
            amount=Money.of(2000),
        )
        cancelled.cancel()

        summary = BettingSummary.from_records([settled, cancelled])

        # CANCELLEDレコードは除外されるので確定済み1件分のみ
        assert summary.record_count == 1
        assert summary.total_investment == Money.of(1000)
        assert summary.total_payout == Money.of(5000)
        assert summary.net_profit == 4000
        assert summary.roi == 500.0

    def test_全レコードが未確定の場合はゼロサマリー(self) -> None:
        """全てPENDINGの場合はゼロサマリーになることを確認."""
        pending = BettingRecord.create(
            user_id=UserId("user-1"),
            race_id=RaceId("202602010811"),
            race_name="東京11R テスト",
            race_date=date(2026, 2, 1),
            venue="東京",
            bet_type=BetType.WIN,
            horse_numbers=HorseNumbers.of(5),
            amount=Money.of(500),
        )

        summary = BettingSummary.from_records([pending])

        assert summary.record_count == 0
        assert summary.total_investment == Money.zero()
        assert summary.total_payout == Money.zero()
        assert summary.net_profit == 0
        assert summary.win_rate == 0.0
        assert summary.roi == 0.0


class TestBettingSummaryRoi:
    """BettingSummaryの回収率テスト."""

    def test_投資ゼロの場合のroiはゼロ(self) -> None:
        """投資額がゼロの場合はROIがゼロになることを確認."""
        summary = BettingSummary.from_records([])
        assert summary.roi == 0.0

    def test_回収率100パーセント(self) -> None:
        """投資額と払戻額が同じ場合に回収率100%であることを確認."""
        records = [_make_settled_record(1000, 1000)]

        summary = BettingSummary.from_records(records)

        assert summary.roi == 100.0

    def test_全ハズレでnet_profitがマイナスになる(self) -> None:
        """全ハズレ時にnet_profitが負値になることを確認."""
        records = [
            _make_settled_record(200, 0),
            _make_settled_record(300, 0),
        ]

        summary = BettingSummary.from_records(records)

        assert summary.net_profit == -500
        assert summary.total_investment == Money.of(500)
        assert summary.total_payout == Money.zero()

    def test_roiが50パーセントのケース(self) -> None:
        """半額回収の場合にROIが50%であることを確認."""
        records = [_make_settled_record(1000, 500)]

        summary = BettingSummary.from_records(records)

        assert summary.roi == 50.0
        assert summary.net_profit == -500
