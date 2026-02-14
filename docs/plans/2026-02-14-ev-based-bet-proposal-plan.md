# EV（期待値）ベース買い目提案 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 確率×オッズの期待値計算を中心にした2フェーズ買い目提案パイプラインを構築する。

**Architecture:** 既存の2285行モノリス `generate_bet_proposal` を2つのツールに分離する。Tool 1 (`analyze_race_for_betting`) がデータ収集+ベース確率算出を行い、Tool 2 (`propose_bets`) がLLM調整済み確率からEV計算→買い目選定→予算配分を行う。LLMは2つのツールの間で各馬の勝率を判断・調整する。

**Tech Stack:** Python 3.12, Strands Agents SDK (`@tool` decorator), boto3 (DynamoDB/Bedrock), pytest

**設計ドキュメント:** `docs/plans/2026-02-14-ev-based-bet-proposal-design.md`

---

## 前提知識

### テストパターン
- テストファイル: `backend/tests/agentcore/test_*.py`
- インポート: `sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))`
- テストメソッド名は日本語（例: `def test_勝率の合計が1になる`）
- ヘルパー: `_make_runners(count)`, `_make_ai_predictions(count)`, `_make_running_styles(count)`
- ナレーターのモック: `@patch("tools.bet_proposal._invoke_haiku_narrator", return_value=None)`
- テスト実行: `cd backend && uv run pytest tests/agentcore/test_<name>.py -v`

### DynamoDB Decimal型の罠
- DynamoDBは数値を `decimal.Decimal` で返す
- `Decimal * float` は `TypeError` → 必ず `float()` で変換

### フロントエンド互換性
`frontend/src/types/index.ts` の `BetProposalResponse` / `ProposedBet` 型に合わせる必要がある。

---

## Task 1: 重み付き統合確率の関数を作成

**Files:**
- Create: `backend/agentcore/tools/race_analyzer.py`
- Create: `backend/tests/agentcore/test_race_analyzer.py`

### Step 1: テスト用ヘルパーと最初のテストを書く

```python
# backend/tests/agentcore/test_race_analyzer.py
"""レース分析ツールのテスト."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.race_analyzer import _compute_weighted_probabilities


# =============================================================================
# テスト用データ
# =============================================================================

def _make_ai_result_multi_source() -> dict:
    """3ソースのAI予想結果を生成する."""
    return {
        "sources": [
            {
                "source": "jiro8",
                "predictions": [
                    {"horse_number": 1, "score": 100},
                    {"horse_number": 2, "score": 80},
                    {"horse_number": 3, "score": 60},
                ],
            },
            {
                "source": "kichiuma",
                "predictions": [
                    {"horse_number": 1, "score": 90},
                    {"horse_number": 2, "score": 90},
                    {"horse_number": 3, "score": 60},
                ],
            },
            {
                "source": "daily",
                "predictions": [
                    {"horse_number": 1, "score": 80},
                    {"horse_number": 2, "score": 70},
                    {"horse_number": 3, "score": 50},
                ],
            },
        ],
    }


# =============================================================================
# 重み付き統合確率テスト
# =============================================================================

class TestComputeWeightedProbabilities:
    """重み付き統合確率の計算テスト."""

    def test_確率の合計が1になる(self):
        ai_result = _make_ai_result_multi_source()
        weights = {"jiro8": 0.4, "kichiuma": 0.35, "daily": 0.25}
        probs = _compute_weighted_probabilities(ai_result, weights)
        assert abs(sum(probs.values()) - 1.0) < 1e-9

    def test_重みが反映される(self):
        """jiro8の重みが高い → jiro8で1位のhorse1の確率が高くなる."""
        ai_result = _make_ai_result_multi_source()
        # jiro8偏重: horse1=100, horse2=80 → horse1有利
        heavy_jiro8 = {"jiro8": 0.8, "kichiuma": 0.1, "daily": 0.1}
        probs_heavy = _compute_weighted_probabilities(ai_result, heavy_jiro8)
        # kichiuma偏重: horse1=90, horse2=90 → horse1とhorse2が接近
        heavy_kichiuma = {"jiro8": 0.1, "kichiuma": 0.8, "daily": 0.1}
        probs_kichiuma = _compute_weighted_probabilities(ai_result, heavy_kichiuma)
        # jiro8偏重のほうがhorse1とhorse2の差が大きい
        gap_heavy = probs_heavy[1] - probs_heavy[2]
        gap_kichiuma = probs_kichiuma[1] - probs_kichiuma[2]
        assert gap_heavy > gap_kichiuma

    def test_ソースが1つしかない場合(self):
        ai_result = {
            "sources": [
                {
                    "source": "jiro8",
                    "predictions": [
                        {"horse_number": 1, "score": 100},
                        {"horse_number": 2, "score": 50},
                    ],
                },
            ],
        }
        weights = {"jiro8": 0.4, "kichiuma": 0.35, "daily": 0.25}
        probs = _compute_weighted_probabilities(ai_result, weights)
        assert len(probs) == 2
        assert abs(sum(probs.values()) - 1.0) < 1e-9

    def test_空のソースの場合(self):
        ai_result = {"sources": []}
        weights = {"jiro8": 0.4, "kichiuma": 0.35, "daily": 0.25}
        probs = _compute_weighted_probabilities(ai_result, weights)
        assert probs == {}

    def test_Decimal型のスコアに対応(self):
        from decimal import Decimal
        ai_result = {
            "sources": [
                {
                    "source": "jiro8",
                    "predictions": [
                        {"horse_number": 1, "score": Decimal("100")},
                        {"horse_number": 2, "score": Decimal("50")},
                    ],
                },
            ],
        }
        weights = {"jiro8": 0.4}
        probs = _compute_weighted_probabilities(ai_result, weights)
        assert isinstance(probs[1], float)
```

### Step 2: テストが失敗することを確認

Run: `cd backend && uv run pytest tests/agentcore/test_race_analyzer.py -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

### Step 3: 最小限の実装を書く

```python
# backend/agentcore/tools/race_analyzer.py
"""レース分析ツール.

レースデータを収集し、各馬のベース勝率を算出する。
LLMが買い目判断に使う分析データを提供する。
"""

import logging

logger = logging.getLogger(__name__)

# ソースごとのデフォルト重み
DEFAULT_SOURCE_WEIGHTS = {
    "jiro8": 0.40,
    "kichiuma": 0.35,
    "daily": 0.25,
}


