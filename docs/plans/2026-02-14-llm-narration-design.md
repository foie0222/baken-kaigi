# LLMナレーション実装計画: 買い目提案の根拠テキスト生成

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 買い目提案の根拠テキスト（proposal_reasoning）を、テンプレート生成からHaiku 4.5によるLLM自然言語生成に置換する

**Architecture:** `_generate_proposal_reasoning()` の内部を3層に分割。`_build_narration_context()` でデータ整理 → `_invoke_haiku_narrator()` でBedrock API呼び出し → 失敗時は既存テンプレートにフォールバック。Phase 0-6のロジック、フロントエンド、エージェントプロンプトは一切変更しない。

**Tech Stack:** Python, Strands Agents SDK, Amazon Bedrock (Haiku 4.5), boto3, pytest

---

### Task 1: `_build_narration_context()` のテストを書く

**Files:**
- Test: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: テストクラスとテストメソッドを追加**

`test_bet_proposal.py` の末尾（`TestProposalReasoningInImpl` クラスの後）に追加:

```python
class TestBuildNarrationContext:
    """_build_narration_context のテスト."""

    def _make_reasoning_args(self):
        """TestProposalReasoning と同じテストデータ."""
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        axis_horses = [
            {"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 85.0},
            {"horse_number": 2, "horse_name": "テスト馬2", "composite_score": 72.0},
        ]
        difficulty = {"difficulty_stars": 3, "difficulty_label": "標準"}
        skip = {"skip_score": 3, "reasons": [], "recommendation": "参戦推奨"}
        bets = [
            {
                "bet_type": "quinella", "bet_type_name": "馬連",
                "horse_numbers": [1, 3], "expected_value": 1.8,
                "composite_odds": 8.5, "confidence": "high",
            },
        ]
        return dict(
            axis_horses=axis_horses,
            difficulty=difficulty,
            predicted_pace="ミドル",
            ai_consensus="概ね合意",
            skip=skip,
            bets=bets,
            preferred_bet_types=None,
            ai_predictions=ai_preds,
            runners_data=runners,
        )

    def test_必須キーが全て含まれる(self):
        """context dictに必要なキーが全て存在する."""
        args = self._make_reasoning_args()
        ctx = _build_narration_context(**args)
        required_keys = {
            "axis_horses", "partner_horses", "difficulty",
            "predicted_pace", "ai_consensus", "skip", "bets",
        }
        assert required_keys.issubset(ctx.keys())

    def test_軸馬にAI順位とスコアが付与される(self):
        """axis_horses の各要素に ai_rank, ai_score が含まれる."""
        args = self._make_reasoning_args()
        ctx = _build_narration_context(**args)
        for horse in ctx["axis_horses"]:
            assert "ai_rank" in horse
            assert "ai_score" in horse
            assert isinstance(horse["ai_rank"], int)
            assert isinstance(horse["ai_score"], float)

    def test_相手馬が抽出される(self):
        """betsから軸馬以外の馬番が partner_horses に含まれる."""
        args = self._make_reasoning_args()
        ctx = _build_narration_context(**args)
        assert len(ctx["partner_horses"]) > 0
        partner_numbers = {p["horse_number"] for p in ctx["partner_horses"]}
        axis_numbers = {1, 2}
        assert partner_numbers.isdisjoint(axis_numbers)

    def test_スピード指数の生データが含まれる(self):
        """speed_index_data が渡された場合、context に speed_index_raw が含まれる."""
        args = self._make_reasoning_args()
        args["speed_index_data"] = {
            "horses": {1: {"indices": [80, 85], "avg": 82.5}},
        }
        ctx = _build_narration_context(**args)
        assert "speed_index_raw" in ctx

    def test_スピード指数なしの場合はキーが存在しない(self):
        """speed_index_data が None の場合、speed_index_raw は含まれない."""
        args = self._make_reasoning_args()
        args["speed_index_data"] = None
        ctx = _build_narration_context(**args)
        assert "speed_index_raw" not in ctx

    def test_過去成績の生データが含まれる(self):
        """past_performance_data が渡された場合、context に past_performance_raw が含まれる."""
        args = self._make_reasoning_args()
        args["past_performance_data"] = {
            "horses": {1: {"results": [1, 3, 2]}},
        }
        ctx = _build_narration_context(**args)
        assert "past_performance_raw" in ctx

    def test_Decimal型データでもエラーにならない(self):
        """DynamoDB Decimal 型でも正常動作する."""
        args = self._make_reasoning_args()
        for pred in args["ai_predictions"]:
            pred["horse_number"] = Decimal(str(pred["horse_number"]))
            pred["rank"] = Decimal(str(pred["rank"]))
            pred["score"] = Decimal(str(pred["score"]))
        ctx = _build_narration_context(**args)
        assert len(ctx["axis_horses"]) == 2
```

