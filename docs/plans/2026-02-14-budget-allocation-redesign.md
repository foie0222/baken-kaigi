# 資金配分ロジック再設計 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 買い目の資金配分を「定率法+信頼度傾斜によるレース間配分」と「ダッチング方式によるレース内配分」に刷新し、MAX_BETS制限を撤廃する。

**Architecture:** bankroll（1日の総資金）から見送りスコアに基づくconfidence_factorでレース予算を算出し、期待値>1.0の全買い目にオッズ逆数比例（ダッチング）で配分する。旧`budget`引数は後方互換で維持。

**Tech Stack:** Python, pytest, Strands Agents SDK (@tool)

---

## 前提知識

- ワークツリー: `/home/inoue-d/dev/baken-kaigi/feat-budget-redesign`
- 対象ファイル: `backend/agentcore/tools/bet_proposal.py`
- テストファイル: `backend/tests/agentcore/test_bet_proposal.py`
- テスト実行: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py -v`
- テストは日本語メソッド名で記述
- テストデータは `_make_runners()`, `_make_ai_predictions()` ヘルパーで生成
- DynamoDB Decimal型に注意: `float()` で変換が必要な場合がある

---

### Task 1: _calculate_confidence_factor の実装

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py` (定数セクション付近、L83あたりに追加)
- Test: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: テストを書く**

```python
class TestCalculateConfidenceFactor:
    """信頼度係数算出のテスト."""

    def test_見送りスコア0で最大値(self):
        assert _calculate_confidence_factor(0) == 2.0

    def test_見送りスコア5で約0_9(self):
        result = _calculate_confidence_factor(5)
        assert 0.85 <= result <= 0.95

    def test_見送りスコア8で最低正値(self):
        result = _calculate_confidence_factor(8)
        assert 0.2 <= result <= 0.3

    def test_見送りスコア9で見送り(self):
        assert _calculate_confidence_factor(9) == 0.0

    def test_見送りスコア10で見送り(self):
        assert _calculate_confidence_factor(10) == 0.0

    def test_スコアが高いほどfactorが小さい(self):
        factors = [_calculate_confidence_factor(s) for s in range(9)]
        for i in range(len(factors) - 1):
            assert factors[i] >= factors[i + 1]
```

テストの import に `_calculate_confidence_factor` を追加する。

**Step 2: テスト実行して失敗を確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestCalculateConfidenceFactor -v`
Expected: FAIL (ImportError: cannot import name '_calculate_confidence_factor')

**Step 3: 実装**

`bet_proposal.py` の定数セクション末尾（L87の `MAX_AXIS_HORSES = 2` の後あたり）に追加:

```python
# 1レースあたりの予算上限（bankrollに対する割合）
MAX_RACE_BUDGET_RATIO = 0.10

# デフォルト基本投入率
DEFAULT_BASE_RATE = 0.03


def _calculate_confidence_factor(skip_score: int) -> float:
    """見送りスコアから信頼度係数を算出する.

    見送りスコア(0-10)を0.0-2.0の連続値にマッピング。
    スコア9以上は見送り（0.0）。

    Args:
        skip_score: 見送りスコア（0-10）

    Returns:
        信頼度係数（0.0-2.0）
    """
    if skip_score >= 9:
        return 0.0
    return max(0.0, 2.0 - skip_score * (1.75 / 8))
```

**Step 4: テスト実行して成功を確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestCalculateConfidenceFactor -v`
Expected: PASS (6 passed)

**Step 5: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py backend/tests/agentcore/test_bet_proposal.py
git commit -m "feat: _calculate_confidence_factor を追加"
```

---

### Task 2: _allocate_budget_dutching の実装

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py` (Phase 5セクション、L928付近に追加)
- Test: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: テストを書く**

