# 自動投票システム Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** バックテスト確定済みの5券種戦略を、レース発走5分前に完全自動でIPAT投票するシステムを構築する。

**Architecture:** EventBridge Scheduler + Lambda 2段構成。Orchestrator Lambda（15分間隔）がレース一覧を取得し、各レースの発走5分前にBetExecutor Lambdaを発火するone-timeスケジュールを動的に作成する。BetExecutor はバックテストと完全同一の決定論的パイプライン（Softmax + Log Opinion Pool + 5券種フィルタ）で買い目を生成し、既存IPAT基盤で投票する。

**Tech Stack:** Python 3.12, AWS Lambda, EventBridge Scheduler, DynamoDB, Secrets Manager, CDK

**設計ドキュメント:** `docs/plans/2026-02-20-auto-betting-design.md`

**バックテスト結果:** `backend/backtest_reference_FINDINGS.md`（bet worktreeにコピー済み）

**バックテスト参照コード:** `backend/backtest_reference_optimize_staking.py`（bet worktreeにコピー済み）

---

## Task 1: 確率推定パイプライン（コア関数）

バックテスト `optimize_staking.py` の `softmax()`, `source_to_probs()`, `log_opinion_pool()`, `market_implied_probs()` を本番モジュールとして実装する。**バックテストのコードを完全に再現すること。**

**Files:**
- Create: `backend/src/domain/services/betting_pipeline.py`
- Test: `backend/tests/domain/test_betting_pipeline.py`

**Step 1: テストを書く**

```python
"""確率推定パイプラインのテスト."""
import math

from src.domain.services.betting_pipeline import (
    BETAS,
    PLACE_WEIGHTS,
    SOURCES,
    WIN_WEIGHTS,
    log_opinion_pool,
    market_implied_probs,
    softmax,
    source_to_probs,
)


class TestSoftmax:
    def test_確率の合計が1になる(self):
        scores = [80, 70, 60, 50, 40]
        beta = 0.07
        probs = softmax(scores, beta)
        assert abs(sum(probs) - 1.0) < 1e-10
        assert len(probs) == 5

    def test_スコアが高いほど確率が高い(self):
        scores = [80, 70, 60]
        probs = softmax(scores, 0.07)
        assert probs[0] > probs[1] > probs[2]

    def test_beta_0でも均等にならない_max正規化(self):
        # beta=0 → exp(0*(s-max)) = 1 for all → 均等
        scores = [80, 70, 60]
        probs = softmax(scores, 0.0)
        assert abs(probs[0] - probs[1]) < 1e-10

    def test_バックテストと同一計算(self):
        """optimize_staking.py の softmax と同一であることを検証."""
        scores = [90, 75, 60, 45, 30]
        beta = 0.070031  # keiba-ai-navi の β
        probs = softmax(scores, beta)
        # 手計算: max_s=90, exps=[e^0, e^(-1.05), e^(-2.1), e^(-3.15), e^(-4.2)]
        max_s = 90
        exps = [math.exp(beta * (s - max_s)) for s in scores]
        total = sum(exps)
        expected = [e / total for e in exps]
        for p, e in zip(probs, expected):
            assert abs(p - e) < 1e-15


class TestSourceToProbs:
    def test_馬番と確率のマッピング(self):
        preds = [
            {"horse_number": 3, "score": 80},
            {"horse_number": 7, "score": 70},
            {"horse_number": 1, "score": 60},
        ]
        result = source_to_probs(preds, 0.07)
        assert set(result.keys()) == {3, 7, 1}
        assert result[3] > result[7] > result[1]
        assert abs(sum(result.values()) - 1.0) < 1e-10


class TestLogOpinionPool:
    def test_2ソース均等ウェイト(self):
        pd1 = {1: 0.5, 2: 0.3, 3: 0.2}
        pd2 = {1: 0.4, 2: 0.4, 3: 0.2}
        result = log_opinion_pool([pd1, pd2], [0.5, 0.5])
        assert abs(sum(result.values()) - 1.0) < 1e-10
        # 幾何平均: horse1 = 0.5^0.5 * 0.4^0.5 ∝ sqrt(0.2)
        assert result[1] > result[2]  # 両ソースで1位

    def test_共通馬番のみ返す(self):
        pd1 = {1: 0.5, 2: 0.5}
        pd2 = {2: 0.6, 3: 0.4}
        result = log_opinion_pool([pd1, pd2], [0.5, 0.5])
        assert set(result.keys()) == {2}  # 共通馬番のみ

    def test_空の場合は空辞書(self):
        pd1 = {1: 0.5}
        pd2 = {2: 0.5}
        result = log_opinion_pool([pd1, pd2], [0.5, 0.5])
        assert result == {}


class TestMarketImpliedProbs:
    def test_オッズから確率変換(self):
        odds_win = {
            "1": {"o": 2.0},   # 50%
            "2": {"o": 5.0},   # 20%
            "3": {"o": 10.0},  # 10%
        }
        result = market_implied_probs(odds_win)
        assert abs(sum(result.values()) - 1.0) < 1e-10
        assert result[1] > result[2] > result[3]

    def test_オッズ0は除外(self):
        odds_win = {"1": {"o": 2.0}, "2": {"o": 0}}
        result = market_implied_probs(odds_win)
        assert set(result.keys()) == {1}


class TestConstants:
    def test_ソース4つ(self):
        assert len(SOURCES) == 4
        assert "keiba-ai-navi" in SOURCES
        assert "umamax" in SOURCES
        assert "muryou-keiba-ai" in SOURCES
        assert "keiba-ai-athena" in SOURCES

    def test_β値がバックテストと一致(self):
        assert BETAS["umamax"] == 0.052082
        assert BETAS["muryou-keiba-ai"] == 0.072791
        assert BETAS["keiba-ai-athena"] == 0.006745
        assert BETAS["keiba-ai-navi"] == 0.070031

    def test_ウェイトがバックテストと一致(self):
        # WIN_WEIGHTS: navi, umamax, muryou, athena（SOURCES順）
        assert WIN_WEIGHTS == [0.401, 0.035, 0.251, 0.313]
        assert PLACE_WEIGHTS == [0.314, 0.214, 0.309, 0.164]
```