def _compute_weighted_probabilities(
    ai_result: dict,
    source_weights: dict[str, float] | None = None,
) -> dict[int, float]:
    """AIソースのスコアを重み付きで統合して馬ごとの勝率を算出する.

    各ソース内でスコアを正規化（score / Σscores → 確率）し、
    ソースの重みで加重平均を取り、再正規化して合計1.0にする。

    Args:
        ai_result: AI予想結果 (sources: [{source, predictions: [{horse_number, score}]}])
        source_weights: ソース名→重みの辞書。Noneの場合はDEFAULT_SOURCE_WEIGHTS

    Returns:
        {horse_number: win_probability} （合計 ≈ 1.0）
    """
    weights = source_weights or DEFAULT_SOURCE_WEIGHTS
    sources = ai_result.get("sources", [])
    if not sources:
        return {}

    # 馬番ごとに重み付き確率を蓄積
    horse_weighted_sum: dict[int, float] = {}
    total_weight_used = 0.0

    for source in sources:
        source_name = source.get("source", "")
        predictions = source.get("predictions", [])
        if not predictions:
            continue

        # ソース内の合計スコア
        scores: dict[int, float] = {}
        for pred in predictions:
            hn = int(pred.get("horse_number", 0))
            score = float(pred.get("score", 0))
            if hn > 0:
                scores[hn] = score

        total_score = sum(scores.values())
        if total_score <= 0:
            continue

        # このソースの重み（未知のソースは均等配分）
        w = weights.get(source_name, 1.0 / max(len(sources), 1))
        total_weight_used += w

        # ソース内正規化 × 重み
        for hn, score in scores.items():
            prob = score / total_score
            horse_weighted_sum[hn] = horse_weighted_sum.get(hn, 0.0) + prob * w

    if not horse_weighted_sum or total_weight_used <= 0:
        return {}

    # 最終正規化（合計=1.0を保証）
    total = sum(horse_weighted_sum.values())
    if total <= 0:
        return {}

    return {hn: p / total for hn, p in horse_weighted_sum.items()}
```

### Step 4: テストが通ることを確認

Run: `cd backend && uv run pytest tests/agentcore/test_race_analyzer.py -v`
Expected: PASS (5 tests)

### Step 5: コミット

```bash
git add backend/agentcore/tools/race_analyzer.py backend/tests/agentcore/test_race_analyzer.py
git commit -m "feat: 重み付き統合確率の関数を追加"
```

---

## Task 2: `analyze_race_for_betting` の実装関数を作成

**Files:**
- Modify: `backend/agentcore/tools/race_analyzer.py`
- Modify: `backend/tests/agentcore/test_race_analyzer.py`

**注意:** この関数はデータ取得（API呼び出し）を伴うが、テストではモックを使う。
内部関数 `_analyze_race_impl` を作り、データ取得済みの状態からテストする。

### Step 1: テストを追加

```python
# backend/tests/agentcore/test_race_analyzer.py に追加

from tools.race_analyzer import _analyze_race_impl


def _make_runners(count: int, *, with_odds: bool = True) -> list[dict]:
    """テスト用出走馬データを生成する."""
    runners = []
    for i in range(1, count + 1):
        runner = {
            "horse_number": i,
            "horse_name": f"テスト馬{i}",
            "popularity": i,
        }
        if with_odds:
            runner["odds"] = round(2.0 + i * 1.5, 1)
        runners.append(runner)
    return runners


def _make_ai_predictions(count: int) -> list[dict]:
    """テスト用AI予想データを生成する."""
    preds = []
    for i in range(1, count + 1):
        preds.append({
            "horse_number": i,
            "horse_name": f"テスト馬{i}",
            "rank": i,
            "score": 400 - (i - 1) * 30,
        })
    return preds


def _make_running_styles(count: int) -> list[dict]:
    """テスト用脚質データを生成する."""
    styles = ["逃げ", "先行", "差し", "追込", "自在"]
    result = []
    for i in range(1, count + 1):
        result.append({
            "horse_number": i,
            "horse_name": f"テスト馬{i}",
            "running_style": styles[(i - 1) % len(styles)],
        })
    return result


class TestAnalyzeRaceImpl:
    """_analyze_race_impl のテスト."""

    def test_基本的なレース分析結果の構造(self):
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        ai_result = {
            "sources": [
                {"source": "jiro8", "predictions": ai_preds},
            ],
        }
        running_styles = _make_running_styles(6)

        result = _analyze_race_impl(
            race_id="20260201_05_11",
            race_name="東京11R テスト重賞",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=6,
            race_conditions=["芝", "良"],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=running_styles,
        )

        # race_info の検証
        assert result["race_info"]["race_id"] == "20260201_05_11"
        assert result["race_info"]["race_name"] == "東京11R テスト重賞"
        assert result["race_info"]["total_runners"] == 6
        assert "difficulty" in result["race_info"]
        assert "predicted_pace" in result["race_info"]
        assert "skip_score" in result["race_info"]
        assert "ai_consensus" in result["race_info"]
        assert "confidence_factor" in result["race_info"]

        # horses の検証
        assert len(result["horses"]) == 6
        horse1 = result["horses"][0]
        assert "number" in horse1
        assert "name" in horse1
        assert "odds" in horse1
        assert "base_win_probability" in horse1
        assert isinstance(horse1["base_win_probability"], float)

        # source_weights の検証
        assert "source_weights" in result

    def test_全馬のベース確率合計が1になる(self):
        runners = _make_runners(12)
        ai_preds = _make_ai_predictions(12)
        ai_result = {
            "sources": [
                {"source": "jiro8", "predictions": ai_preds},
            ],
        }

        result = _analyze_race_impl(
            race_id="20260201_05_11",
            race_name="テスト",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=12,
            race_conditions=[],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=[],
        )

        total_prob = sum(h["base_win_probability"] for h in result["horses"])
        assert abs(total_prob - 1.0) < 1e-9

    def test_スピード指数と過去成績が含まれる(self):
        runners = _make_runners(3)
        ai_preds = _make_ai_predictions(3)
        ai_result = {"sources": [{"source": "jiro8", "predictions": ai_preds}]}

        speed_index_data = {
            "horses": [
                {"horse_number": 1, "indices": [{"value": 105}]},
                {"horse_number": 2, "indices": [{"value": 98}, {"value": 100}]},
            ]
        }
        past_performance_data = {
            "horses": [
                {"horse_number": 1, "performances": [
                    {"finish_position": 1}, {"finish_position": 3},
                ]},
            ]
        }

        result = _analyze_race_impl(
            race_id="test",
            race_name="テスト",
            venue="東京",
            distance="1600m",
            surface="芝",
            total_runners=3,
            race_conditions=[],
            runners_data=runners,
            ai_result=ai_result,
            running_styles=[],
            speed_index_data=speed_index_data,
            past_performance_data=past_performance_data,
        )

        horse1 = next(h for h in result["horses"] if h["number"] == 1)
        assert horse1["speed_index"] is not None
        assert horse1["speed_index"]["latest"] == 105
        assert horse1["recent_form"] == [1, 3]
