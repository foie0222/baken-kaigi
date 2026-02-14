"""IpatBetLineのテスト."""
import pytest

from src.domain.enums import IpatBetType, IpatVenueCode
from src.domain.value_objects import IpatBetLine


class TestIpatBetLine:
    """IpatBetLineの単体テスト."""

    def test_正常な値で生成できる(self) -> None:
        """正常な値でIpatBetLineを生成できることを確認."""
        line = IpatBetLine(
            opdt="20260201",
            venue_code=IpatVenueCode.TOKYO,
            race_number=11,
            bet_type=IpatBetType.TANSYO,
            number="03",
            amount=100,
        )
        assert line.opdt == "20260201"
        assert line.venue_code == IpatVenueCode.TOKYO
        assert line.race_number == 11
        assert line.bet_type == IpatBetType.TANSYO
        assert line.number == "03"
        assert line.amount == 100

    def test_レース番号が0以下でエラー(self) -> None:
        """レース番号が0以下の場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="1から12"):
            IpatBetLine(
                opdt="20260201",
                venue_code=IpatVenueCode.TOKYO,
                race_number=0,
                bet_type=IpatBetType.TANSYO,
                number="03",
                amount=100,
            )

    def test_レース番号が13以上でエラー(self) -> None:
        """レース番号が13以上の場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="1から12"):
            IpatBetLine(
                opdt="20260201",
                venue_code=IpatVenueCode.TOKYO,
                race_number=13,
                bet_type=IpatBetType.TANSYO,
                number="03",
                amount=100,
            )

    def test_金額が100円未満でエラー(self) -> None:
        """金額が100円未満の場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="100円単位"):
            IpatBetLine(
                opdt="20260201",
                venue_code=IpatVenueCode.TOKYO,
                race_number=1,
                bet_type=IpatBetType.TANSYO,
                number="03",
                amount=50,
            )

    def test_金額が100円単位でないとエラー(self) -> None:
        """金額が100円単位でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="100円単位"):
            IpatBetLine(
                opdt="20260201",
                venue_code=IpatVenueCode.TOKYO,
                race_number=1,
                bet_type=IpatBetType.TANSYO,
                number="03",
                amount=150,
            )

    def test_単勝のCSV行を生成できる(self) -> None:
        """単勝のCSV行を正しく生成できることを確認."""
        line = IpatBetLine(
            opdt="20260201",
            venue_code=IpatVenueCode.TOKYO,
            race_number=11,
            bet_type=IpatBetType.TANSYO,
            number="03",
            amount=100,
        )
        csv = line.to_csv_line()
        assert csv == "20260201,TOKYO,11,TANSYO,NORMAL,,03,100"

    def test_馬連のCSV行を生成できる(self) -> None:
        """馬連のCSV行を正しく生成できることを確認."""
        line = IpatBetLine(
            opdt="20260201",
            venue_code=IpatVenueCode.NAKAYAMA,
            race_number=1,
            bet_type=IpatBetType.UMAREN,
            number="01-03",
            amount=500,
        )
        csv = line.to_csv_line()
        assert csv == "20260201,NAKAYAMA,1,UMAREN,NORMAL,,01-03,500"

    def test_三連単のCSV行を生成できる(self) -> None:
        """三連単のCSV行を正しく生成できることを確認."""
        line = IpatBetLine(
            opdt="20260201",
            venue_code=IpatVenueCode.HANSHIN,
            race_number=12,
            bet_type=IpatBetType.SANRENTAN,
            number="01-03-07",
            amount=1000,
        )
        csv = line.to_csv_line()
        assert csv == "20260201,HANSHIN,12,SANRENTAN,NORMAL,,01-03-07,1000"

    def test_不変オブジェクトである(self) -> None:
        """IpatBetLineは不変（frozen）であることを確認."""
        line = IpatBetLine(
            opdt="20260201",
            venue_code=IpatVenueCode.TOKYO,
            race_number=11,
            bet_type=IpatBetType.TANSYO,
            number="03",
            amount=100,
        )
        with pytest.raises(AttributeError):
            line.amount = 200  # type: ignore