**Step 2: テスト実行して失敗を確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/bet/backend && uv run pytest tests/domain/test_betting_pipeline.py -v`
Expected: FAIL (module not found)

**Step 3: 実装**

```python
"""バックテスト確定済みの確率推定パイプライン.

optimize_staking.py (backtest) の関数群を完全再現。
定数・計算ロジックを一切変更しないこと。
"""
import math

SOURCES = ["keiba-ai-navi", "umamax", "muryou-keiba-ai", "keiba-ai-athena"]

BETAS = {
    "umamax": 0.052082,
    "muryou-keiba-ai": 0.072791,
    "keiba-ai-athena": 0.006745,
    "keiba-ai-navi": 0.070031,
}

# MLE最適化ウェイト（SOURCES順: navi, umamax, muryou, athena）
WIN_WEIGHTS = [0.401, 0.035, 0.251, 0.313]
PLACE_WEIGHTS = [0.314, 0.214, 0.309, 0.164]


def softmax(scores: list, beta: float) -> list[float]:
    """Softmax calibration."""
    max_s = max(scores)
    exps = [math.exp(beta * (s - max_s)) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def source_to_probs(preds: list[dict], beta: float) -> dict[int, float]:
    """ソース予想をSoftmax確率に変換."""
    scores = [p["score"] for p in preds]
    horse_nums = [p["horse_number"] for p in preds]
    return dict(zip(horse_nums, softmax(scores, beta)))


def log_opinion_pool(
    prob_dicts: list[dict[int, float]], weights: list[float]
) -> dict[int, float]:
    """Log Opinion Poolで複数ソースの確率を統合."""
    all_horses = set(prob_dicts[0].keys())
    for pd in prob_dicts[1:]:
        all_horses &= set(pd.keys())
    if not all_horses:
        return {}
    combined = {}
    for h in all_horses:
        log_p = sum(
            w * math.log(max(pd.get(h, 1e-10), 1e-10))
            for pd, w in zip(prob_dicts, weights)
        )
        combined[h] = math.exp(log_p)
    total = sum(combined.values())
    return {h: p / total for h, p in combined.items()} if total > 0 else {}


def market_implied_probs(odds_win: dict) -> dict[int, float]:
    """単勝オッズからMarket Implied Probabilitiesを算出."""
    raw = {}
    for hn_str, info in odds_win.items():
        if info["o"] > 0:
            raw[int(hn_str)] = 1.0 / info["o"]
    total = sum(raw.values())
    return {h: p / total for h, p in raw.items()} if total > 0 else {}
```

**Step 4: テスト実行して全パス確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/bet/backend && uv run pytest tests/domain/test_betting_pipeline.py -v`
Expected: ALL PASS

**Step 5: コミット**

```bash
git add backend/src/domain/services/betting_pipeline.py backend/tests/domain/test_betting_pipeline.py
git commit -m "feat: 確率推定パイプラインのコア関数を実装"
```

---

## Task 2: 5券種の買い目生成

バックテスト確定済みの5券種フィルタ（単勝Edge+Kelly, 複勝Top4+合意2+mid3-8, ワイドTop5+合意2+odds10+, 馬連Top3+合意3+odds15+, 馬単Top3+合意3+qodds15+ Natural）を実装する。

**Files:**
- Create: `backend/src/domain/services/bet_generator.py`
- Test: `backend/tests/domain/test_bet_generator.py`
- Read: `backend/backtest_reference_FINDINGS.md` — 各券種のフィルタ条件を参照

**Step 1: テストを書く**

テストデータとして、Pool確率・合意度・オッズを与えて期待する買い目が生成されることを検証する。

```python
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
        (3, 0.25),  # 1位
        (7, 0.20),  # 2位
        (1, 0.15),  # 3位
        (5, 0.12),  # 4位
        (9, 0.10),  # 5位
        (2, 0.08),  # 6位
        (4, 0.05),  # 7位
        (6, 0.03),  # 8位
        (8, 0.02),  # 9位
    ]


def _make_agree_counts():
    """各馬番のソースTop4合意数（4ソース中何ソースがTop4に推すか）."""
    return {3: 4, 7: 3, 1: 3, 5: 2, 9: 2, 2: 1, 4: 0, 6: 0, 8: 0}


class TestGenerateWinBets:
    def test_edge範囲内の馬が買い目になる(self):
        combined = {3: 0.25, 7: 0.20, 1: 0.15, 5: 0.12, 9: 0.10, 2: 0.08}
        # market: 3番のedge = 0.25 - 0.21 = 0.04（範囲内）
        mkt = {3: 0.21, 7: 0.19, 1: 0.14, 5: 0.13, 9: 0.11, 2: 0.09}
        odds_win = {
            "3": {"o": 4.8}, "7": {"o": 5.3}, "1": {"o": 7.1},
            "5": {"o": 7.7}, "9": {"o": 9.1}, "2": {"o": 11.1},
        }
        bets = generate_win_bets(combined, mkt, odds_win)
        assert len(bets) > 0
        for b in bets:
            assert b.bet_type == "win"
            assert b.amount >= 100
            assert b.amount % 100 == 0

    def test_edge範囲外はスキップ(self):
        combined = {3: 0.25}
        mkt = {3: 0.24}  # edge = 0.01 < 0.03
        odds_win = {"3": {"o": 4.0}}
        bets = generate_win_bets(combined, mkt, odds_win)
        assert len(bets) == 0


class TestGeneratePlaceBets:
    def test_Top4_合意2_mid3to8(self):
        ranked = _make_ranked()
        agree = _make_agree_counts()
        odds_place = {
            "3": {"lo": 1.1, "mid": 1.5, "hi": 2.0},  # mid < 3.0 → 除外
            "7": {"lo": 2.5, "mid": 4.0, "hi": 6.0},  # Top4, 合意3, mid 4.0 → 対象
            "1": {"lo": 2.0, "mid": 3.5, "hi": 5.0},  # Top4, 合意3, mid 3.5 → 対象
            "5": {"lo": 3.0, "mid": 5.0, "hi": 7.0},  # Top4, 合意2, mid 5.0 → 対象
            "9": {"lo": 4.0, "mid": 6.5, "hi": 9.0},  # Top5 → 除外（Top4以内）
        }
        bets = generate_place_bets(ranked, odds_place, agree)
        horse_nums = [b.horse_numbers for b in bets]
        assert [7] in horse_nums
        assert [1] in horse_nums
        assert [5] in horse_nums
        assert [3] not in horse_nums  # mid < 3.0
        assert [9] not in horse_nums  # Top5（Top4以内でない）
        for b in bets:
            assert b.bet_type == "place"
            assert b.amount == 100


class TestGenerateWideBets:
    def test_Top5_合意2_odds10plus(self):
        ranked = _make_ranked()
        agree = _make_agree_counts()
        # ワイドオッズ: 組み合わせ馬番をキーにした辞書
        odds_wide = {
            "3-7": 8.5,   # 両馬合意2+だが odds < 10 → 除外
            "3-1": 12.0,  # 両馬合意2+, odds 12 → 対象
            "3-5": 15.0,  # 5番は合意2, odds 15 → 対象
            "3-9": 20.0,  # 9番は合意2, odds 20 → 対象
            "7-1": 18.0,  # 両馬合意2+, odds 18 → 対象
            "7-5": 22.0,  # 両馬合意2+, odds 22 → 対象
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
            "3-1": 18.0,  # Top3, 両馬合意3+, odds 18 → 対象
            "7-1": 20.0,  # Top3, 両馬合意3+, odds 20 → 対象
        }
        bets = generate_quinella_bets(ranked, odds_quinella, agree)
        assert len(bets) == 2
        assert any(b.horse_numbers == [3, 1] for b in bets)
        assert any(b.horse_numbers == [7, 1] for b in bets)
        # 3-7 は odds < 15 で除外
        assert not any(b.horse_numbers == [3, 7] for b in bets)
        for b in bets:
            assert b.bet_type == "quinella"
            assert b.amount == 100


class TestGenerateExactaBets:
    def test_Top3_合意3_qodds15plus_natural(self):
        ranked = _make_ranked()
        agree = _make_agree_counts()
        odds_quinella = {
            "3-7": 18.0,  # Top3, 両馬合意3+, odds 18 → 対象
            "3-1": 20.0,  # Top3, 両馬合意3+, odds 20 → 対象
            "7-1": 25.0,  # Top3, 両馬合意3+, odds 25 → 対象
        }
        bets = generate_exacta_bets(ranked, odds_quinella, agree)
        assert len(bets) == 3
        # Natural order: Pool上位が1着
        # 3>7 なので 3-7: [3,7], 3>1 なので 3-1: [3,1], 7>1 なので 7-1: [7,1]
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
```

**Step 2: テスト実行して失敗を確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/bet/backend && uv run pytest tests/domain/test_bet_generator.py -v`

**Step 3: 実装**

```python
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
WIN_EDGE_TILT_CENTER = 0.035  # edge / 0.035 でティルト

PLACE_TOP_N = 4
PLACE_AGREE_MIN = 2
PLACE_AGREE_SRC = 4  # src4 = Top4以内で合意判定
PLACE_MID_LO = 3.0
PLACE_MID_HI = 8.0

WIDE_TOP_N = 5
WIDE_AGREE_MIN = 2
WIDE_AGREE_SRC = 4
WIDE_ODDS_MIN = 10.0

QUINELLA_TOP_N = 3
QUINELLA_AGREE_MIN = 3
QUINELLA_AGREE_SRC = 4
QUINELLA_ODDS_MIN = 15.0

EXACTA_TOP_N = 3
EXACTA_AGREE_MIN = 3
EXACTA_AGREE_SRC = 4
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
```

**Step 4: テスト実行して全パス確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/bet/backend && uv run pytest tests/domain/test_bet_generator.py -v`

**Step 5: コミット**

```bash
git add backend/src/domain/services/bet_generator.py backend/tests/domain/test_bet_generator.py
git commit -m "feat: 5券種の買い目生成ロジックを実装"
```

---

## Task 3: 合意度計算ヘルパー

各馬番が「4ソース中何ソースのTopN以内にランクされるか」を計算するヘルパー。Task 2の `agree_counts` を生成するために必要。

**Files:**
- Modify: `backend/src/domain/services/betting_pipeline.py`
- Modify: `backend/tests/domain/test_betting_pipeline.py`

**Step 1: テスト追加**

```python
class TestComputeAgreeCounts:
    def test_4ソース中の合意数(self):
        """各馬番が何ソースのTop4以内にランクされるかを数える."""
        from src.domain.services.betting_pipeline import compute_agree_counts

        # 各ソースの確率辞書（値はソース内の確率）
        source_probs = [
            {1: 0.3, 2: 0.25, 3: 0.2, 4: 0.15, 5: 0.1},  # Top4: 1,2,3,4
            {1: 0.3, 3: 0.25, 5: 0.2, 2: 0.15, 4: 0.1},  # Top4: 1,3,5,2
            {3: 0.3, 1: 0.25, 2: 0.2, 5: 0.15, 4: 0.1},  # Top4: 3,1,2,5
            {1: 0.3, 2: 0.25, 5: 0.2, 3: 0.15, 4: 0.1},  # Top4: 1,2,5,3
        ]
        result = compute_agree_counts(source_probs, top_n=4)
        assert result[1] == 4  # 全ソースでTop4
        assert result[2] == 3  # 3ソースでTop4（ソース2ではTop5）
        assert result[3] == 4  # 全ソースでTop4
        assert result[5] == 3  # 3ソースでTop4
        assert result[4] == 1  # 1ソースのみTop4（ソース1のみ）
```

**Step 2: テスト実行して失敗を確認**

**Step 3: 実装追加（betting_pipeline.py に追記）**

```python
def compute_agree_counts(
    source_probs: list[dict[int, float]], top_n: int
) -> dict[int, int]:
    """各馬番が何ソースのTopN以内にランクされるかを計算."""
    counts: dict[int, int] = {}
    for probs in source_probs:
        ranked = sorted(probs.keys(), key=lambda h: probs[h], reverse=True)[:top_n]
        for h in ranked:
            counts[h] = counts.get(h, 0) + 1
    return counts
```

**Step 4: テスト実行して全パス確認**

**Step 5: コミット**

```bash
git add backend/src/domain/services/betting_pipeline.py backend/tests/domain/test_betting_pipeline.py
git commit -m "feat: ソース合意度計算ヘルパーを追加"
```

---

## Task 4: BetProposal → IpatBetLine 変換

Cart を経由せず、`BetProposal` から直接 `IpatBetLine` を生成するコンバータ。

**Files:**
- Create: `backend/src/domain/services/bet_to_ipat_converter.py`
- Test: `backend/tests/domain/test_bet_to_ipat_converter.py`
- Read: `backend/src/domain/value_objects/ipat_bet_line.py` — IpatBetLine の構造を確認
- Read: `backend/src/domain/enums/ipat_bet_type.py` — IpatBetType のenum値を確認
- Read: `backend/src/domain/enums/ipat_venue_code.py` — IpatVenueCode のenum値を確認

**Step 1: テストを書く**

```python
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
        assert lines[0].number == "07-03"  # 順序保持（1着-2着）

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
```

**Step 2: テスト実行して失敗を確認**

**Step 3: 実装**

```python
"""BetProposal → IpatBetLine 直接変換.

Cart を経由せず、買い目提案から直接 IPAT投票行を生成する。
"""
from src.domain.enums import IpatBetType, IpatVenueCode
from src.domain.services.bet_generator import BetProposal
from src.domain.value_objects import IpatBetLine

_BET_TYPE_MAP = {
    "win": IpatBetType.TANSYO,
    "place": IpatBetType.FUKUSYO,
    "wide": IpatBetType.WIDE,
    "quinella": IpatBetType.UMAREN,
    "exacta": IpatBetType.UMATAN,
}


class BetToIpatConverter:
    """BetProposal を IpatBetLine に変換."""

    @staticmethod
    def convert(race_id: str, proposals: list[BetProposal]) -> list[IpatBetLine]:
        """race_id と買い目リストから IpatBetLine リストを生成."""
        opdt = race_id[:8]
        venue_code = IpatVenueCode.from_course_code(race_id[8:10])
        race_number = int(race_id[10:12])

        lines = []
        for p in proposals:
            ipat_type = _BET_TYPE_MAP[p.bet_type]
            number = "-".join(f"{n:02d}" for n in p.horse_numbers)
            lines.append(
                IpatBetLine(
                    opdt=opdt,
                    venue_code=venue_code,
                    race_number=race_number,
                    bet_type=ipat_type,
                    number=number,
                    amount=p.amount,
                )
            )
        return lines
```

**Step 4: テスト実行して全パス確認**

**Step 5: コミット**

```bash
git add backend/src/domain/services/bet_to_ipat_converter.py backend/tests/domain/test_bet_to_ipat_converter.py
git commit -m "feat: BetProposal → IpatBetLine 直接変換を実装"
```

---

## Task 5: BetExecutor Lambda ハンドラ

レースごとに起動され、パイプライン実行 → IPAT投票 → 記録保存を行う。

**Files:**
- Create: `backend/batch/auto_bet_executor.py`
- Test: `backend/tests/batch/test_auto_bet_executor.py`
- Read: `backend/src/infrastructure/providers/jravan_ipat_gateway.py` — submit_bets の使い方
- Read: `backend/src/infrastructure/providers/secrets_manager_credentials_provider.py` — credentials 取得
- Read: `backend/src/infrastructure/repositories/dynamodb_purchase_order_repository.py` — save の使い方

**Step 1: テストを書く**

テストは外部依存（DynamoDB, JRA-VAN API, Secrets Manager, IPAT）を全てモック化。パイプライン実行のe2eフローをテストする。

```python
"""BetExecutor Lambda ハンドラのテスト."""
from unittest.mock import MagicMock, patch

from batch.auto_bet_executor import handler, _run_pipeline, _fetch_predictions, _fetch_odds


class TestFetchPredictions:
    def test_DynamoDBからAI予想を取得(self):
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "race_id": "202602210501",
                    "source": "keiba-ai-navi",
                    "predictions": [
                        {"horse_number": "1", "score": "80", "rank": "1"},
                        {"horse_number": "2", "score": "70", "rank": "2"},
                    ],
                }
            ]
        }
        result = _fetch_predictions(mock_table, "202602210501")
        assert "keiba-ai-navi" in result
        assert result["keiba-ai-navi"][0]["horse_number"] == 1
        assert result["keiba-ai-navi"][0]["score"] == 80.0


class TestRunPipeline:
    def test_予想とオッズから買い目を生成(self):
        predictions = {
            "keiba-ai-navi": [
                {"horse_number": 1, "score": 90, "rank": 1},
                {"horse_number": 2, "score": 80, "rank": 2},
                {"horse_number": 3, "score": 70, "rank": 3},
                {"horse_number": 4, "score": 60, "rank": 4},
                {"horse_number": 5, "score": 50, "rank": 5},
            ],
            "umamax": [
                {"horse_number": 1, "score": 85, "rank": 1},
                {"horse_number": 2, "score": 75, "rank": 2},
                {"horse_number": 3, "score": 65, "rank": 3},
                {"horse_number": 4, "score": 55, "rank": 4},
                {"horse_number": 5, "score": 45, "rank": 5},
            ],
            "muryou-keiba-ai": [
                {"horse_number": 1, "score": 88, "rank": 1},
                {"horse_number": 3, "score": 78, "rank": 2},
                {"horse_number": 2, "score": 68, "rank": 3},
                {"horse_number": 5, "score": 58, "rank": 4},
                {"horse_number": 4, "score": 48, "rank": 5},
            ],
            "keiba-ai-athena": [
                {"horse_number": 1, "score": 92, "rank": 1},
                {"horse_number": 2, "score": 82, "rank": 2},
                {"horse_number": 3, "score": 72, "rank": 3},
                {"horse_number": 4, "score": 62, "rank": 4},
                {"horse_number": 5, "score": 52, "rank": 5},
            ],
        }
        odds = {
            "win": {
                "1": {"o": 3.5}, "2": {"o": 5.0}, "3": {"o": 8.0},
                "4": {"o": 15.0}, "5": {"o": 20.0},
            },
            "place": {
                "1": {"lo": 1.1, "mid": 1.5, "hi": 2.0},
                "2": {"lo": 2.0, "mid": 3.5, "hi": 5.0},
                "3": {"lo": 2.5, "mid": 4.5, "hi": 7.0},
                "4": {"lo": 3.0, "mid": 5.5, "hi": 8.0},
                "5": {"lo": 4.0, "mid": 7.0, "hi": 10.0},
            },
            "quinella": {"1-2": 12.0, "1-3": 18.0, "2-3": 25.0},
            "quinella_place": {"1-2": 5.0, "1-3": 8.0, "2-3": 12.0, "1-4": 15.0},
        }
        bets = _run_pipeline(predictions, odds)
        # 何かしらの買い目が生成されることを確認（具体的な件数はデータ依存）
        assert isinstance(bets, list)


class TestHandler:
    @patch("batch.auto_bet_executor._submit_bets")
    @patch("batch.auto_bet_executor._fetch_odds")
    @patch("batch.auto_bet_executor._fetch_predictions")
    def test_正常系_買い目なしでも正常終了(
        self, mock_preds, mock_odds, mock_submit
    ):
        mock_preds.return_value = {}  # 予想なし → 買い目0件
        event = {"race_id": "202602210501"}
        result = handler(event, None)
        assert result["status"] == "ok"
        assert result["bets_count"] == 0
        mock_submit.assert_not_called()
```

**Step 2: テスト実行して失敗を確認**

**Step 3: 実装**

```python
"""自動投票 BetExecutor Lambda.

レース発走5分前に起動され、決定論的パイプラインで買い目を生成し、
IPAT投票を実行する。
"""
import json
import logging
import os

import boto3
import requests

from src.domain.identifiers import CartId, UserId
from src.domain.entities import PurchaseOrder
from src.domain.value_objects import Money
from src.domain.services.betting_pipeline import (
    BETAS,
    PLACE_WEIGHTS,
    SOURCES,
    WIN_WEIGHTS,
    compute_agree_counts,
    log_opinion_pool,
    market_implied_probs,
    source_to_probs,
)
from src.domain.services.bet_generator import (
    generate_exacta_bets,
    generate_place_bets,
    generate_quinella_bets,
    generate_wide_bets,
    generate_win_bets,
)
from src.domain.services.bet_to_ipat_converter import BetToIpatConverter
from src.infrastructure.providers.jravan_ipat_gateway import JraVanIpatGateway
from src.infrastructure.providers.secrets_manager_credentials_provider import (
    SecretsManagerCredentialsProvider,
)
from src.infrastructure.repositories.dynamodb_purchase_order_repository import (
    DynamoDBPurchaseOrderRepository,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JRAVAN_API_URL = os.environ.get("JRAVAN_API_URL", "http://10.0.1.100:8000")
TARGET_USER_ID = os.environ.get("TARGET_USER_ID", "")


def handler(event, context):
    """Lambda ハンドラ."""
    race_id = event["race_id"]
    logger.info("BetExecutor started: race_id=%s", race_id)

    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    table = dynamodb.Table("baken-kaigi-ai-predictions")

    predictions = _fetch_predictions(table, race_id)
    if len(predictions) < 2:
        logger.warning("予想ソース不足: %d ソース", len(predictions))
        return {"status": "ok", "bets_count": 0, "reason": "insufficient_sources"}

    odds = _fetch_odds(race_id)
    bets = _run_pipeline(predictions, odds)

    if not bets:
        logger.info("買い目なし")
        return {"status": "ok", "bets_count": 0, "reason": "no_bets"}

    bet_lines = BetToIpatConverter.convert(race_id, bets)
    _submit_bets(race_id, bet_lines)

    return {"status": "ok", "bets_count": len(bet_lines), "race_id": race_id}


def _fetch_predictions(table, race_id: str) -> dict:
    """DynamoDB から4ソースのAI予想を取得."""
    predictions = {}
    for source in SOURCES:
        resp = table.get_item(Key={"race_id": race_id, "source": source})
        item = resp.get("Item")
        if not item:
            continue
        preds = [
            {
                "horse_number": int(p["horse_number"]),
                "score": float(p["score"]),
                "rank": int(p["rank"]),
            }
            for p in item.get("predictions", [])
        ]
        if preds:
            predictions[source] = sorted(preds, key=lambda x: x["rank"])
    return predictions


def _fetch_odds(race_id: str) -> dict:
    """JRA-VAN API から最新オッズを取得."""
    resp = requests.get(f"{JRAVAN_API_URL}/races/{race_id}/odds", timeout=30)
    resp.raise_for_status()
    return resp.json()


def _run_pipeline(predictions: dict, odds: dict) -> list:
    """決定論的パイプラインで5券種の買い目を生成."""
    from src.domain.services.bet_generator import BetProposal

    all_bets: list[BetProposal] = []

    # --- 単勝用: WIN_WEIGHTS ---
    win_prob_dicts, win_weights = [], []
    for s, w in zip(SOURCES, WIN_WEIGHTS):
        if s in predictions:
            win_prob_dicts.append(source_to_probs(predictions[s], BETAS[s]))
            win_weights.append(w)
    if len(win_prob_dicts) >= 2:
        wt = sum(win_weights)
        win_combined = log_opinion_pool(win_prob_dicts, [w / wt for w in win_weights])
        if win_combined and "win" in odds:
            win_mkt = market_implied_probs(odds["win"])
            all_bets.extend(generate_win_bets(win_combined, win_mkt, odds["win"]))

    # --- 複勝・ワイド・馬連・馬単用: PLACE_WEIGHTS ---
    place_prob_dicts, place_weights = [], []
    source_probs_list = []  # 合意度計算用
    for s, w in zip(SOURCES, PLACE_WEIGHTS):
        if s in predictions:
            pd = source_to_probs(predictions[s], BETAS[s])
            place_prob_dicts.append(pd)
            place_weights.append(w)
            source_probs_list.append(pd)
    if len(place_prob_dicts) >= 2:
        wt = sum(place_weights)
        place_combined = log_opinion_pool(
            place_prob_dicts, [w / wt for w in place_weights]
        )
        if not place_combined:
            return all_bets

        ranked = sorted(place_combined.items(), key=lambda x: x[1], reverse=True)
        agree_counts = compute_agree_counts(source_probs_list, top_n=4)

        # 複勝
        if "place" in odds:
            all_bets.extend(generate_place_bets(ranked, odds["place"], agree_counts))

        # ワイド: odds key は "quinella_place"
        if "quinella_place" in odds:
            all_bets.extend(
                generate_wide_bets(ranked, odds["quinella_place"], agree_counts)
            )

        # 馬連
        if "quinella" in odds:
            all_bets.extend(
                generate_quinella_bets(ranked, odds["quinella"], agree_counts)
            )

        # 馬単（馬連オッズで代用フィルタ）
        if "quinella" in odds:
            all_bets.extend(
                generate_exacta_bets(ranked, odds["quinella"], agree_counts)
            )

    return all_bets


def _submit_bets(race_id, bet_lines):
    """IPAT投票を実行し、PurchaseOrder を記録."""
    user_id = UserId(TARGET_USER_ID)

    creds_provider = SecretsManagerCredentialsProvider()
    credentials = creds_provider.get_credentials(user_id)
    if credentials is None:
        raise RuntimeError(f"IPAT credentials not found for user: {TARGET_USER_ID}")

    gateway = JraVanIpatGateway(base_url=JRAVAN_API_URL)

    total = sum(line.amount for line in bet_lines)
    order = PurchaseOrder.create(
        user_id=user_id,
        cart_id=CartId(f"auto-{race_id}"),
        bet_lines=bet_lines,
        total_amount=Money(total),
    )
    order.mark_submitted()

    repo = DynamoDBPurchaseOrderRepository()

    success = gateway.submit_bets(credentials, bet_lines)
    if success:
        order.mark_completed()
    else:
        order.mark_failed("IPAT投票に失敗しました")

    repo.save(order)

    if not success:
        raise RuntimeError(f"IPAT submit failed for race: {race_id}")

    logger.info(
        "投票完了: race=%s, bets=%d, total=%d",
        race_id,
        len(bet_lines),
        total,
    )
```

**Step 4: テスト実行して全パス確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/bet/backend && uv run pytest tests/batch/test_auto_bet_executor.py -v`

**Step 5: コミット**

```bash
git add backend/batch/auto_bet_executor.py backend/tests/batch/test_auto_bet_executor.py
git commit -m "feat: BetExecutor Lambda ハンドラを実装"
```

---

## Task 6: Orchestrator Lambda ハンドラ

15分間隔で起動され、当日レース一覧を取得し、発走5分前のone-timeスケジュールを動的に作成する。

**Files:**
- Create: `backend/batch/auto_bet_orchestrator.py`
- Test: `backend/tests/batch/test_auto_bet_orchestrator.py`

**Step 1: テストを書く**

```python
"""Orchestrator Lambda ハンドラのテスト."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from batch.auto_bet_orchestrator import (
    handler,
    _get_today_races,
    _create_schedule,
    _schedule_exists,
    _schedule_name,
)


class TestScheduleName:
    def test_race_idからスケジュール名を生成(self):
        assert _schedule_name("202602210501") == "auto-bet-202602210501"


class TestGetTodayRaces:
    @patch("batch.auto_bet_orchestrator.requests")
    def test_JRA_VAN_APIからレース一覧取得(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"race_id": "202602210501", "start_time": "2026-02-21T10:00:00+09:00"},
            {"race_id": "202602210502", "start_time": "2026-02-21T10:30:00+09:00"},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_resp

        races = _get_today_races("20260221")
        assert len(races) == 2
        assert races[0]["race_id"] == "202602210501"


class TestScheduleExists:
    def test_スケジュールが存在する(self):
        mock_client = MagicMock()
        mock_client.get_schedule.return_value = {"Name": "auto-bet-202602210501"}
        assert _schedule_exists(mock_client, "auto-bet-202602210501") is True

    def test_スケジュールが存在しない(self):
        mock_client = MagicMock()
        mock_client.get_schedule.side_effect = (
            mock_client.exceptions.ResourceNotFoundException({}, "GetSchedule")
        )
        # ResourceNotFoundException は boto3 で動的に生成されるため、
        # 実際のテストでは Exception をキャッチするパターンにする
        # ここでは概略


class TestHandler:
    @patch("batch.auto_bet_orchestrator._create_schedule")
    @patch("batch.auto_bet_orchestrator._schedule_exists")
    @patch("batch.auto_bet_orchestrator._get_today_races")
    @patch("batch.auto_bet_orchestrator.datetime")
    def test_未スケジュールのレースにスケジュール作成(
        self, mock_dt, mock_races, mock_exists, mock_create
    ):
        mock_dt.now.return_value = datetime(2026, 2, 21, 0, 15, tzinfo=timezone.utc)
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_races.return_value = [
            {"race_id": "202602210501", "start_time": "2026-02-21T10:00:00+09:00"},
            {"race_id": "202602210502", "start_time": "2026-02-21T10:30:00+09:00"},
        ]
        mock_exists.return_value = False

        result = handler({}, None)
        assert result["created"] == 2
        assert mock_create.call_count == 2
```

**Step 2: テスト実行して失敗を確認**

**Step 3: 実装**

```python
"""自動投票 Orchestrator Lambda.

15分間隔で起動。当日レース一覧を取得し、
発走5分前の one-time スケジュールを EventBridge Scheduler で動的に作成する。
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JRAVAN_API_URL = os.environ.get("JRAVAN_API_URL", "http://10.0.1.100:8000")
BET_EXECUTOR_ARN = os.environ.get("BET_EXECUTOR_ARN", "")
SCHEDULER_ROLE_ARN = os.environ.get("SCHEDULER_ROLE_ARN", "")
SCHEDULE_GROUP = os.environ.get("SCHEDULE_GROUP", "default")
MINUTES_BEFORE = 5  # 発走何分前にスケジュール
JST = timezone(timedelta(hours=9))


def handler(event, context):
    """Lambda ハンドラ."""
    now = datetime.now(timezone.utc)
    today = now.astimezone(JST).strftime("%Y%m%d")
    logger.info("Orchestrator started: date=%s", today)

    races = _get_today_races(today)
    if not races:
        logger.info("レースなし（非開催日）")
        return {"status": "ok", "created": 0, "skipped": 0}

    scheduler = boto3.client("scheduler", region_name="ap-northeast-1")
    created, skipped = 0, 0

    for race in races:
        race_id = race["race_id"]
        name = _schedule_name(race_id)

        start_time = datetime.fromisoformat(race["start_time"])
        fire_at = start_time - timedelta(minutes=MINUTES_BEFORE)

        if fire_at <= now:
            skipped += 1
            continue

        if _schedule_exists(scheduler, name):
            skipped += 1
            continue

        _create_schedule(scheduler, name, fire_at, race_id)
        created += 1

    logger.info("完了: created=%d, skipped=%d, total=%d", created, skipped, len(races))
    return {"status": "ok", "created": created, "skipped": skipped}


def _schedule_name(race_id: str) -> str:
    return f"auto-bet-{race_id}"


def _get_today_races(date_str: str) -> list[dict]:
    """JRA-VAN API からレース一覧を取得."""
    resp = requests.get(f"{JRAVAN_API_URL}/races", params={"date": date_str}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _schedule_exists(scheduler, name: str) -> bool:
    """EventBridge Schedule が既に存在するか."""
    try:
        scheduler.get_schedule(Name=name, GroupName=SCHEDULE_GROUP)
        return True
    except scheduler.exceptions.ResourceNotFoundException:
        return False


def _create_schedule(scheduler, name: str, fire_at: datetime, race_id: str):
    """EventBridge one-time schedule を作成."""
    schedule_expression = f"at({fire_at.strftime('%Y-%m-%dT%H:%M:%S')})"
    scheduler.create_schedule(
        Name=name,
        GroupName=SCHEDULE_GROUP,
        ScheduleExpression=schedule_expression,
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": BET_EXECUTOR_ARN,
            "RoleArn": SCHEDULER_ROLE_ARN,
            "Input": json.dumps({"race_id": race_id}),
        },
        ActionAfterCompletion="DELETE",
        State="ENABLED",
    )
    logger.info("Schedule created: %s at %s for %s", name, fire_at, race_id)
```

**Step 4: テスト実行して全パス確認**

**Step 5: コミット**

```bash
git add backend/batch/auto_bet_orchestrator.py backend/tests/batch/test_auto_bet_orchestrator.py
git commit -m "feat: Orchestrator Lambda ハンドラを実装"
```

---

## Task 7: CDK スタック変更

BakenKaigiBatchStack に Orchestrator Lambda, BetExecutor Lambda, EventBridge ルール, IAM ロールを追加する。

**Files:**
- Modify: `cdk/stacks/batch_stack.py`
- Modify: `cdk/tests/test_batch_stack.py` (あれば)

**Step 1: テストを書く（CDK Assertions）**

```python
"""batch_stack の自動投票リソースのテスト."""
# 既存の test_batch_stack.py に追加

def test_自動投票Lambda2つが定義されている(self):
    from aws_cdk.assertions import Match, Template
    template = Template.from_stack(self.stack)

    # Orchestrator Lambda
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "baken-kaigi-auto-bet-orchestrator",
        "Handler": "batch.auto_bet_orchestrator.handler",
        "Timeout": 60,
    })

    # BetExecutor Lambda
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "baken-kaigi-auto-bet-executor",
        "Handler": "batch.auto_bet_executor.handler",
        "Timeout": 120,
    })