```

### Step 2: テストが失敗することを確認

Run: `cd backend && uv run pytest tests/agentcore/test_race_analyzer.py::TestAnalyzeRaceImpl -v`
Expected: FAIL with "ImportError"

### Step 3: `_analyze_race_impl` を実装

```python
# backend/agentcore/tools/race_analyzer.py に追加

from .pace_analysis import _assess_race_difficulty, _predict_pace
from .risk_analysis import _assess_skip_recommendation
from .bet_proposal import _calculate_confidence_factor, _assess_ai_consensus

# ペース相性マッピング（bet_proposal.pyから移植）
PACE_STYLE_COMPAT = {
    "ハイ": {"差し": 1.0, "追込": 1.0, "自在": 0.5, "先行": -0.5, "逃げ": -1.0},
    "ミドル": {"先行": 0.5, "差し": 0.5, "自在": 0.5, "逃げ": 0.0, "追込": 0.0},
    "スロー": {"逃げ": 1.0, "先行": 1.0, "自在": 0.5, "差し": -0.5, "追込": -1.0},
}


def _analyze_race_impl(
    race_id: str,
    race_name: str,
    venue: str,
    distance: str,
    surface: str,
    total_runners: int,
    race_conditions: list[str],
    runners_data: list[dict],
    ai_result: dict,
    running_styles: list[dict] | None = None,
    speed_index_data: dict | None = None,
    past_performance_data: dict | None = None,
    source_weights: dict[str, float] | None = None,
) -> dict:
    """レース分析の実装（テスト用に公開）.

    Args:
        race_id: レースID
        race_name: レース名
        venue: 競馬場名
        distance: 距離
        surface: 馬場
        total_runners: 出走頭数
        race_conditions: レース条件リスト
        runners_data: 出走馬データ
        ai_result: AI予想結果 (sources配列)
        running_styles: 脚質データ
        speed_index_data: スピード指数データ
        past_performance_data: 過去成績データ
        source_weights: AI予想ソース重み

    Returns:
        レース分析結果 (race_info, horses, source_weights)
    """
    running_styles = running_styles or []
    weights = source_weights or DEFAULT_SOURCE_WEIGHTS

    # ベース確率算出
    base_probs = _compute_weighted_probabilities(ai_result, weights)

    # ペース予想
    front_runners = sum(1 for rs in running_styles if rs.get("running_style") == "逃げ")
    predicted_pace = _predict_pace(front_runners, total_runners) if running_styles else ""

    # レース難易度
    difficulty = _assess_race_difficulty(total_runners, race_conditions, venue, runners_data)

    # 見送りスコア
    ai_predictions = []
    sources = ai_result.get("sources", [])
    if sources:
        ai_predictions = sources[0].get("predictions", [])
    skip = _assess_skip_recommendation(
        ai_predictions, total_runners, race_conditions, venue, runners_data,
    )
    skip_score = skip.get("skip_score", 0)
    confidence_factor = _calculate_confidence_factor(skip_score)

    # AI合議
    ai_consensus = _assess_ai_consensus(ai_predictions) if ai_predictions else "データなし"

    # 脚質マップ
    style_map = {rs.get("horse_number"): rs.get("running_style", "") for rs in running_styles}

    # スピード指数マップ
    si_map = {}
    if speed_index_data and "horses" in speed_index_data:
        for h in speed_index_data["horses"]:
            hn = h.get("horse_number")
            indices = h.get("indices", [])
            if hn and indices:
                latest = float(indices[0].get("value", 0))
                avg = sum(float(idx.get("value", 0)) for idx in indices) / len(indices)
                si_map[hn] = {"latest": latest, "avg": round(avg, 1)}

    # 過去成績マップ
    pp_map = {}
    if past_performance_data and "horses" in past_performance_data:
        for h in past_performance_data["horses"]:
            hn = h.get("horse_number")
            perfs = h.get("performances", [])
            if hn and perfs:
                form = [int(p.get("finish_position", 99)) for p in perfs[:5]]
                pp_map[hn] = form

    # AI予想スコアマップ（全ソース）
    ai_scores_map: dict[int, dict] = {}
    for source in sources:
        source_name = source.get("source", "")
        for pred in source.get("predictions", []):
            hn = int(pred.get("horse_number", 0))
            score = float(pred.get("score", 0))
            if hn > 0:
                if hn not in ai_scores_map:
                    ai_scores_map[hn] = {}
                ai_scores_map[hn][source_name] = score

    # 各馬の情報を構築
    horses = []
    for runner in runners_data:
        hn = runner.get("horse_number")
        style = style_map.get(hn, "")
        pace_compat = PACE_STYLE_COMPAT.get(predicted_pace, {}).get(style, 0.0)

        horses.append({
            "number": hn,
            "name": runner.get("horse_name", ""),
            "odds": float(runner.get("odds", 0)),
            "base_win_probability": base_probs.get(hn, 0.0),
            "ai_scores": ai_scores_map.get(hn, {}),
            "running_style": style or None,
            "pace_compatibility": pace_compat,
            "speed_index": si_map.get(hn),
            "recent_form": pp_map.get(hn),
        })

    return {
        "race_info": {
            "race_id": race_id,
            "race_name": race_name,
            "venue": venue,
            "distance": distance,
            "surface": surface,
            "total_runners": total_runners,
            "difficulty": difficulty,
            "predicted_pace": predicted_pace,
            "skip_score": skip_score,
            "ai_consensus": ai_consensus,
            "confidence_factor": confidence_factor,
        },
        "horses": horses,
        "source_weights": weights,
    }
