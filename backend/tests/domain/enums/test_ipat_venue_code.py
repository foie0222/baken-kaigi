"""IpatVenueCodeのテスト."""
import pytest

from src.domain.enums import IpatVenueCode


class TestIpatVenueCode:
    """IpatVenueCodeの単体テスト."""

    def test_TOKYOが存在する(self) -> None:
        """TOKYOメンバーが存在することを確認."""
        assert IpatVenueCode.TOKYO.value == "05"

    def test_NAKAYAMAが存在する(self) -> None:
        """NAKAYAMAメンバーが存在することを確認."""
        assert IpatVenueCode.NAKAYAMA.value == "06"

    def test_HANSHINが存在する(self) -> None:
        """HANSHINメンバーが存在することを確認."""
        assert IpatVenueCode.HANSHIN.value == "09"

    def test_KYOTOが存在する(self) -> None:
        """KYOTOメンバーが存在することを確認."""
        assert IpatVenueCode.KYOTO.value == "08"

    def test_SAPPOROが存在する(self) -> None:
        """SAPPOROメンバーが存在することを確認."""
        assert IpatVenueCode.SAPPORO.value == "01"

    def test_HAKODATEが存在する(self) -> None:
        """HAKODATEメンバーが存在することを確認."""
        assert IpatVenueCode.HAKODATE.value == "02"

    def test_FUKUSHIMAが存在する(self) -> None:
        """FUKUSHIMAメンバーが存在することを確認."""
        assert IpatVenueCode.FUKUSHIMA.value == "03"

    def test_NIIGATAが存在する(self) -> None:
        """NIIGATAメンバーが存在することを確認."""
        assert IpatVenueCode.NIIGATA.value == "04"

    def test_CHUKYOが存在する(self) -> None:
        """CHUKYOメンバーが存在することを確認."""
        assert IpatVenueCode.CHUKYO.value == "07"

    def test_KOKURAが存在する(self) -> None:
        """KOKURAメンバーが存在することを確認."""
        assert IpatVenueCode.KOKURA.value == "10"

    def test_コード05からTOKYOに変換(self) -> None:
        """コード'05'からIpatVenueCode.TOKYOに変換できることを確認."""
        assert IpatVenueCode.from_course_code("05") == IpatVenueCode.TOKYO

    def test_コード06からNAKAYAMAに変換(self) -> None:
        """コード'06'からIpatVenueCode.NAKAYAMAに変換できることを確認."""
        assert IpatVenueCode.from_course_code("06") == IpatVenueCode.NAKAYAMA

    def test_コード09からHANSHINに変換(self) -> None:
        """コード'09'からIpatVenueCode.HANSHINに変換できることを確認."""
        assert IpatVenueCode.from_course_code("09") == IpatVenueCode.HANSHIN

    def test_コード01からSAPPOROに変換(self) -> None:
        """コード'01'からIpatVenueCode.SAPPOROに変換できることを確認."""
        assert IpatVenueCode.from_course_code("01") == IpatVenueCode.SAPPORO

    def test_コード10からKOKURAに変換(self) -> None:
        """コード'10'からIpatVenueCode.KOKURAに変換できることを確認."""
        assert IpatVenueCode.from_course_code("10") == IpatVenueCode.KOKURA

    def test_不正なコードでエラー(self) -> None:
        """不正なコードでValueErrorが発生することを確認."""
        with pytest.raises(ValueError):
            IpatVenueCode.from_course_code("99")

    def test_会場は10箇所(self) -> None:
        """会場が10箇所であることを確認."""
        assert len(IpatVenueCode) == 10
