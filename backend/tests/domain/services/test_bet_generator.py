"""5券種買い目生成のテスト."""
from src.domain.services.bet_generator import (
    BetProposal,
    generate_exacta_bets,
    generate_place_bets,
    generate_quinella_bets,
    generate_wide_bets,
    generate_win_bets,
)


def _make_ranked():
    """Pool ranked: [(horse_number, probability), ...] 確率降順."""
    return [
        (3, 0.25),
        (7, 0.20),
        (1, 0.15),
        (5, 0.12),
        (9, 0.10),
        (2, 0.08),
        (4, 0.05),
        (6, 0.03),
        (8, 0.02),
    ]


def _make_agree_counts():
    """各馬番のソースTop4合意数."""
    return {3: 4, 7: 3, 1: 3, 5: 2, 9: 2, 2: 1, 4: 0, 6: 0, 8: 0}


class TestGenerateWinBets:
    def test_edge範囲内の馬が買い目になる(self):
        combined = {3: 0.25, 7: 0.20, 1: 0.15, 5: 0.12, 9: 0.10, 2: 0.08}
        mkt = {3: 0.21, 7: 0.19, 1: 0.14, 5: 0.13, 9: 0.11, 2: 0.09}
        odds_win = {"3": 4.8, "7": 5.3, "1": 7.1, "5": 7.7, "9": 9.1, "2": 11.1}
        bets = generate_win_bets(combined, mkt, odds_win)
        assert len(bets) > 0
        for b in bets:
            assert b.bet_type == "win"
            assert b.amount >= 100
            assert b.amount % 100 == 0

    def test_edge範囲外はスキップ(self):
        combined = {3: 0.25}
        mkt = {3: 0.24}  # edge = 0.01 < 0.03
        odds_win = {"3": 4.0}
        bets = generate_win_bets(combined, mkt, odds_win)
        assert len(bets) == 0


class TestGeneratePlaceBets:
    def test_Top4_合意2_mid3to8(self):
        ranked = _make_ranked()
        agree = _make_agree_counts()
        odds_place = {
            "3": {"min": 1.1, "max": 2.0},  # mid=1.55 < 3.0 → 除外
            "7": {"min": 2.5, "max": 6.0},  # Top4, 合意3, mid=4.25 → 対象
            "1": {"min": 2.0, "max": 5.0},  # Top4, 合意3, mid=3.5 → 対象
            "5": {"min": 3.0, "max": 7.0},  # Top4, 合意2, mid=5.0 → 対象
            "9": {"min": 4.0, "max": 9.0},  # Top5 → 除外（Top4以内）
        }
        bets = generate_place_bets(ranked, odds_place, agree)
        horse_nums = [b.horse_numbers for b in bets]
        assert [7] in horse_nums
        assert [1] in horse_nums
        assert [5] in horse_nums
        assert [3] not in horse_nums
        assert [9] not in horse_nums
        for b in bets:
            assert b.bet_type == "place"
            assert b.amount == 100


class TestGenerateWideBets:
    def test_Top5_合意2_odds10plus(self):
        ranked = _make_ranked()
        agree = _make_agree_counts()
        odds_wide = {
            "3-7": 8.5,   # odds < 10 → 除外
            "1-3": 12.0,  # 両馬合意2+, odds 12 → 対象
            "3-5": 15.0,  # 5番は合意2, odds 15 → 対象
            "3-9": 20.0,  # 9番は合意2, odds 20 → 対象
            "1-7": 18.0,  # 両馬合意2+, odds 18 → 対象
            "5-7": 22.0,  # 両馬合意2+, odds 22 → 対象
            "1-5": 25.0,  # 両馬合意2+, odds 25 → 対象
            "1-9": 30.0,  # 両馬合意2+, odds 30 → 対象
            "5-9": 35.0,  # 両馬合意2+, odds 35 → 対象
            "7-9": 28.0,  # 両馬合意2+, odds 28 → 対象
            "2-9": 40.0,  # 2番は合意1 → 除外
        }
        bets = generate_wide_bets(ranked, odds_wide, agree)
        # 3-7 は odds < 10 で除外
        assert not any(b.horse_numbers == [3, 7] for b in bets)
        # 2-9 は2番の合意が1 → 除外
        assert not any(2 in b.horse_numbers for b in bets)
        for b in bets:
            assert b.bet_type == "wide"
            assert b.amount == 100
            assert len(b.horse_numbers) == 2


class TestGenerateQuinellaBets:
    def test_Top3_合意3_odds15plus(self):
        ranked = _make_ranked()
        agree = _make_agree_counts()
        odds_quinella = {
            "3-7": 12.0,  # odds < 15 → 除外
            "1-3": 18.0,  # Top3, 両馬合意3+, odds 18 → 対象
            "1-7": 20.0,  # Top3, 両馬合意3+, odds 20 → 対象
        }
        bets = generate_quinella_bets(ranked, odds_quinella, agree)
        assert len(bets) == 2
        assert any(b.horse_numbers == [1, 3] for b in bets)
        assert any(b.horse_numbers == [1, 7] for b in bets)
        assert not any(b.horse_numbers == [3, 7] for b in bets)
        for b in bets:
            assert b.bet_type == "quinella"
            assert b.amount == 100


class TestGenerateExactaBets:
    def test_Top3_合意3_qodds15plus_natural(self):
        ranked = _make_ranked()
        agree = _make_agree_counts()
        odds_quinella = {
            "3-7": 18.0,
            "1-3": 20.0,
            "1-7": 25.0,
        }
        bets = generate_exacta_bets(ranked, odds_quinella, agree)
        assert len(bets) == 3
        # Natural order: Pool上位が1着
        assert any(b.horse_numbers == [3, 7] for b in bets)
        assert any(b.horse_numbers == [3, 1] for b in bets)
        assert any(b.horse_numbers == [7, 1] for b in bets)
        for b in bets:
            assert b.bet_type == "exacta"
            assert b.amount == 100
            assert len(b.horse_numbers) == 2


class TestBetProposal:
    def test_構造(self):
        bp = BetProposal(
            bet_type="win",
            horse_numbers=[3],
            amount=200,
        )
        assert bp.bet_type == "win"
        assert bp.horse_numbers == [3]
        assert bp.amount == 200