**Step 2: import に `_build_narration_context` を追加**

`test_bet_proposal.py` の先頭にあるimport（L24付近）に追加:

```python
from tools.bet_proposal import (
    ...
    _build_narration_context,
    ...
)
```

**Step 3: テスト実行して失敗を確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestBuildNarrationContext -v`
Expected: FAIL（ImportError: `_build_narration_context` が存在しない）

**Step 4: コミット**

```bash
git add backend/tests/agentcore/test_bet_proposal.py
git commit -m "test: _build_narration_context の失敗テストを追加"
```

---

### Task 2: `_build_narration_context()` を実装する

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py`（`_generate_proposal_reasoning` の直前、L1604付近に追加）

**Step 1: 関数を実装**

`_generate_proposal_reasoning()` の直前に追加:

```python
def _build_narration_context(
    axis_horses: list[dict],
    difficulty: dict,
    predicted_pace: str,
    ai_consensus: str,
    skip: dict,
    bets: list[dict],
    preferred_bet_types: list[str] | None,
    ai_predictions: list[dict],
    runners_data: list[dict],
    speed_index_data: dict | None = None,
    past_performance_data: dict | None = None,
) -> dict:
    """LLMナレーション用のコンテキストdictを構築する."""
    # AI順位・スコアマップ（Decimal対策）
    ai_rank_map = {
        int(p.get("horse_number", 0)): int(p.get("rank", 99))
        for p in ai_predictions
    }
    ai_score_map = {
        int(p.get("horse_number", 0)): float(p.get("score", 0))
        for p in ai_predictions
    }
    runners_map = {r.get("horse_number"): r for r in runners_data}

    # 軸馬にAI情報を付与
    enriched_axis = []
    for ax in axis_horses:
        hn = ax["horse_number"]
        runner = runners_map.get(hn, {})
        enriched = {
            "horse_number": hn,
            "horse_name": ax.get("horse_name", ""),
            "composite_score": float(ax.get("composite_score", 0)),
            "ai_rank": ai_rank_map.get(hn, 99),
            "ai_score": ai_score_map.get(hn, 0),
            "odds": float(runner.get("odds", 0)) if runner.get("odds") else 0,
        }
        if speed_index_data:
            si_score = _calculate_speed_index_score(hn, speed_index_data)
            if si_score is not None:
                enriched["speed_index_score"] = float(si_score)
        if past_performance_data:
            form_s = _calculate_form_score(hn, past_performance_data)
            if form_s is not None:
                enriched["form_score"] = float(form_s)
        enriched_axis.append(enriched)

    # 相手馬を抽出
    axis_numbers = {ax["horse_number"] for ax in axis_horses}
    partner_numbers_seen = []
    for bet in bets:
        for hn in bet.get("horse_numbers", []):
            if hn not in axis_numbers and hn not in partner_numbers_seen:
                partner_numbers_seen.append(hn)

    partners = []
    for hn in partner_numbers_seen[:MAX_PARTNERS]:
        runner = runners_map.get(hn, {})
        ev_vals = [
            b.get("expected_value", 0) for b in bets
            if hn in b.get("horse_numbers", [])
        ]
        partners.append({
            "horse_number": hn,
            "horse_name": runner.get("horse_name", ""),
            "ai_rank": ai_rank_map.get(hn, 99),
            "max_expected_value": max(ev_vals) if ev_vals else 0,
        })

    ctx = {
        "axis_horses": enriched_axis,
        "partner_horses": partners,
        "difficulty": difficulty,
        "predicted_pace": predicted_pace,
        "ai_consensus": ai_consensus,
        "skip": skip,
        "bets": [
            {
                "bet_type_name": b.get("bet_type_name", ""),
                "horse_numbers": b.get("horse_numbers", []),
                "expected_value": b.get("expected_value", 0),
                "composite_odds": float(b.get("composite_odds", 0)),
                "confidence": b.get("confidence", ""),
            }
            for b in bets
        ],
    }
    if preferred_bet_types:
        ctx["preferred_bet_types"] = preferred_bet_types
    if speed_index_data:
        ctx["speed_index_raw"] = speed_index_data
    if past_performance_data:
        ctx["past_performance_raw"] = past_performance_data
    return ctx
```

