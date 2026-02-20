"""BetProposal → IpatBetLine 変換テスト."""
from src.domain.enums import IpatBetType, IpatVenueCode
from src.domain.services.bet_generator import BetProposal
from src.domain.services.bet_to_ipat_converter import BetToIpatConverter


class TestBetToIpatConverter:
    def test_単勝変換(self):
        proposal = BetProposal(bet_type="win", horse_numbers=[3], amount=200)
        lines = BetToIpatConverter.convert("202602210511", [proposal])
        assert len(lines) == 1
        line = lines[0]
        assert line.opdt == "20260221"
        assert line.venue_code == IpatVenueCode.TOKYO
        assert line.race_number == 11
        assert line.bet_type == IpatBetType.TANSYO
        assert line.number == "03"
        assert line.amount == 200

    def test_複勝変換(self):
        proposal = BetProposal(bet_type="place", horse_numbers=[7], amount=100)
        lines = BetToIpatConverter.convert("202602210608", [proposal])
        assert len(lines) == 1
        assert lines[0].bet_type == IpatBetType.FUKUSYO
        assert lines[0].venue_code == IpatVenueCode.NAKAYAMA
        assert lines[0].number == "07"

    def test_ワイド変換(self):
        proposal = BetProposal(bet_type="wide", horse_numbers=[3, 12], amount=100)
        lines = BetToIpatConverter.convert("202602210501", [proposal])
        assert lines[0].bet_type == IpatBetType.WIDE
        assert lines[0].number == "03-12"

    def test_馬連変換(self):
        proposal = BetProposal(bet_type="quinella", horse_numbers=[5, 14], amount=100)
        lines = BetToIpatConverter.convert("202602210501", [proposal])
        assert lines[0].bet_type == IpatBetType.UMAREN
        assert lines[0].number == "05-14"

    def test_馬単変換_順序保持(self):
        proposal = BetProposal(bet_type="exacta", horse_numbers=[7, 3], amount=100)
        lines = BetToIpatConverter.convert("202602210501", [proposal])
        assert lines[0].bet_type == IpatBetType.UMATAN
        assert lines[0].number == "07-03"

    def test_複数買い目の一括変換(self):
        proposals = [
            BetProposal(bet_type="win", horse_numbers=[3], amount=200),
            BetProposal(bet_type="place", horse_numbers=[7], amount=100),
            BetProposal(bet_type="wide", horse_numbers=[3, 7], amount=100),
        ]
        lines = BetToIpatConverter.convert("202602210501", proposals)
        assert len(lines) == 3

    def test_race_idパース_京都(self):
        proposal = BetProposal(bet_type="win", horse_numbers=[1], amount=100)
        lines = BetToIpatConverter.convert("202602210801", [proposal])
        assert lines[0].venue_code == IpatVenueCode.KYOTO
        assert lines[0].race_number == 1