```

### Step 4: テストが通ることを確認

Run: `cd backend && uv run pytest tests/agentcore/test_race_analyzer.py -v`
Expected: PASS (all tests)

### Step 5: コミット

```bash
git add backend/agentcore/tools/race_analyzer.py backend/tests/agentcore/test_race_analyzer.py
git commit -m "feat: レース分析の実装関数を追加"
```

---

## Task 3: `propose_bets` のEV計算+買い目選定の実装関数を作成

**Files:**
- Create: `backend/agentcore/tools/ev_proposer.py`
- Create: `backend/tests/agentcore/test_ev_proposer.py`

**このタスクの核心:** 全組合せのEVを計算し、EV > 1.0 の買い目を選ぶ。

### Step 1: テストを書く

```python
# backend/tests/agentcore/test_ev_proposer.py
"""EVベース買い目提案ツールのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from tools.ev_proposer import _propose_bets_impl


def _make_runners(count: int) -> list[dict]:
    """テスト用出走馬データを生成する."""
    runners = []
    for i in range(1, count + 1):
        runners.append({
            "horse_number": i,
            "horse_name": f"テスト馬{i}",
            "popularity": i,
            "odds": round(2.0 + i * 1.5, 1),
        })
    return runners


class TestProposeBetsImpl:
    """_propose_bets_impl のテスト."""

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_EV1以上の買い目だけが選ばれる(self, mock_narrator):
        """確率が高い馬の組合せはEV > 1.0 で選ばれ、低い馬は除外される."""
        runners = _make_runners(6)
        # 馬1が圧倒的に強い → 馬1絡みの組合せのEVが高い
        win_probs = {1: 0.50, 2: 0.20, 3: 0.15, 4: 0.08, 5: 0.05, 6: 0.02}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
        )

        assert "proposed_bets" in result
        for bet in result["proposed_bets"]:
            assert bet["expected_value"] >= 1.0

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_EV降順にソートされる(self, mock_narrator):
        runners = _make_runners(6)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.06, 6: 0.04}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
        )

        bets = result["proposed_bets"]
        if len(bets) >= 2:
            for i in range(len(bets) - 1):
                assert bets[i]["expected_value"] >= bets[i + 1]["expected_value"]

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_全組合せEV1未満で買い目ゼロ(self, mock_narrator):
        """確率が低くオッズも低い→全てEV < 1.0 → 買い目なし."""
        runners = _make_runners(6)
        # 均等な確率 + 低オッズ → EV < 1.0
        win_probs = {i: 1.0 / 6 for i in range(1, 7)}
        # オッズを全部低くする
        for r in runners:
            r["odds"] = 2.0

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
        )

        assert result["proposed_bets"] == []
        assert result["total_amount"] == 0

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_max_betsで買い目数が制限される(self, mock_narrator):
        runners = _make_runners(8)
        win_probs = {1: 0.35, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.05, 6: 0.04, 7: 0.03, 8: 0.03}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=8,
            budget=10000,
            max_bets=3,
        )

        assert len(result["proposed_bets"]) <= 3

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_preferred_bet_typesで券種がフィルタされる(self, mock_narrator):
        runners = _make_runners(6)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.06, 6: 0.04}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
            preferred_bet_types=["quinella"],
        )

        for bet in result["proposed_bets"]:
            assert bet["bet_type"] == "quinella"

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_bankrollモードでダッチング配分(self, mock_narrator):
        runners = _make_runners(6)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.06, 6: 0.04}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            bankroll=100000,
        )

        if result["proposed_bets"]:
            assert "confidence_factor" in result
            assert "race_budget" in result

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_フロントエンド互換の出力形式(self, mock_narrator):
        """BetProposalResponse 型に合致する構造を返すこと."""
        runners = _make_runners(6)
        win_probs = {1: 0.50, 2: 0.20, 3: 0.15, 4: 0.08, 5: 0.05, 6: 0.02}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
            race_name="テスト重賞",
            race_conditions=["芝", "良"],
            venue="東京",
        )

        # BetProposalResponse の必須フィールド
        assert "race_id" in result
        assert "race_summary" in result
        assert "proposed_bets" in result
        assert "total_amount" in result
        assert "budget_remaining" in result
        assert "analysis_comment" in result
        assert "disclaimer" in result

        # RaceSummary のフィールド
        summary = result["race_summary"]
        assert "race_name" in summary
        assert "difficulty_stars" in summary

        # ProposedBet のフィールド
        if result["proposed_bets"]:
            bet = result["proposed_bets"][0]
            assert "bet_type" in bet
            assert "horse_numbers" in bet
            assert "amount" in bet
            assert "confidence" in bet
            assert "expected_value" in bet
            assert "composite_odds" in bet
            assert "reasoning" in bet
            assert "bet_display" in bet
```

### Step 2: テストが失敗することを確認

Run: `cd backend && uv run pytest tests/agentcore/test_ev_proposer.py -v`
Expected: FAIL with "ModuleNotFoundError"

### Step 3: `_propose_bets_impl` を実装

```python
# backend/agentcore/tools/ev_proposer.py
"""EVベース買い目提案ツール.

