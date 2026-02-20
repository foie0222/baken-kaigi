"""5券種の買い目生成.

バックテスト確定済みのフィルタ条件を完全再現する。
FINDINGS.md の各券種「採用戦略（確定）」セクションが仕様。
"""
from dataclasses import dataclass

# --- 定数（バックテスト確定値） ---
WIN_EDGE_MIN = 0.03
WIN_EDGE_MAX = 0.05
WIN_KELLY_FRACTION = 0.10
WIN_BANKROLL = 100_000
WIN_EDGE_TILT_CENTER = 0.035

PLACE_TOP_N = 4
PLACE_AGREE_MIN = 2
PLACE_MID_LO = 3.0
PLACE_MID_HI = 8.0

WIDE_TOP_N = 5
WIDE_AGREE_MIN = 2
WIDE_ODDS_MIN = 10.0

QUINELLA_TOP_N = 3
QUINELLA_AGREE_MIN = 3
QUINELLA_ODDS_MIN = 15.0

EXACTA_TOP_N = 3
EXACTA_AGREE_MIN = 3
EXACTA_QODDS_MIN = 15.0


@dataclass
class BetProposal:
    """買い目提案."""

    bet_type: str  # "win", "place", "wide", "quinella", "exacta"
    horse_numbers: list[int]  # 単勝/複勝=[n], ワイド/馬連/馬単=[n1, n2]
    amount: int  # 金額（100円単位）


def generate_win_bets(
    combined: dict[int, float],
    mkt: dict[int, float],
    odds_win: dict,
) -> list[BetProposal]:
    """単勝: Edge 0.03-0.05 + Kelly10%×edgeTilt."""
    bets = []
    for hn, est_prob in combined.items():
        mkt_prob = mkt.get(hn, 0)
        edge = est_prob - mkt_prob
        hn_str = str(hn)
        if edge <= WIN_EDGE_MIN or edge > WIN_EDGE_MAX:
            continue
        if hn_str not in odds_win:
            continue
        odds = odds_win[hn_str]["o"]
        if odds <= 1:
            continue
        kelly_frac = (est_prob * odds - 1) / (odds - 1)
        if kelly_frac <= 0:
            continue
        amount = WIN_BANKROLL * kelly_frac * WIN_KELLY_FRACTION * (edge / WIN_EDGE_TILT_CENTER)
        amount = max(100, round(amount / 100) * 100)
        bets.append(BetProposal(bet_type="win", horse_numbers=[hn], amount=amount))
    return bets


def generate_place_bets(
    ranked: list[tuple[int, float]],
    odds_place: dict,
    agree_counts: dict[int, int],
) -> list[BetProposal]:
    """複勝: Pool Top4 + 合意2(src4) + mid 3.0-8.0."""
    bets = []
    top_horses = [h for h, _ in ranked[:PLACE_TOP_N]]
    for hn in top_horses:
        if agree_counts.get(hn, 0) < PLACE_AGREE_MIN:
            continue
        hn_str = str(hn)
        if hn_str not in odds_place:
            continue
        mid = odds_place[hn_str].get("mid", 0)
        if mid < PLACE_MID_LO or mid > PLACE_MID_HI:
            continue
        bets.append(BetProposal(bet_type="place", horse_numbers=[hn], amount=100))
    return bets


def generate_wide_bets(
    ranked: list[tuple[int, float]],
    odds_wide: dict,
    agree_counts: dict[int, int],
) -> list[BetProposal]:
    """ワイド: Pool Top5 + 合意2(src4) + odds 10+."""
    bets = []
    top_horses = [h for h, _ in ranked[:WIDE_TOP_N]]
    for i in range(len(top_horses)):
        for j in range(i + 1, len(top_horses)):
            h1, h2 = top_horses[i], top_horses[j]
            if agree_counts.get(h1, 0) < WIDE_AGREE_MIN:
                continue
            if agree_counts.get(h2, 0) < WIDE_AGREE_MIN:
                continue
            key = f"{min(h1, h2)}-{max(h1, h2)}"
            if key not in odds_wide:
                continue
            odds = odds_wide[key]
            if odds < WIDE_ODDS_MIN:
                continue
            bets.append(
                BetProposal(
                    bet_type="wide",
                    horse_numbers=sorted([h1, h2]),
                    amount=100,
                )
            )
    return bets


def generate_quinella_bets(
    ranked: list[tuple[int, float]],
    odds_quinella: dict,
    agree_counts: dict[int, int],
) -> list[BetProposal]:
    """馬連: Pool Top3 + 合意3(src4) + odds 15+."""
    bets = []
    top_horses = [h for h, _ in ranked[:QUINELLA_TOP_N]]
    for i in range(len(top_horses)):
        for j in range(i + 1, len(top_horses)):
            h1, h2 = top_horses[i], top_horses[j]
            if agree_counts.get(h1, 0) < QUINELLA_AGREE_MIN:
                continue
            if agree_counts.get(h2, 0) < QUINELLA_AGREE_MIN:
                continue
            key = f"{min(h1, h2)}-{max(h1, h2)}"
            if key not in odds_quinella:
                continue
            odds = odds_quinella[key]
            if odds < QUINELLA_ODDS_MIN:
                continue
            bets.append(
                BetProposal(
                    bet_type="quinella",
                    horse_numbers=sorted([h1, h2]),
                    amount=100,
                )
            )
    return bets


def generate_exacta_bets(
    ranked: list[tuple[int, float]],
    odds_quinella: dict,
    agree_counts: dict[int, int],
) -> list[BetProposal]:
    """馬単: Pool Top3 + 合意3(src4) + qodds 15+ + Natural order."""
    bets = []
    top_horses = [h for h, _ in ranked[:EXACTA_TOP_N]]
    for i in range(len(top_horses)):
        for j in range(i + 1, len(top_horses)):
            h1, h2 = top_horses[i], top_horses[j]  # h1がPool上位
            if agree_counts.get(h1, 0) < EXACTA_AGREE_MIN:
                continue
            if agree_counts.get(h2, 0) < EXACTA_AGREE_MIN:
                continue
            key = f"{min(h1, h2)}-{max(h1, h2)}"
            if key not in odds_quinella:
                continue
            odds = odds_quinella[key]
            if odds < EXACTA_QODDS_MIN:
                continue
            # Natural order: Pool上位 (h1) が1着
            bets.append(
                BetProposal(
                    bet_type="exacta",
                    horse_numbers=[h1, h2],  # 順序あり: 1着, 2着
                    amount=100,
                )
            )
    return bets
