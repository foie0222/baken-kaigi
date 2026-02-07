"""IpatBetTypeのテスト."""
from src.domain.enums import BetType, IpatBetType


class TestIpatBetType:
    """IpatBetTypeの単体テスト."""

    def test_TANSYOが存在する(self) -> None:
        """TANSYOメンバーが存在することを確認."""
        assert IpatBetType.TANSYO.value == "tansyo"

    def test_FUKUSYOが存在する(self) -> None:
        """FUKUSYOメンバーが存在することを確認."""
        assert IpatBetType.FUKUSYO.value == "fukusyo"

    def test_UMARENが存在する(self) -> None:
        """UMARENメンバーが存在することを確認."""
        assert IpatBetType.UMAREN.value == "umaren"

    def test_WIDEが存在する(self) -> None:
        """WIDEメンバーが存在することを確認."""
        assert IpatBetType.WIDE.value == "wide"

    def test_UMATANが存在する(self) -> None:
        """UMATANメンバーが存在することを確認."""
        assert IpatBetType.UMATAN.value == "umatan"

    def test_SANRENPUKUが存在する(self) -> None:
        """SANRENPUKUメンバーが存在することを確認."""
        assert IpatBetType.SANRENPUKU.value == "sanrenpuku"

    def test_SANRENTANが存在する(self) -> None:
        """SANRENTANメンバーが存在することを確認."""
        assert IpatBetType.SANRENTAN.value == "sanrentan"

    def test_WINからTANSYOに変換(self) -> None:
        """BetType.WINからIpatBetType.TANSYOに変換できることを確認."""
        assert IpatBetType.from_bet_type(BetType.WIN) == IpatBetType.TANSYO

    def test_PLACEからFUKUSYOに変換(self) -> None:
        """BetType.PLACEからIpatBetType.FUKUSYOに変換できることを確認."""
        assert IpatBetType.from_bet_type(BetType.PLACE) == IpatBetType.FUKUSYO

    def test_QUINELLAからUMARENに変換(self) -> None:
        """BetType.QUINELLAからIpatBetType.UMARENに変換できることを確認."""
        assert IpatBetType.from_bet_type(BetType.QUINELLA) == IpatBetType.UMAREN

    def test_QUINELLA_PLACEからWIDEに変換(self) -> None:
        """BetType.QUINELLA_PLACEからIpatBetType.WIDEに変換できることを確認."""
        assert IpatBetType.from_bet_type(BetType.QUINELLA_PLACE) == IpatBetType.WIDE

    def test_EXACTAからUMATANに変換(self) -> None:
        """BetType.EXACTAからIpatBetType.UMATANに変換できることを確認."""
        assert IpatBetType.from_bet_type(BetType.EXACTA) == IpatBetType.UMATAN

    def test_TRIOからSANRENPUKUに変換(self) -> None:
        """BetType.TRIOからIpatBetType.SANRENPUKUに変換できることを確認."""
        assert IpatBetType.from_bet_type(BetType.TRIO) == IpatBetType.SANRENPUKU

    def test_TRIFECTAからSANRENTANに変換(self) -> None:
        """BetType.TRIFECTAからIpatBetType.SANRENTANに変換できることを確認."""
        assert IpatBetType.from_bet_type(BetType.TRIFECTA) == IpatBetType.SANRENTAN

    def test_券種は7種類(self) -> None:
        """券種が7種類であることを確認."""
        assert len(IpatBetType) == 7