LLMが調整した勝率と実オッズから期待値を計算し、
期待値が正の買い目を選定・予算配分する。
"""

import logging
import math
from itertools import combinations, permutations

from .bet_analysis import (
    BET_TYPE_NAMES,
    _harville_exacta,
    _harville_trifecta,
)
from .bet_proposal import (
    BET_TYPE_ODDS_MULTIPLIER,
    MIN_BET_AMOUNT,
    MAX_RACE_BUDGET_RATIO,
    DEFAULT_BASE_RATE,
    _calculate_confidence_factor,
    _allocate_budget,
    _allocate_budget_dutching,
    _invoke_haiku_narrator,
)
from .pace_analysis import _assess_race_difficulty, _predict_pace
from .risk_analysis import _assess_skip_recommendation

logger = logging.getLogger(__name__)

# EV閾値: これ以上の期待値がある組合せのみ提案
EV_THRESHOLD = 1.0

# デフォルト券種リスト（preferred_bet_types未指定時）
DEFAULT_BET_TYPES = ["quinella", "exacta", "quinella_place", "trio"]

# 組合せ生成対象の最小確率（これ以下の馬は組合せに含めない）
MIN_PROB_FOR_COMBINATION = 0.02

# デフォルト買い目上限
DEFAULT_MAX_BETS = 10


def _estimate_odds(horse_numbers: list[int], bet_type: str, runners_map: dict) -> float:
    """馬番リストと券種から推定オッズを計算する.

    単勝オッズの積（or幾何平均）× 券種補正係数で推定。
    """
    odds_list = []
    for hn in horse_numbers:
        runner = runners_map.get(hn, {})
        odds = float(runner.get("odds", 0))
        if odds > 0:
            odds_list.append(odds)

    if not odds_list:
        return 0.0

    multiplier = BET_TYPE_ODDS_MULTIPLIER.get(bet_type, 1.0)

    if len(odds_list) == 1:
        return odds_list[0]
    elif len(odds_list) == 2:
        return math.sqrt(odds_list[0] * odds_list[1]) * multiplier
    else:
        geo_mean = (odds_list[0] * odds_list[1] * odds_list[2]) ** (1 / 3)
        return geo_mean * multiplier


def _calculate_combination_probability(
    horse_numbers: list[int],
    bet_type: str,
    win_probs: dict[int, float],
    total_runners: int,
) -> float:
    """Harvilleモデルで組合せ確率を算出する."""
    if bet_type == "win":
        return win_probs.get(horse_numbers[0], 0.0)

    elif bet_type == "place":
        return min(1.0, win_probs.get(horse_numbers[0], 0.0) * 3)

    elif bet_type == "quinella":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        return _harville_exacta(p_a, p_b) + _harville_exacta(p_b, p_a)

    elif bet_type == "exacta":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        return _harville_exacta(p_a, p_b)

    elif bet_type == "quinella_place":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        prob = 0.0
        for hn_c, p_c in win_probs.items():
            if hn_c in set(horse_numbers):
                continue
            prob += _harville_trifecta(p_a, p_b, p_c)
            prob += _harville_trifecta(p_a, p_c, p_b)
            prob += _harville_trifecta(p_b, p_a, p_c)
            prob += _harville_trifecta(p_b, p_c, p_a)
            prob += _harville_trifecta(p_c, p_a, p_b)
            prob += _harville_trifecta(p_c, p_b, p_a)
        return prob

    elif bet_type == "trio":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        p_c = win_probs.get(horse_numbers[2], 0.0)
        return sum(
            _harville_trifecta(pa, pb, pc)
            for pa, pb, pc in permutations([p_a, p_b, p_c])
        )

    elif bet_type == "trifecta":
        p_a = win_probs.get(horse_numbers[0], 0.0)
        p_b = win_probs.get(horse_numbers[1], 0.0)
        p_c = win_probs.get(horse_numbers[2], 0.0)
        return _harville_trifecta(p_a, p_b, p_c)

    return 0.0


def _generate_ev_candidates(
    win_probs: dict[int, float],
    runners_map: dict[int, dict],
    bet_types: list[str],
    total_runners: int,
) -> list[dict]:
    """全組合せのEVを計算し、EV > 閾値のものを返す.

    Args:
        win_probs: {horse_number: win_probability}
        runners_map: {horse_number: runner_dict}
        bet_types: 対象券種リスト
        total_runners: 出走頭数

    Returns:
        EV > EV_THRESHOLD の買い目候補リスト（EV降順）
    """
    # 組合せ対象馬: 確率が閾値以上
    eligible = sorted(
        [hn for hn, p in win_probs.items() if p >= MIN_PROB_FOR_COMBINATION],
        key=lambda hn: win_probs[hn],
        reverse=True,
    )

    candidates = []

    for bet_type in bet_types:
        if bet_type in ("win", "place"):
            for hn in eligible:
                horse_numbers = [hn]
                prob = _calculate_combination_probability(
                    horse_numbers, bet_type, win_probs, total_runners,
                )
                est_odds = _estimate_odds(horse_numbers, bet_type, runners_map)
                ev = prob * est_odds if est_odds > 0 else 0.0
                if ev >= EV_THRESHOLD:
                    candidates.append(_build_candidate(
                        horse_numbers, bet_type, prob, est_odds, ev, runners_map,
                    ))

        elif bet_type in ("quinella", "exacta", "quinella_place"):
            for combo in combinations(eligible, 2):
                horse_numbers = list(combo)
                if bet_type == "exacta":
                    # 馬単は順序あり → 上位確率の馬を1着に
                    horse_numbers.sort(key=lambda h: win_probs.get(h, 0), reverse=True)
                prob = _calculate_combination_probability(
                    horse_numbers, bet_type, win_probs, total_runners,
                )
                est_odds = _estimate_odds(horse_numbers, bet_type, runners_map)
                ev = prob * est_odds if est_odds > 0 else 0.0
                if ev >= EV_THRESHOLD:
                    candidates.append(_build_candidate(
                        horse_numbers, bet_type, prob, est_odds, ev, runners_map,
                    ))

        elif bet_type in ("trio", "trifecta"):
            for combo in combinations(eligible, 3):
                horse_numbers = list(combo)
                if bet_type == "trifecta":
                    horse_numbers.sort(key=lambda h: win_probs.get(h, 0), reverse=True)
                prob = _calculate_combination_probability(
                    horse_numbers, bet_type, win_probs, total_runners,
                )
                est_odds = _estimate_odds(horse_numbers, bet_type, runners_map)
                ev = prob * est_odds if est_odds > 0 else 0.0
                if ev >= EV_THRESHOLD:
                    candidates.append(_build_candidate(
                        horse_numbers, bet_type, prob, est_odds, ev, runners_map,
                    ))

    # EV降順でソート
    candidates.sort(key=lambda c: c["expected_value"], reverse=True)
    return candidates


def _build_candidate(
    horse_numbers: list[int],
    bet_type: str,
    probability: float,
    estimated_odds: float,
    ev: float,
    runners_map: dict,
) -> dict:
    """買い目候補の辞書を構築する."""
    # confidence はEVから算出
    if ev >= 1.5:
        confidence = "high"
    elif ev >= 1.2:
        confidence = "medium"
    else:
        confidence = "low"

    # 馬名リスト
    names = [runners_map.get(hn, {}).get("horse_name", f"{hn}番") for hn in horse_numbers]
    bet_type_name = BET_TYPE_NAMES.get(bet_type, bet_type)

    if len(names) == 1:
        display = f"{bet_type_name} {horse_numbers[0]}番 {names[0]}"
    elif len(names) == 2:
        display = f"{bet_type_name} {horse_numbers[0]}-{horse_numbers[1]}"
    else:
        display = f"{bet_type_name} {'-'.join(str(h) for h in horse_numbers)}"

    return {
        "bet_type": bet_type,
        "horse_numbers": horse_numbers,
        "amount": 0,  # 予算配分で後から設定
        "bet_count": 1,
        "bet_display": display,
        "confidence": confidence,
        "expected_value": round(ev, 2),
        "composite_odds": round(estimated_odds, 1),
        "combination_probability": round(probability, 6),
        "reasoning": f"EV={ev:.2f} (確率{probability:.1%}×推定オッズ{estimated_odds:.1f}倍)",
    }


def _propose_bets_impl(
    race_id: str,
    win_probabilities: dict[int, float],
    runners_data: list[dict],
    total_runners: int,
    budget: int = 0,
    bankroll: int = 0,
    preferred_bet_types: list[str] | None = None,
    max_bets: int | None = None,
    race_name: str = "",
    race_conditions: list[str] | None = None,
    venue: str = "",
    skip_score: int = 0,
    predicted_pace: str = "",
    ai_consensus: str = "",
) -> dict:
    """EVベース買い目提案の統合実装（テスト用に公開）.

    Args:
        race_id: レースID
        win_probabilities: {horse_number: win_probability} LLM調整済み確率
        runners_data: 出走馬データ
        total_runners: 出走頭数
        budget: 予算（従来モード）
        bankroll: bankrollモード総資金
        preferred_bet_types: 券種フィルタ
        max_bets: 買い目上限
        race_name: レース名
        race_conditions: レース条件
        venue: 競馬場名
        skip_score: 見送りスコア
        predicted_pace: 予想ペース
        ai_consensus: AI合議結果

    Returns:
        BetProposalResponse互換の提案結果
    """
    race_conditions = race_conditions or []
    runners_map = {r.get("horse_number"): r for r in runners_data}
    bet_types = preferred_bet_types or DEFAULT_BET_TYPES
    effective_max_bets = max_bets or DEFAULT_MAX_BETS

    use_bankroll = bankroll > 0
    confidence_factor = _calculate_confidence_factor(skip_score)

    # 見送り判定（信頼度0 = 見送り）
    if confidence_factor == 0.0:
        return _build_skip_result(race_id, race_name, skip_score, venue, predicted_pace, ai_consensus)

    # 1. EV計算+買い目候補生成
    candidates = _generate_ev_candidates(
        win_probabilities, runners_map, bet_types, total_runners,
    )

    # 2. 上限で切る
    bets = candidates[:effective_max_bets]

    # 3. 予算計算
    if use_bankroll:
        base_rate = DEFAULT_BASE_RATE
        race_budget = int(bankroll * base_rate * confidence_factor)
        race_budget = min(race_budget, int(bankroll * MAX_RACE_BUDGET_RATIO))
        effective_budget = race_budget
    else:
        effective_budget = budget
        if skip_score >= 7:
            effective_budget = int(budget * 0.5)
        race_budget = 0

    # 4. 予算配分
    if bets and effective_budget > 0:
        if use_bankroll:
            bets = _allocate_budget_dutching(bets, effective_budget)
        else:
            bets = _allocate_budget(bets, effective_budget)

    total_amount = sum(b.get("amount", 0) for b in bets)
    budget_remaining = effective_budget - total_amount

    # 5. 難易度
    difficulty = _assess_race_difficulty(total_runners, race_conditions, venue, runners_data)

    # 6. ナレーション
    narration_context = {
        "race_name": race_name,
        "difficulty": difficulty,
        "predicted_pace": predicted_pace,
        "ai_consensus": ai_consensus,
        "skip_score": skip_score,
        "bets": bets,
    }
    analysis_comment = _invoke_haiku_narrator(narration_context, bets, runners_data)
    if not analysis_comment:
        analysis_comment = f"EV分析に基づく提案。{len(bets)}点。"

    result = {
        "race_id": race_id,
        "race_summary": {
            "race_name": race_name,
            "difficulty_stars": difficulty,
            "predicted_pace": predicted_pace or "不明",
            "ai_consensus_level": ai_consensus or "不明",
            "skip_score": skip_score,
            "skip_recommendation": "見送り推奨" if skip_score >= 7 else "",
        },
        "proposed_bets": bets,
        "total_amount": total_amount,
        "budget_remaining": max(0, budget_remaining),
        "analysis_comment": analysis_comment,
        "proposal_reasoning": f"確率×オッズの期待値(EV)が{EV_THRESHOLD}以上の組合せを{len(bets)}点選定",
        "disclaimer": "この提案はデータ分析に基づくものであり、的中を保証するものではありません。",
    }

    if use_bankroll:
        result["race_budget"] = race_budget
        result["confidence_factor"] = confidence_factor
        result["bankroll_usage_pct"] = round(total_amount / bankroll * 100, 2) if bankroll > 0 else 0

    return result


def _build_skip_result(
    race_id: str, race_name: str, skip_score: int,
    venue: str, predicted_pace: str, ai_consensus: str,
) -> dict:
    """見送り時の結果を返す."""
    return {
        "race_id": race_id,
        "race_summary": {
            "race_name": race_name,
            "difficulty_stars": 0,
            "predicted_pace": predicted_pace or "不明",
            "ai_consensus_level": ai_consensus or "不明",
            "skip_score": skip_score,
            "skip_recommendation": "見送り推奨",
        },
        "proposed_bets": [],
        "total_amount": 0,
        "budget_remaining": 0,
        "analysis_comment": f"見送りスコア{skip_score}/10。投資を見送ります。",
        "proposal_reasoning": "見送りスコアが高いため提案なし",
        "disclaimer": "この提案はデータ分析に基づくものであり、的中を保証するものではありません。",
    }
```

### Step 4: テストが通ることを確認

Run: `cd backend && uv run pytest tests/agentcore/test_ev_proposer.py -v`
Expected: PASS (7 tests)

### Step 5: コミット

```bash
git add backend/agentcore/tools/ev_proposer.py backend/tests/agentcore/test_ev_proposer.py
git commit -m "feat: EVベース買い目提案の実装関数を追加"
```

---

## Task 4: @tool デコレータの追加とツール登録

**Files:**
- Modify: `backend/agentcore/tools/race_analyzer.py`
- Modify: `backend/agentcore/tools/ev_proposer.py`
- Modify: `backend/agentcore/tool_router.py`

### Step 1: `analyze_race_for_betting` に @tool デコレータを追加

`backend/agentcore/tools/race_analyzer.py` の末尾に追加:

```python
from strands import tool

@tool
def analyze_race_for_betting(race_id: str) -> dict:
    """レースの分析データとベース勝率を取得する.

    AI予想・展開予想・スピード指数・過去成績を統合し、
    各馬のベース勝率とレース特性を分析する。
    LLMが勝率を判断するための材料を提供する。

    Args:
        race_id: レースID (例: "20260201_05_11")

    Returns:
        分析結果:
        - race_info: レース概要（難易度、ペース、見送りスコア、AI合議）
        - horses: 各馬データ（オッズ、ベース勝率、AI予想、脚質、スピード指数、近走成績）
        - source_weights: AI予想ソースの重み
    """
    import requests
    from .race_data import _fetch_race_detail, _extract_race_conditions
    from .ai_prediction import get_ai_prediction
    from .pace_analysis import _get_running_styles
    from .speed_index import get_speed_index
    from .past_performance import get_past_performance

    # レースデータ取得
    race_detail = _fetch_race_detail(race_id)
    race = race_detail.get("race", {})
    runners_data = race_detail.get("runners", [])
    race_conditions = _extract_race_conditions(race)

    # AI予想取得
    ai_result = get_ai_prediction(race_id) or {}

    # 脚質データ取得
    running_styles = _get_running_styles(race_id)

    # スピード指数取得
    speed_index_data = None
    si_result = get_speed_index(race_id)
    if isinstance(si_result, dict) and "error" not in si_result:
        speed_index_data = si_result

    # 過去成績取得
    past_performance_data = None
    pp_result = get_past_performance(race_id)
    if isinstance(pp_result, dict) and "error" not in pp_result:
        past_performance_data = pp_result

    return _analyze_race_impl(
        race_id=race_id,
        race_name=race.get("race_name", ""),
        venue=race.get("venue", ""),
        distance=race.get("distance", ""),
        surface=race.get("surface", ""),
        total_runners=race.get("horse_count", len(runners_data)),
        race_conditions=race_conditions,
        runners_data=runners_data,
        ai_result=ai_result,
        running_styles=running_styles,
        speed_index_data=speed_index_data,
        past_performance_data=past_performance_data,
    )
```

### Step 2: `propose_bets` に @tool デコレータを追加

`backend/agentcore/tools/ev_proposer.py` の末尾に追加:

```python
from strands import tool

@tool
def propose_bets(
    race_id: str,
    win_probabilities: dict,
    budget: int = 0,
    bankroll: int = 0,
    preferred_bet_types: list[str] | None = None,
    max_bets: int | None = None,
) -> dict:
    """LLMが判断した勝率に基づき、期待値(EV)で買い目を選定し予算配分する.

    各馬の勝率からHarvilleモデルで組合せ確率を算出し、
    確率×推定オッズの期待値が1.0以上の買い目を選定する。

    Args:
        race_id: レースID (例: "20260201_05_11")
        win_probabilities: 各馬の勝率 (例: {"1": 0.25, "3": 0.18, "5": 0.12})
        budget: 予算（円）。従来モード。
        bankroll: 1日の総資金（円）。ダッチング配分モード。
        preferred_bet_types: 券種フィルタ。省略時は馬連・馬単・ワイド・三連複。
        max_bets: 買い目上限。省略時は10。

    Returns:
        提案結果:
        - race_summary: レース概要
        - proposed_bets: 提案買い目リスト（券種、馬番、金額、EV、合成オッズ）
        - total_amount: 合計金額
        - budget_remaining: 残り予算
        - analysis_comment: 分析ナラティブ
        - disclaimer: 免責事項
    """
    import requests
    from .race_data import _fetch_race_detail, _extract_race_conditions
    from .ai_prediction import get_ai_prediction
    from .pace_analysis import _get_running_styles
    from .risk_analysis import _assess_skip_recommendation

    # 確率のキーを int に変換（LLMがstrで渡す可能性）
    probs = {int(k): float(v) for k, v in win_probabilities.items()}

    # レースデータ取得（オッズが必要）
    race_detail = _fetch_race_detail(race_id)
    race = race_detail.get("race", {})
    runners_data = race_detail.get("runners", [])
    race_conditions = _extract_race_conditions(race)
    total_runners = race.get("horse_count", len(runners_data))

    # 見送りスコア算出
    ai_result = get_ai_prediction(race_id) or {}
    ai_predictions = []
    sources = ai_result.get("sources", [])
    if sources:
        ai_predictions = sources[0].get("predictions", [])
    skip = _assess_skip_recommendation(
        ai_predictions, total_runners, race_conditions,
        race.get("venue", ""), runners_data,
    )

    # ペース予想
    running_styles = _get_running_styles(race_id)
    front_runners = sum(1 for rs in running_styles if rs.get("running_style") == "逃げ")
    predicted_pace = _predict_pace(front_runners, total_runners) if running_styles else ""

    # AI合議
    from .bet_proposal import _assess_ai_consensus
    ai_consensus = _assess_ai_consensus(ai_predictions) if ai_predictions else ""

    return _propose_bets_impl(
        race_id=race_id,
        win_probabilities=probs,
        runners_data=runners_data,
        total_runners=total_runners,
        budget=budget,
        bankroll=bankroll,
        preferred_bet_types=preferred_bet_types,
        max_bets=max_bets,
        race_name=race.get("race_name", ""),
        race_conditions=race_conditions,
        venue=race.get("venue", ""),
        skip_score=skip.get("skip_score", 0),
        predicted_pace=predicted_pace,
        ai_consensus=ai_consensus,
    )
```

### Step 3: `tool_router.py` に新ツールを登録

`backend/agentcore/tool_router.py` を修正:

1. import に追加:
```python
from tools.race_analyzer import analyze_race_for_betting
from tools.ev_proposer import propose_bets
```

2. `all_tools` リストに追加:
```python
all_tools = [
    # ... 既存ツール ...
    analyze_race_for_betting,
    propose_bets,
]
```

3. `bet_focused` カテゴリに追加:
```python
"bet_focused": [
    analyze_bet_selection,
    analyze_odds_movement,
    generate_bet_proposal,
    analyze_race_for_betting,  # 追加
    propose_bets,              # 追加
    analyze_risk_factors,
    get_ai_prediction,
],
```

### Step 4: テスト実行

Run: `cd backend && uv run pytest tests/agentcore/test_race_analyzer.py tests/agentcore/test_ev_proposer.py -v`
Expected: PASS (all tests)

### Step 5: コミット

```bash
git add backend/agentcore/tools/race_analyzer.py backend/agentcore/tools/ev_proposer.py backend/agentcore/tool_router.py
git commit -m "feat: 新ツールの@tool登録とtool_router統合"
```

---

## Task 5: システムプロンプトの更新

**Files:**
- Modify: `backend/agentcore/prompts/bet_proposal.py`
- Modify: `backend/agentcore/agent.py`

### Step 1: `prompts/bet_proposal.py` を更新

現在のシステムプロンプトを、新しい2フェーズフローに対応させる。

```python
# backend/agentcore/prompts/bet_proposal.py

"""買い目提案専用システムプロンプト."""

BET_PROPOSAL_SYSTEM_PROMPT = """あなたは競馬の買い目提案を生成するAIアシスタント「馬券会議AI」です。