**Step 2: テスト実行して成功を確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestBuildNarrationContext -v`
Expected: ALL PASS

**Step 3: 既存テストが壊れていないことを確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest tests/agentcore/test_bet_proposal.py -v --tb=short 2>&1 | tail -20`
Expected: 既存テスト全てPASS

**Step 4: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py backend/tests/agentcore/test_bet_proposal.py
git commit -m "feat: _build_narration_context() を実装"
```

---

### Task 3: `_invoke_haiku_narrator()` のテストを書く

**Files:**
- Test: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: テストクラスを追加**

```python
class TestInvokeHaikuNarrator:
    """_invoke_haiku_narrator のテスト."""

    def _make_context(self):
        """最小限のコンテキスト."""
        return {
            "axis_horses": [
                {
                    "horse_number": 1, "horse_name": "テスト馬1",
                    "composite_score": 85.0, "ai_rank": 1, "ai_score": 500,
                    "odds": 3.4,
                },
            ],
            "partner_horses": [
                {"horse_number": 3, "horse_name": "テスト馬3", "ai_rank": 2, "max_expected_value": 1.5},
            ],
            "difficulty": {"difficulty_stars": 3, "difficulty_label": "標準"},
            "predicted_pace": "ミドル",
            "ai_consensus": "概ね合意",
            "skip": {"skip_score": 2, "reasons": [], "recommendation": "参戦推奨"},
            "bets": [
                {
                    "bet_type_name": "馬連", "horse_numbers": [1, 3],
                    "expected_value": 1.5, "composite_odds": 8.5, "confidence": "high",
                },
            ],
        }

    @patch("tools.bet_proposal._call_bedrock_haiku")
    def test_正常時にLLM生成テキストを返す(self, mock_call):
        """Bedrock正常時はLLM生成テキストを返す."""
        mock_call.return_value = (
            "【軸馬選定】1番テスト馬1を軸に。AI指数1位で信頼度が高い\n\n"
            "【券種】レース難易度★3のため馬連を選定\n\n"
            "【組み合わせ】相手は3番テスト馬3。期待値1.5で妙味あり\n\n"
            "【リスク】AI合議「概ね合意」。見送りスコア2/10で積極参戦レベル"
        )
        result = _invoke_haiku_narrator(self._make_context())
        assert "【軸馬選定】" in result
        assert "【券種】" in result
        assert "【組み合わせ】" in result
        assert "【リスク】" in result
        mock_call.assert_called_once()

    @patch("tools.bet_proposal._call_bedrock_haiku")
    def test_LLMが4セクション返さない場合はNoneを返す(self, mock_call):
        """LLMが不完全な出力をした場合はNone（フォールバック用）."""
        mock_call.return_value = "不完全な回答です"
        result = _invoke_haiku_narrator(self._make_context())
        assert result is None

    @patch("tools.bet_proposal._call_bedrock_haiku")
    def test_API例外時はNoneを返す(self, mock_call):
        """Bedrock APIエラー時はNone（フォールバック用）."""
        mock_call.side_effect = Exception("ServiceUnavailable")
        result = _invoke_haiku_narrator(self._make_context())
        assert result is None
```

**Step 2: import を追加**

```python
from unittest.mock import patch
from tools.bet_proposal import (
    ...
    _invoke_haiku_narrator,
    ...
)
```

**Step 3: テスト実行して失敗を確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestInvokeHaikuNarrator -v`
Expected: FAIL（ImportError: `_invoke_haiku_narrator` が存在しない）