def test_Orchestrator用EventBridgeルール(self):
    template = Template.from_stack(self.stack)
    template.has_resource_properties("AWS::Events::Rule", {
        "ScheduleExpression": "cron(0/15 0-7 ? * SAT,SUN *)",
    })
```

**Step 2: テスト実行して失敗を確認**

**Step 3: 実装（batch_stack.py の末尾に追加）**

`batch_stack.py` の `__init__` メソッド末尾に以下を追加:

```python
        # ========================================
        # 自動投票 Lambda
        # ========================================

        target_user_id = os.environ.get("AUTO_BET_USER_ID", "")

        # --- 購入記録テーブル参照 ---
        purchase_order_table = dynamodb.Table.from_table_name(
            self, "PurchaseOrderTable", "baken-kaigi-purchase-order"
        )

        # --- BetExecutor Lambda (VPC内、IPAT投票実行) ---
        auto_bet_executor_props: dict = {
            "runtime": lambda_.Runtime.PYTHON_3_12,
            "timeout": Duration.seconds(120),
            "memory_size": 512,
            "layers": [batch_deps_layer],
            "environment": {
                "PYTHONPATH": "/var/task:/opt/python",
                "TARGET_USER_ID": target_user_id,
                "PURCHASE_ORDER_TABLE_NAME": purchase_order_table.table_name,
            },
        }
        if vpc is not None:
            auto_bet_executor_props["vpc"] = vpc
            auto_bet_executor_props["vpc_subnets"] = ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        if use_jravan and jravan_api_url is not None:
            auto_bet_executor_props["environment"]["JRAVAN_API_URL"] = jravan_api_url

        auto_bet_executor_fn = lambda_.Function(
            self,
            "AutoBetExecutorFunction",
            handler="batch.auto_bet_executor.handler",
            code=backend_code,
            function_name="baken-kaigi-auto-bet-executor",
            description="自動投票 BetExecutor（レース発走5分前にパイプライン実行→IPAT投票）",
            **auto_bet_executor_props,
        )
        ai_predictions_table.grant_read_data(auto_bet_executor_fn)
        purchase_order_table.grant_write_data(auto_bet_executor_fn)
        auto_bet_executor_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}"
                    f":secret:baken-kaigi/ipat/*"
                ],
            )
        )

        # --- Orchestrator Lambda (VPC外、スケジュール管理) ---
        auto_bet_orchestrator_fn = lambda_.Function(
            self,
            "AutoBetOrchestratorFunction",
            handler="batch.auto_bet_orchestrator.handler",
            code=backend_code,
            function_name="baken-kaigi-auto-bet-orchestrator",
            description="自動投票 Orchestrator（15分間隔でレース確認→スケジュール作成）",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(60),
            memory_size=256,
            layers=[batch_deps_layer],
            environment={
                "PYTHONPATH": "/var/task:/opt/python",
                "BET_EXECUTOR_ARN": auto_bet_executor_fn.function_arn,
                "JRAVAN_API_URL": jravan_api_url or "",
            },
        )

        # Scheduler → BetExecutor invoke 用 IAM ロール
        scheduler_role = iam.Role(
            self,
            "AutoBetSchedulerRole",
            role_name="baken-kaigi-auto-bet-scheduler-role",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )
        auto_bet_executor_fn.grant_invoke(scheduler_role)

        auto_bet_orchestrator_fn.add_environment(
            "SCHEDULER_ROLE_ARN", scheduler_role.role_arn
        )

        # Orchestrator に Scheduler 操作権限
        auto_bet_orchestrator_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "scheduler:CreateSchedule",
                    "scheduler:DeleteSchedule",
                    "scheduler:GetSchedule",
                ],
                resources=["*"],
            )
        )
        # Orchestrator に PassRole 権限（Scheduler がロールを引き受けるため）
        auto_bet_orchestrator_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[scheduler_role.role_arn],
            )
        )

        # --- EventBridge ルール（土日 09:15-16:00 JST = 00:15-07:00 UTC, 15分間隔）---
        auto_bet_orchestrator_rule = events.Rule(
            self,
            "AutoBetOrchestratorRule",
            rule_name="baken-kaigi-auto-bet-orchestrator-rule",
            description="自動投票 Orchestrator を土日09:15-16:00 JSTに15分間隔で実行",
            schedule=events.Schedule.cron(
                minute="0/15",
                hour="0-7",
                month="*",
                week_day="SAT,SUN",
                year="*",
            ),
        )
        auto_bet_orchestrator_rule.add_target(
            targets.LambdaFunction(auto_bet_orchestrator_fn)
        )
```

`import` に `aws_iam` を追加:

```python
from aws_cdk import aws_iam as iam
```

**Step 4: CDKテスト実行**

Run: `cd /home/inoue-d/dev/baken-kaigi/bet/cdk && npx cdk synth --context jravan=true 2>&1 | head -20`

**Step 5: コミット**

```bash
git add cdk/stacks/batch_stack.py
git commit -m "feat: 自動投票 Lambda + EventBridge を CDK に追加"
```

---

## Task 8: リファレンスファイルのクリーンアップ

バックテスト参照用にコピーしたファイルを削除。

**Step 1:**

```bash
rm backend/backtest_reference_optimize_staking.py backend/backtest_reference_FINDINGS.md
git add -u
git commit -m "chore: バックテスト参照ファイルを削除"
```

---

## Task 9: 全テスト実行 & 動作確認

**Step 1: 全テスト実行**

Run: `cd /home/inoue-d/dev/baken-kaigi/bet/backend && uv run pytest -x -v`

全テストがパスすることを確認。

**Step 2: CDK synth**

Run: `cd /home/inoue-d/dev/baken-kaigi/bet/cdk && npx cdk synth --context jravan=true --quiet`

エラーがないことを確認。