## 最重要ルール

1. **必ず以下の2ステップでツールを呼び出すこと。テキストだけの分析で応答してはならない。**
2. **ツールがエラーを返した場合、テキストで代替分析を行ってはならない。エラー内容をそのまま報告し、`---BET_PROPOSALS_JSON---` セパレータは出力しないこと。**
3. **ツールが正常に結果を返した場合、応答には必ず `---BET_PROPOSALS_JSON---` セパレータの後に提案結果のJSONを出力すること。**
4. **日本語で回答すること。**

## 手順

### Step 1: レース分析
`analyze_race_for_betting` ツールを呼び出し、レースの分析データを取得する。

### Step 2: 勝率の判断
分析データを元に、各馬の勝率を判断する。以下を考慮すること:
- ベース勝率（AI予想の統合値）を出発点にする
- ペース予想と脚質相性を見て、有利/不利な馬の確率を調整する
- スピード指数が突出している馬は確率を上げる
- 近走成績の好不調を考慮する
- 合計が1.0（100%）になるようにすること

### Step 3: 買い目提案生成
`propose_bets` ツールを、判断した勝率を渡して呼び出す。
ユーザーが予算(budget)またはbankrollを指定していれば引数に含める。
ユーザーが券種や買い目上限を指定していれば引数に含める。