**Step 4: コミット**

```bash
git add backend/tests/agentcore/test_bet_proposal.py
git commit -m "test: _invoke_haiku_narrator の失敗テストを追加"
```

---

### Task 4: `_call_bedrock_haiku()` と `_invoke_haiku_narrator()` を実装する

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py`

**Step 1: ファイル先頭の import に `json`, `logging`, `boto3` を追加**

`bet_proposal.py` の import セクション（L7付近）に追加:

```python
import json
import logging
import math

import boto3
import requests
```

**Step 2: ナレーション用定数とシステムプロンプトを追加**

定数セクション（`MAX_AXIS_HORSES` 等の定義の後、L87付近）に追加:

```python
# LLMナレーション: モデルID
NARRATOR_MODEL_ID = "jp.anthropic.claude-haiku-4-5-20251001-v1:0"

# LLMナレーション: システムプロンプト
NARRATOR_SYSTEM_PROMPT = """あなたは競馬データアナリストです。
以下のデータを元に、買い目提案の根拠を4セクションで書いてください。

## 出力フォーマット（厳守）
以下の4セクションを改行区切りで出力すること。セクション名は【】で囲む。
各セクション以外のテキストは出力しないこと。

【軸馬選定】...

【券種】...

【組み合わせ】...

【リスク】...

## ルール
- 4セクション（【軸馬選定】【券種】【組み合わせ】【リスク】）は必須
- 各セクション1〜3文で簡潔に
- データの数値（AI指数順位・スコア・オッズ等）は正確に引用すること
- レースごとの特徴や注目ポイントを自分の言葉で解説すること
- 過去成績がある場合は、具体的な着順推移や距離適性に言及
- スピード指数がある場合は、指数の位置づけや推移に言及
- 「おすすめ」「買うべき」等の推奨表現は禁止

## トーン制御
- AI合議が「明確な上位」「概ね合意」→ 確信的に語る
- AI合議が「やや接戦」「混戦」→ 慎重に、リスクにも触れながら語る
- 見送りスコア≥7 → 警戒的に、予算削減を強調"""

logger = logging.getLogger(__name__)
```

**Step 3: `_call_bedrock_haiku()` を実装**

`_build_narration_context()` の直後に追加:

```python
def _call_bedrock_haiku(system_prompt: str, user_message: str) -> str:
    """Bedrock Converse API で Haiku を呼び出す."""
    client = boto3.client("bedrock-runtime", region_name="ap-northeast-1")
    response = client.converse(
        modelId=NARRATOR_MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_message}]}],
        inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
    )
    return response["output"]["message"]["content"][0]["text"]
```

**Step 4: `_invoke_haiku_narrator()` を実装**

```python
def _invoke_haiku_narrator(context: dict) -> str | None:
    """コンテキストを元にHaikuでナレーションを生成する.

    Returns:
        生成されたテキスト。4セクション揃わない場合やエラー時は None。
    """
    try:
        user_message = json.dumps(context, ensure_ascii=False, default=str)
        text = _call_bedrock_haiku(NARRATOR_SYSTEM_PROMPT, user_message)
        # 4セクション全て含まれるか検証
        required = ["【軸馬選定】", "【券種】", "【組み合わせ】", "【リスク】"]
        if all(section in text for section in required):
            return text.strip()
        logger.warning("LLMナレーション: 4セクション不足。フォールバックへ。")
        return None
    except Exception:
        logger.exception("LLMナレーション: Bedrock呼び出し失敗。フォールバックへ。")
        return None
```

**Step 5: テスト実行して成功を確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestInvokeHaikuNarrator -v`
Expected: ALL PASS

**Step 6: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py
git commit -m "feat: _call_bedrock_haiku() と _invoke_haiku_narrator() を実装"
```

---

### Task 5: `_generate_proposal_reasoning()` をLLM呼び出しに置換する

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py`（L1604-1683の `_generate_proposal_reasoning()` を変更）

**Step 1: 既存関数をリネーム**

既存の `_generate_proposal_reasoning()` を `_generate_proposal_reasoning_template()` にリネーム。