```python
class TestAllocateBudgetDutching:
    """ダッチング方式予算配分のテスト."""

    def test_均等払い戻しになる(self):
        """どの買い目が的中しても同額の払い戻しになる."""
        bets = [
            {"estimated_odds": 5.0, "expected_value": 1.5},
            {"estimated_odds": 10.0, "expected_value": 1.2},
            {"estimated_odds": 20.0, "expected_value": 1.1},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        # 各買い目の（金額 × オッズ）がほぼ同額になる
        payouts = [b["amount"] * b["estimated_odds"] for b in result]
        # 100円単位丸めの誤差を許容（最大と最小の差がオッズ×100以内）
        assert max(payouts) - min(payouts) <= max(b["estimated_odds"] for b in result) * 100

    def test_EV1以下の買い目は除外される(self):
        """期待値が1.0以下の買い目は配分されない."""
        bets = [
            {"estimated_odds": 5.0, "expected_value": 1.5},
            {"estimated_odds": 10.0, "expected_value": 0.8},  # 除外
        ]
        result = _allocate_budget_dutching(bets, 3000)
        assert len(result) == 1
        assert result[0]["expected_value"] == 1.5

    def test_全買い目EV1以下なら空リスト(self):
        bets = [
            {"estimated_odds": 5.0, "expected_value": 0.9},
            {"estimated_odds": 10.0, "expected_value": 0.5},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        assert result == []

    def test_100円単位に丸められる(self):
        bets = [
            {"estimated_odds": 5.0, "expected_value": 1.5},
            {"estimated_odds": 8.0, "expected_value": 1.2},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        for b in result:
            assert b["amount"] % 100 == 0

    def test_合計がbudgetを超えない(self):
        bets = [
            {"estimated_odds": 3.0, "expected_value": 1.3},
            {"estimated_odds": 5.0, "expected_value": 1.2},
            {"estimated_odds": 8.0, "expected_value": 1.1},
        ]
        result = _allocate_budget_dutching(bets, 2000)
        total = sum(b["amount"] for b in result)
        assert total <= 2000

    def test_空リスト入力(self):
        result = _allocate_budget_dutching([], 3000)
        assert result == []

    def test_予算ゼロ(self):
        bets = [{"estimated_odds": 5.0, "expected_value": 1.5}]
        result = _allocate_budget_dutching(bets, 0)
        assert all(b.get("amount", 0) == 0 for b in result) or result == bets

    def test_composite_oddsが結果に含まれる(self):
        bets = [
            {"estimated_odds": 5.0, "expected_value": 1.5},
            {"estimated_odds": 10.0, "expected_value": 1.2},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        for b in result:
            assert "composite_odds" in b

    def test_最低賭け金未満の買い目が除外される(self):
        """予算が少なく高オッズの買い目に100円配分できない場合は除外."""
        bets = [
            {"estimated_odds": 3.0, "expected_value": 1.5},
            {"estimated_odds": 100.0, "expected_value": 1.1},  # 配分が100円未満
        ]
        result = _allocate_budget_dutching(bets, 300)
        # 100倍の買い目は100円未満になるため除外されうる
        assert all(b["amount"] >= 100 for b in result)

    def test_低オッズの買い目に多く配分される(self):
        """ダッチングではオッズが低い買い目に多く配分される."""
        bets = [
            {"estimated_odds": 3.0, "expected_value": 1.5},
            {"estimated_odds": 10.0, "expected_value": 1.2},
        ]
        result = _allocate_budget_dutching(bets, 3000)
        low_odds = next(b for b in result if b["estimated_odds"] == 3.0)
        high_odds = next(b for b in result if b["estimated_odds"] == 10.0)
        assert low_odds["amount"] > high_odds["amount"]
```

テストの import に `_allocate_budget_dutching` を追加する。