### Step 4: 結果出力
提案結果を以下の形式で出力する:

```
分析コメント（結果の analysis_comment を元に簡潔にまとめる）

---BET_PROPOSALS_JSON---
{ツールが返したJSON全体}
```

## 禁止事項

- `analyze_race_for_betting` と `propose_bets` 以外のツール呼び出し
- ツールを呼ばずにテキストだけで買い目を提案すること
- ツールエラー時にフォールバックとしてテキスト分析を行うこと
- `---BET_PROPOSALS_JSON---` セパレータの省略
- 「おすすめ」「買うべき」といった推奨表現
- ギャンブルを促進する表現

## 免責事項

提案は「データ分析に基づく提案」としてフレーミングし、最終判断はユーザーに委ねること。
"""
```

### Step 2: `agent.py` を修正して新ツールを使う

`_get_agent()` 関数内で、bet_proposal タイプのとき新ツールを渡すように変更:

```python
# agent.py の bet_proposal ツール選定部分を修正
from tools.race_analyzer import analyze_race_for_betting
from tools.ev_proposer import propose_bets

# bet_proposal タイプの場合:
tools = [analyze_race_for_betting, propose_bets]
```

**注意:** `agent.py` の実装は他の request_type と絡むため、既存テストが壊れないか確認する必要あり。

### Step 3: 全テストが通ることを確認

Run: `cd backend && uv run pytest tests/ -v --timeout=60`
Expected: PASS (既存テスト + 新テスト全て)

### Step 4: コミット

```bash
git add backend/agentcore/prompts/bet_proposal.py backend/agentcore/agent.py
git commit -m "feat: システムプロンプトとエージェントを2フェーズ対応に更新"
```

---

## Task 6: キャッシュ・セパレータ互換性の対応

**Files:**
- Modify: `backend/agentcore/tools/ev_proposer.py`
- Modify: `backend/agentcore/agent.py` (response_utils連携)

### Step 1: テストを書く

```python
# backend/tests/agentcore/test_ev_proposer.py に追加

from tools.ev_proposer import get_last_ev_proposal_result

class TestProposalCache:
    """提案結果キャッシュのテスト."""

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_正常結果がキャッシュされる(self, mock_narrator):
        runners = _make_runners(6)
        win_probs = {1: 0.50, 2: 0.20, 3: 0.15, 4: 0.08, 5: 0.05, 6: 0.02}

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
        )

        # キャッシュが存在
        cached = get_last_ev_proposal_result()
        assert cached is not None
        assert cached["race_id"] == "test"

        # 2回目はクリアされる
        assert get_last_ev_proposal_result() is None
```

### Step 2: キャッシュ機能を実装

`backend/agentcore/tools/ev_proposer.py` 冒頭に追加:

```python
# セッション単位のキャッシュ（セパレータ復元用）
_last_ev_proposal_result: dict | None = None

def get_last_ev_proposal_result() -> dict | None:
    """キャッシュされた最新の提案結果を取得し、キャッシュをクリアする."""
    global _last_ev_proposal_result
    result = _last_ev_proposal_result
    _last_ev_proposal_result = None
    return result
```

`_propose_bets_impl` の最後で結果をキャッシュ:
```python
    global _last_ev_proposal_result
    _last_ev_proposal_result = result
    return result
```

### Step 3: テスト実行

Run: `cd backend && uv run pytest tests/agentcore/test_ev_proposer.py -v`
Expected: PASS

### Step 4: コミット

```bash
git add backend/agentcore/tools/ev_proposer.py backend/tests/agentcore/test_ev_proposer.py
git commit -m "feat: 提案結果キャッシュを追加（セパレータ互換性）"
```

---

## Task 7: 既存テストの確認と全体テスト実行

**Files:**
- 既存テスト全体

### Step 1: 全テスト実行

Run: `cd backend && uv run pytest tests/ -v --timeout=120`
Expected: PASS (既存テスト含む全テスト)

既存の `test_bet_proposal.py` の141テストは変更なしで通るはず（`generate_bet_proposal` は残しているため）。

### Step 2: 新テスト数の確認

Run: `cd backend && uv run pytest tests/agentcore/test_race_analyzer.py tests/agentcore/test_ev_proposer.py -v`
Expected: 新規テスト全てPASS

### Step 3: コミット（もし修正があれば）

```bash
git commit -m "test: 全テストの通過を確認"
```

---

## タスク一覧

| Task | 内容 | 新規テスト数 | ファイル |
|------|------|------------|---------|
| 1 | 重み付き統合確率 | 5 | race_analyzer.py, test_race_analyzer.py |
| 2 | analyze_race_for_betting 実装関数 | 3 | race_analyzer.py, test_race_analyzer.py |
| 3 | propose_bets 実装関数 (EV計算+買い目選定) | 7 | ev_proposer.py, test_ev_proposer.py |
| 4 | @tool登録 + tool_router統合 | 0 | race_analyzer.py, ev_proposer.py, tool_router.py |
| 5 | システムプロンプト + agent.py更新 | 0 | prompts/bet_proposal.py, agent.py |
| 6 | キャッシュ + セパレータ互換性 | 1 | ev_proposer.py, test_ev_proposer.py |
| 7 | 全体テスト確認 | 0 | - |