**Step 2: 新しい `_generate_proposal_reasoning()` を実装**

リネーム後の関数の直後に、同じシグネチャで新関数を追加:

```python
def _generate_proposal_reasoning(
    axis_horses: list[dict],
    difficulty: dict,
    predicted_pace: str,
    ai_consensus: str,
    skip: dict,
    bets: list[dict],
    preferred_bet_types: list[str] | None,
    ai_predictions: list[dict],
    runners_data: list[dict],
    skip_gate_threshold: int = SKIP_GATE_THRESHOLD,
    speed_index_data: dict | None = None,
    past_performance_data: dict | None = None,
) -> str:
    """提案根拠テキストを4セクションで生成する（LLMナレーション版）."""
    context = _build_narration_context(
        axis_horses=axis_horses,
        difficulty=difficulty,
        predicted_pace=predicted_pace,
        ai_consensus=ai_consensus,
        skip=skip,
        bets=bets,
        preferred_bet_types=preferred_bet_types,
        ai_predictions=ai_predictions,
        runners_data=runners_data,
        speed_index_data=speed_index_data,
        past_performance_data=past_performance_data,
    )
    result = _invoke_haiku_narrator(context)
    if result is not None:
        return result
    # フォールバック: テンプレート生成
    return _generate_proposal_reasoning_template(
        axis_horses=axis_horses,
        difficulty=difficulty,
        predicted_pace=predicted_pace,
        ai_consensus=ai_consensus,
        skip=skip,
        bets=bets,
        preferred_bet_types=preferred_bet_types,
        ai_predictions=ai_predictions,
        runners_data=runners_data,
        skip_gate_threshold=skip_gate_threshold,
        speed_index_data=speed_index_data,
        past_performance_data=past_performance_data,
    )
```

**Step 3: テスト実行**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest tests/agentcore/test_bet_proposal.py -v --tb=short 2>&1 | tail -30`
Expected: 既存テストの一部が失敗する可能性あり（Bedrock呼び出しのため）→ Task 6 で対処

**Step 4: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py
git commit -m "feat: _generate_proposal_reasoning をLLMナレーション版に置換"
```

---

### Task 6: 既存テストをLLMナレーション対応に更新する

**Files:**
- Modify: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: `TestProposalReasoning` のテストに Bedrock モックを適用**

既存の `TestProposalReasoning` クラスのテストが Bedrock API を呼ばないよう、`_call_bedrock_haiku` をモックする。クラスレベルのデコレータで一括適用:

```python
@patch("tools.bet_proposal._call_bedrock_haiku", return_value=None)
class TestProposalReasoning:
    """_generate_proposal_reasoning のテスト.

    _call_bedrock_haiku を None で返すモックにすることで、
    常にフォールバック（テンプレート生成）が使われる。
    既存テストの期待値はテンプレート生成の出力に合致しているため、そのまま維持。
    """

    def _make_reasoning_args(self, *, skip_score: int = 3, preferred_bet_types=None):
        # ... 既存のまま

    def test_提案根拠が文字列を返す(self, mock_haiku):
        # ... 既存のまま（mock_haiku 引数を追加するだけ）
```

各テストメソッドのシグネチャに `mock_haiku` 引数を追加（`@patch` クラスデコレータにより自動注入）。テストの中身は変更不要。

**Step 2: `TestProposalReasoningInImpl` も同様にモック適用**

```python
@patch("tools.bet_proposal._call_bedrock_haiku", return_value=None)
class TestProposalReasoningInImpl:
```

**Step 3: テスト実行して全テスト成功を確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest tests/agentcore/test_bet_proposal.py -v --tb=short 2>&1 | tail -30`
Expected: ALL PASS

**Step 4: 全テスト実行**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest --tb=short 2>&1 | tail -10`
Expected: ALL PASS（2000件以上）

**Step 5: コミット**

```bash
git add backend/tests/agentcore/test_bet_proposal.py
git commit -m "test: 既存テストにBedrock Haikuモックを適用"
```

---

### Task 7: LLM→テンプレートフォールバックの統合テストを追加

**Files:**
- Test: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: 統合テストクラスを追加**

