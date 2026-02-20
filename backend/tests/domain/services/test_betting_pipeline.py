"""確率推定パイプラインのテスト."""
import math

from src.domain.services.betting_pipeline import (
    BETAS,
    PLACE_WEIGHTS,
    SOURCES,
    WIN_WEIGHTS,
    compute_agree_counts,
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

    def test_beta_0で均等(self):
        scores = [80, 70, 60]
        probs = softmax(scores, 0.0)
        assert abs(probs[0] - probs[1]) < 1e-10

    def test_バックテストと同一計算(self):
        """optimize_staking.py の softmax と同一であることを検証."""
        scores = [90, 75, 60, 45, 30]
        beta = 0.070031
        probs = softmax(scores, beta)
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
        assert result[1] > result[2]

    def test_共通馬番のみ返す(self):
        pd1 = {1: 0.5, 2: 0.5}
        pd2 = {2: 0.6, 3: 0.4}
        result = log_opinion_pool([pd1, pd2], [0.5, 0.5])
        assert set(result.keys()) == {2}

    def test_空の場合は空辞書(self):
        pd1 = {1: 0.5}
        pd2 = {2: 0.5}
        result = log_opinion_pool([pd1, pd2], [0.5, 0.5])
        assert result == {}


class TestMarketImpliedProbs:
    def test_オッズから確率変換(self):
        odds_win = {
            "1": {"o": 2.0},
            "2": {"o": 5.0},
            "3": {"o": 10.0},
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

    def test_β値がバックテストと一致(self):
        assert BETAS["umamax"] == 0.052082
        assert BETAS["muryou-keiba-ai"] == 0.072791
        assert BETAS["keiba-ai-athena"] == 0.006745
        assert BETAS["keiba-ai-navi"] == 0.070031

    def test_ウェイトがバックテストと一致(self):
        assert WIN_WEIGHTS == [0.401, 0.035, 0.251, 0.313]
        assert PLACE_WEIGHTS == [0.314, 0.214, 0.309, 0.164]


class TestComputeAgreeCounts:
    def test_4ソース中の合意数(self):
        source_probs = [
            {1: 0.3, 2: 0.25, 3: 0.2, 4: 0.15, 5: 0.1},
            {1: 0.3, 3: 0.25, 5: 0.2, 2: 0.15, 4: 0.1},
            {3: 0.3, 1: 0.25, 2: 0.2, 5: 0.15, 4: 0.1},
            {1: 0.3, 2: 0.25, 5: 0.2, 3: 0.15, 4: 0.1},
        ]
        result = compute_agree_counts(source_probs, top_n=4)
        assert result[1] == 4
        assert result[2] == 4
        assert result[3] == 4
        assert result[5] == 3
        assert result[4] == 1