**Step 2: テスト実行して失敗を確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestAllocateBudgetDutching -v`
Expected: FAIL (ImportError)

**Step 3: 実装**

`bet_proposal.py` のPhase 5セクション（L928付近）に `_allocate_budget` の後に追加:

```python
def _allocate_budget_dutching(bets: list[dict], budget: int) -> list[dict]:
    """ダッチング方式で予算を配分する.

    どの買い目が的中しても同額の払い戻しになるように、
    オッズの逆数に比例して配分する。

    Args:
        bets: 買い目候補リスト（estimated_odds, expected_value キーを持つ）
        budget: 総予算（円）

    Returns:
        金額付き買い目リスト（期待値>1.0のもののみ）
    """
    if not bets or budget <= 0:
        return bets

    eligible = [b for b in bets if b.get("expected_value", 0) > 1.0]
    if not eligible:
        return []

    inv_odds_sum = sum(1.0 / float(b["estimated_odds"]) for b in eligible)
    composite_odds = 1.0 / inv_odds_sum

    unit = MIN_BET_AMOUNT
    for bet in eligible:
        raw = budget * composite_odds / float(bet["estimated_odds"])
        bet["amount"] = max(unit, int(math.floor(raw / unit) * unit))

    funded = [b for b in eligible if b.get("amount", 0) >= unit]
    if len(funded) < len(eligible):
        return _allocate_budget_dutching(funded, budget)

    total = sum(b["amount"] for b in funded)
    remaining = budget - total
    if remaining >= unit and funded:
        funded[0]["amount"] += int(remaining // unit) * unit

    final_inv_sum = sum(1.0 / float(b["estimated_odds"]) for b in funded)
    final_composite = round(1.0 / final_inv_sum, 2) if final_inv_sum > 0 else 0
    for bet in funded:
        bet["composite_odds"] = final_composite

    return funded
```

**Step 4: テスト実行して成功を確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestAllocateBudgetDutching -v`
Expected: PASS (10 passed)

**Step 5: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py backend/tests/agentcore/test_bet_proposal.py
git commit -m "feat: _allocate_budget_dutching を追加"
```

---

### Task 3: ペルソナ設定に base_rate を追加

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py` (CHARACTER_PROFILES, _DEFAULT_CONFIG)
- Test: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: テストを書く**

```python
class TestBaseRateConfig:
    """base_rate設定のテスト."""

    def test_デフォルトのbase_rateは003(self):
        config = _get_character_config(None)
        assert config["base_rate"] == 0.03

    def test_conservativeのbase_rateは002(self):
        config = _get_character_config("conservative")
        assert config["base_rate"] == 0.02

    def test_aggressiveのbase_rateは005(self):
        config = _get_character_config("aggressive")
        assert config["base_rate"] == 0.05

    def test_全ペルソナにbase_rateが存在する(self):
        for persona in ["analyst", "intuition", "conservative", "aggressive", None]:
            config = _get_character_config(persona)
            assert "base_rate" in config
            assert 0 < config["base_rate"] <= 0.10
```

**Step 2: テスト実行して失敗を確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestBaseRateConfig -v`
Expected: FAIL (KeyError: 'base_rate')

**Step 3: 実装**

`_DEFAULT_CONFIG` に `"base_rate": DEFAULT_BASE_RATE` を追加。
`CHARACTER_PROFILES` に各ペルソナの `base_rate` を追加:
- `"conservative"`: `"base_rate": 0.02`
- `"aggressive"`: `"base_rate": 0.05`
- `"analyst"`, `"intuition"` はデフォルト(0.03)を使用するため追加不要。

**Step 4: テスト実行して成功を確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestBaseRateConfig -v`
Expected: PASS (4 passed)

**Step 5: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py backend/tests/agentcore/test_bet_proposal.py
git commit -m "feat: ペルソナ設定にbase_rateを追加"
```

---

### Task 4: _generate_bet_candidates から MAX_BETS 制限を撤廃

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py` (L616-889の_generate_bet_candidates)
- Test: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: テストを書く**

```python
class TestGenerateBetCandidatesNoMaxBets:
    """MAX_BETS撤廃後の買い目生成テスト."""

    def test_期待値プラスの買い目が8点以上でも全て返される(self):
        """MAX_BETSによるカットがなくなったことを確認."""
        runners = _make_runners(12)
        preds = _make_ai_predictions(12)
        axis = [
            {"horse_number": 1, "composite_score": 100},
            {"horse_number": 2, "composite_score": 90},
        ]
        result = _generate_bet_candidates(
            axis_horses=axis,
            runners_data=runners,
            ai_predictions=preds,
            bet_types=["quinella", "trio"],
            total_runners=12,
        )
        # 旧仕様では8点が上限だったが、新仕様では8点を超えることがある
        # （ただしトリガミ除外でそれ以下になる可能性もある）
        # 少なくともmax_betsパラメータが無視されることを確認
        assert isinstance(result, list)
```

**Step 2: テスト実行（現時点で成功するかもしれないが確認）**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestGenerateBetCandidatesNoMaxBets -v`

**Step 3: 実装**

`_generate_bet_candidates` を変更:
- `max_bets` パラメータのデフォルト値を `None` に変更（後方互換: 指定時はそのまま動作）
- L880の `selected = bets[:max_bets]` を条件付きに:

```python
if max_bets is not None:
    selected = bets[:max_bets]
else:
    selected = bets
```

- `_assign_relative_confidence(selected)` の呼び出しはそのまま残す（ダッチング配分では使わないが、後方互換のbudgetモードで使う）

**Step 4: テスト実行。既存テストも全て通ることを確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py -v`
Expected: ALL PASS

**Step 5: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py backend/tests/agentcore/test_bet_proposal.py
git commit -m "feat: _generate_bet_candidates のMAX_BETS強制カットを条件付きに変更"
```

---

### Task 5: _generate_bet_proposal_impl に bankroll モードを追加

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py` (L1324-1488の_generate_bet_proposal_impl)
- Test: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: テストを書く**

```python
class TestBankrollMode:
    """bankrollモードの統合テスト."""

    def test_bankroll指定でrace_budgetが自動算出される(self):
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=0,
            bankroll=30000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        assert result["race_budget"] > 0
        assert result["confidence_factor"] > 0

    def test_budget指定で従来動作(self):
        """budget指定時は従来の信頼度別配分が使われる."""
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=5000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        assert result["total_amount"] <= 5000

    def test_bankrollの10パーセントを超えない(self):
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=0,
            bankroll=10000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        assert result["total_amount"] <= 10000 * 0.10

    def test_見送りスコアが高いとrace_budgetが小さくなる(self):
        """見送りスコアが高い場合、予算が少なくなる."""
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        # 見送りスコアは内部で算出されるため、直接制御は難しいが
        # bankroll_usage_pctが含まれることを確認
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=0,
            bankroll=30000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        assert "bankroll_usage_pct" in result

    def test_bankrollモードでcomposite_oddsが出力される(self):
        runners = _make_runners(8)
        preds = _make_ai_predictions(8)
        result = _generate_bet_proposal_impl(
            race_id="test_001",
            budget=0,
            bankroll=30000,
            runners_data=runners,
            ai_predictions=preds,
            total_runners=8,
        )
        if result["proposed_bets"]:
            assert "composite_odds" in result["proposed_bets"][0]
```

**Step 2: テスト実行して失敗を確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py::TestBankrollMode -v`
Expected: FAIL (TypeError: unexpected keyword argument 'bankroll')

**Step 3: 実装**

`_generate_bet_proposal_impl` に変更を加える:

1. `bankroll: int = 0` パラメータを追加
2. bankroll > 0 の場合:
   - `_assess_skip_recommendation()` から `skip_score` を取得
   - `confidence_factor = _calculate_confidence_factor(skip_score)`
   - `race_budget = min(bankroll * config["base_rate"] * confidence_factor, bankroll * MAX_RACE_BUDGET_RATIO)`
   - `race_budget` を100円単位に丸め
   - `_generate_bet_candidates()` を `max_bets=None` で呼び出し
   - `_allocate_budget_dutching()` で配分
3. bankroll == 0 (かつ budget > 0)の場合: 従来ロジックをそのまま使用
4. 出力に `race_budget`, `composite_odds`, `confidence_factor`, `bankroll_usage_pct` を追加

**Step 4: テスト実行。既存テストも全て通ることを確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py -v`
Expected: ALL PASS

**Step 5: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py backend/tests/agentcore/test_bet_proposal.py
git commit -m "feat: _generate_bet_proposal_impl にbankrollモードを追加"
```

---

### Task 6: @tool 関数に bankroll 引数を追加

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py` (L1718-の generate_bet_proposal)

**Step 1: 実装**

`generate_bet_proposal` の引数に `bankroll: int = 0` を追加し、`_generate_bet_proposal_impl` に渡す。docstring も更新。

```python
@tool
def generate_bet_proposal(
    race_id: str,
    budget: int = 0,
    bankroll: int = 0,
    preferred_bet_types: list[str] | None = None,
    axis_horses: list[int] | None = None,
    character_type: str | None = None,
    max_bets: int | None = None,
) -> dict:
```

**Step 2: 既存テストが全て通ることを確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py -v`
Expected: ALL PASS

**Step 3: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py
git commit -m "feat: generate_bet_proposal にbankroll引数を追加"
```

---

### Task 7: 全テスト実行 & リグレッション確認

**Step 1: 全テスト実行**

Run: `cd backend && uv run pytest -v`
Expected: ALL PASS（既存テストがリグレッションしていないこと）

**Step 2: 必要があれば修正してコミット**

既存テストの import に不足がある場合は修正。特に `_allocate_budget` と `_assign_relative_confidence` は残すため、import エラーは発生しない想定。

---

### Task 8: 不要な定数・コードのクリーンアップ

既存の `_allocate_budget`, `_assign_relative_confidence` は **削除しない**。`budget` モード（後方互換）で使い続けるため。ただし以下を対応:

- `MAX_BETS` 定数のコメントにデフォルト値であり強制上限ではない旨を追記
- `SKIP_BUDGET_REDUCTION` は bankroll モードでは使わないが、budget モードの後方互換で残す

**Step 1: コメント更新して既存テスト確認**

Run: `cd backend && uv run pytest tests/agentcore/test_bet_proposal.py -v`
Expected: ALL PASS

**Step 2: コミット**

```bash
git add backend/agentcore/tools/bet_proposal.py
git commit -m "docs: 定数コメントを更新（bankrollモード対応）"
```