```python
class TestLlmNarrationIntegration:
    """LLMナレーション→テンプレートフォールバックの統合テスト."""

    def _make_reasoning_args(self):
        runners = _make_runners(6)
        ai_preds = _make_ai_predictions(6)
        return dict(
            axis_horses=[
                {"horse_number": 1, "horse_name": "テスト馬1", "composite_score": 85.0},
            ],
            difficulty={"difficulty_stars": 3, "difficulty_label": "標準"},
            predicted_pace="ミドル",
            ai_consensus="概ね合意",
            skip={"skip_score": 3, "reasons": [], "recommendation": "参戦推奨"},
            bets=[
                {
                    "bet_type": "quinella", "bet_type_name": "馬連",
                    "horse_numbers": [1, 3], "expected_value": 1.8,
                    "composite_odds": 8.5, "confidence": "high",
                },
            ],
            preferred_bet_types=None,
            ai_predictions=ai_preds,
            runners_data=runners,
        )

    @patch("tools.bet_proposal._call_bedrock_haiku")
    def test_LLM成功時はLLM生成テキストが使われる(self, mock_call):
        """Haiku正常時はLLM生成テキストが返る."""
        llm_text = (
            "【軸馬選定】1番テスト馬1（AI指数1位）を軸に据えた。前走の走りが安定\n\n"
            "【券種】難易度★3の標準レース。馬連で勝負\n\n"
            "【組み合わせ】相手は3番テスト馬3。期待値1.8と高い\n\n"
            "【リスク】AI合議「概ね合意」。積極参戦レベル"
        )
        mock_call.return_value = llm_text
        result = _generate_proposal_reasoning(**self._make_reasoning_args())
        assert "前走の走りが安定" in result  # LLM固有のテキスト

    @patch("tools.bet_proposal._call_bedrock_haiku")
    def test_LLM失敗時はテンプレートにフォールバックする(self, mock_call):
        """Haiku APIエラー時はテンプレート生成にフォールバック."""
        mock_call.side_effect = Exception("ServiceUnavailable")
        result = _generate_proposal_reasoning(**self._make_reasoning_args())
        assert "【軸馬選定】" in result
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("tools.bet_proposal._call_bedrock_haiku")
    def test_LLMが不完全な出力をした場合はテンプレートにフォールバック(self, mock_call):
        """4セクション揃わない場合はテンプレートにフォールバック."""
        mock_call.return_value = "中途半端な回答"
        result = _generate_proposal_reasoning(**self._make_reasoning_args())
        assert "【軸馬選定】" in result
        assert "【リスク】" in result
```

**Step 2: テスト実行**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestLlmNarrationIntegration -v`
Expected: ALL PASS

**Step 3: 全テスト最終確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/llm-narration/backend && uv run pytest --tb=short 2>&1 | tail -10`
Expected: ALL PASS

**Step 4: コミット**

```bash
git add backend/tests/agentcore/test_bet_proposal.py
git commit -m "test: LLMナレーション統合テストを追加"
```

---

### Task 8: 設計ドキュメントを更新してPR作成

**Files:**
- Modify: `docs/plans/2026-02-14-llm-narration-design.md`（実装完了ステータスに更新）

**Step 1: PR作成**

```bash
git push -u origin feature/llm-narration
gh pr create --title "feat: 買い目提案の根拠テキストをLLMナレーションに置換" --body "$(cat <<'EOF'
## Summary
- 買い目提案の根拠テキスト（proposal_reasoning）をHaiku 4.5による自然言語生成に置換
- Phase 0-6の既存ロジックは一切変更なし
- Bedrock API失敗時は既存テンプレートにフォールバック

## 変更内容
- `_build_narration_context()`: LLM用コンテキスト構築
- `_invoke_haiku_narrator()`: Bedrock Converse API呼び出し
- `_generate_proposal_reasoning()`: LLM優先・テンプレートフォールバック
- 既存テストにBedrockモック適用、統合テスト追加

## Test plan
- [ ] 全既存テストがパスすること
- [ ] LLMナレーション関連の新規テストがパスすること
- [ ] 本番環境で提案実行し、根拠テキストが自然言語で生成されることを確認

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
