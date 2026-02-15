# 確率/EVフィルター設定 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ユーザーが確率範囲とEV範囲をスライダーで設定し、EV proposerの候補フィルタリングに反映する。

**Architecture:** BettingPreference値オブジェクトに4つのfloatフィールドを追加し、DynamoDBに保存。API経由でフロントエンドから設定。AgentCore起動時にev_proposerにフィルター値を注入し、_generate_ev_candidatesのフィルタ条件で使用する。

**Tech Stack:** Python 3.12 (backend), React + TypeScript (frontend), DynamoDB (persistence), Strands SDK (AgentCore)

---

### Task 1: BettingPreference 値オブジェクトにフィルターフィールド追加

**Files:**
- Modify: `backend/src/domain/value_objects/betting_preference.py`
- Test: `backend/tests/domain/test_betting_preference_enums.py`

**Step 1: 失敗するテストを書く**

`backend/tests/domain/test_betting_preference_enums.py` の `TestBettingPreference` クラスに以下を追加:

```python
def test_フィルターフィールド付きで作成できる(self):
    pref = BettingPreference(
        bet_type_preference=BetTypePreference.AUTO,
        min_probability=0.05,
        max_probability=0.30,
        min_ev=1.5,
        max_ev=5.0,
    )
    assert pref.min_probability == 0.05
    assert pref.max_probability == 0.30
    assert pref.min_ev == 1.5
    assert pref.max_ev == 5.0

def test_デフォルト値にフィルターフィールドが含まれる(self):
    pref = BettingPreference.default()
    assert pref.min_probability == 0.01
    assert pref.max_probability == 0.50
    assert pref.min_ev == 1.0
    assert pref.max_ev == 10.0

def test_to_dictにフィルターフィールドが含まれる(self):
    pref = BettingPreference(
        bet_type_preference=BetTypePreference.AUTO,
        min_probability=0.05,
        max_probability=0.30,
        min_ev=1.5,
        max_ev=5.0,
    )
    d = pref.to_dict()
    assert d == {
        "bet_type_preference": "auto",
        "min_probability": 0.05,
        "max_probability": 0.30,
        "min_ev": 1.5,
        "max_ev": 5.0,
    }

def test_from_dictでフィルターフィールドを復元できる(self):
    data = {
        "bet_type_preference": "trio_focused",
        "min_probability": 0.03,
        "max_probability": 0.25,
        "min_ev": 1.2,
        "max_ev": 8.0,
    }
    pref = BettingPreference.from_dict(data)
    assert pref.min_probability == 0.03
    assert pref.max_probability == 0.25
    assert pref.min_ev == 1.2
    assert pref.max_ev == 8.0

def test_from_dictでフィルターフィールドなしはデフォルト値(self):
    data = {"bet_type_preference": "auto"}
    pref = BettingPreference.from_dict(data)
    assert pref.min_probability == 0.01
    assert pref.max_probability == 0.50
    assert pref.min_ev == 1.0
    assert pref.max_ev == 10.0
```

**Step 2: テストが失敗することを確認**

Run: `cd backend && uv run pytest tests/domain/test_betting_preference_enums.py -v`
Expected: FAIL (TypeError: unexpected keyword argument)

**Step 3: 実装**

`backend/src/domain/value_objects/betting_preference.py` を以下のように修正:

```python
"""好み設定値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import BetTypePreference


@dataclass(frozen=True)
class BettingPreference:
    """ユーザーの馬券購入好み設定."""

    bet_type_preference: BetTypePreference
    min_probability: float = 0.01
    max_probability: float = 0.50
    min_ev: float = 1.0
    max_ev: float = 10.0

    @classmethod
    def default(cls) -> BettingPreference:
        """デフォルト値で作成する."""
        return cls(
            bet_type_preference=BetTypePreference.AUTO,
        )

    def to_dict(self) -> dict:
        """辞書に変換する."""
        return {
            "bet_type_preference": self.bet_type_preference.value,
            "min_probability": self.min_probability,
            "max_probability": self.max_probability,
            "min_ev": self.min_ev,
            "max_ev": self.max_ev,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> BettingPreference:
        """辞書から復元する."""
        if not data:
            return cls.default()
        return cls(
            bet_type_preference=BetTypePreference(data.get("bet_type_preference", "auto")),
            min_probability=float(data.get("min_probability", 0.01)),
            max_probability=float(data.get("max_probability", 0.50)),
            min_ev=float(data.get("min_ev", 1.0)),
            max_ev=float(data.get("max_ev", 10.0)),
        )
```

**Step 4: テストが通ることを確認**

Run: `cd backend && uv run pytest tests/domain/test_betting_preference_enums.py -v`
Expected: ALL PASS

**Step 5: 既存テストが壊れていないことを確認**

Run: `cd backend && uv run pytest tests/domain/ tests/infrastructure/repositories/test_dynamodb_agent_repository_serialization.py -v --ignore=tests/batch`
Expected: ALL PASS（デフォルト値があるので既存テストはそのまま通る）

**Step 6: コミット**

```bash
git add backend/src/domain/value_objects/betting_preference.py backend/tests/domain/test_betting_preference_enums.py
git commit -m "feat: BettingPreferenceにmin/max確率・EVフィルターフィールド追加"
```

---

### Task 2: APIハンドラーにフィルターバリデーション追加

**Files:**
- Modify: `backend/src/api/handlers/agent.py:169-176`
- Test: `backend/tests/api/handlers/test_agent.py`

**Step 1: 失敗するテストを書く**

`backend/tests/api/handlers/test_agent.py` の `TestUpdateAgentPreference` クラスに以下を追加:

```python
def test_フィルター設定を更新できる(self):
    create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ", "base_style": "solid"})
    agent_handler(create_event, None)

    event = _make_event(
        method="PUT",
        path="/agents/me",
        body={
            "betting_preference": {
                "bet_type_preference": "auto",
                "min_probability": 0.05,
                "max_probability": 0.30,
                "min_ev": 1.5,
                "max_ev": 5.0,
            },
        },
    )
    response = agent_handler(event, None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["betting_preference"]["min_probability"] == 0.05
    assert body["betting_preference"]["max_probability"] == 0.30
    assert body["betting_preference"]["min_ev"] == 1.5
    assert body["betting_preference"]["max_ev"] == 5.0

def test_min_probabilityが範囲外で400(self):
    create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ", "base_style": "solid"})
    agent_handler(create_event, None)

    event = _make_event(
        method="PUT",
        path="/agents/me",
        body={
            "betting_preference": {
                "min_probability": 0.0,
            },
        },
    )
    response = agent_handler(event, None)
    assert response["statusCode"] == 400

def test_min_probabilityがmax_probabilityより大きいと400(self):
    create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ", "base_style": "solid"})
    agent_handler(create_event, None)

    event = _make_event(
        method="PUT",
        path="/agents/me",
        body={
            "betting_preference": {
                "min_probability": 0.30,
                "max_probability": 0.10,
            },
        },
    )
    response = agent_handler(event, None)
    assert response["statusCode"] == 400

def test_min_evが範囲外で400(self):
    create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ", "base_style": "solid"})
    agent_handler(create_event, None)

    event = _make_event(
        method="PUT",
        path="/agents/me",
        body={
            "betting_preference": {
                "min_ev": 0.5,
            },
        },
    )
    response = agent_handler(event, None)
    assert response["statusCode"] == 400

def test_min_evがmax_evより大きいと400(self):
    create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ", "base_style": "solid"})
    agent_handler(create_event, None)

    event = _make_event(
        method="PUT",
        path="/agents/me",
        body={
            "betting_preference": {
                "min_ev": 8.0,
                "max_ev": 2.0,
            },
        },
    )
    response = agent_handler(event, None)
    assert response["statusCode"] == 400
```

**Step 2: テストが失敗することを確認**

Run: `cd backend && uv run pytest tests/api/handlers/test_agent.py::TestUpdateAgentPreference -v`
Expected: 新しいテストが FAIL（バリデーションが未実装のため400が返らない）

**Step 3: 実装**

`backend/src/api/handlers/agent.py` の `_update_agent` 関数内、betting_preference バリデーション部分（169行目付近）を以下に差し替え:

```python
# betting_preference バリデーション
if betting_preference is not None:
    if not isinstance(betting_preference, dict):
        return bad_request_response("betting_preference must be an object", event=event)
    btp = betting_preference.get("bet_type_preference")
    if btp is not None and btp not in _VALID_BET_TYPE_PREFERENCES:
        return bad_request_response(
            f"bet_type_preference must be one of: {', '.join(_VALID_BET_TYPE_PREFERENCES)}", event=event
        )
    # 確率フィルター バリデーション
    min_prob = betting_preference.get("min_probability")
    max_prob = betting_preference.get("max_probability")
    if min_prob is not None:
        if not isinstance(min_prob, (int, float)) or not (0.01 <= min_prob <= 0.50):
            return bad_request_response("min_probability must be between 0.01 and 0.50", event=event)
    if max_prob is not None:
        if not isinstance(max_prob, (int, float)) or not (0.01 <= max_prob <= 0.50):
            return bad_request_response("max_probability must be between 0.01 and 0.50", event=event)
    if min_prob is not None and max_prob is not None and min_prob > max_prob:
        return bad_request_response("min_probability must be <= max_probability", event=event)
    # EVフィルター バリデーション
    min_ev = betting_preference.get("min_ev")
    max_ev = betting_preference.get("max_ev")
    if min_ev is not None:
        if not isinstance(min_ev, (int, float)) or not (1.0 <= min_ev <= 10.0):
            return bad_request_response("min_ev must be between 1.0 and 10.0", event=event)
    if max_ev is not None:
        if not isinstance(max_ev, (int, float)) or not (1.0 <= max_ev <= 10.0):
            return bad_request_response("max_ev must be between 1.0 and 10.0", event=event)
    if min_ev is not None and max_ev is not None and min_ev > max_ev:
        return bad_request_response("min_ev must be <= max_ev", event=event)
```

**Step 4: テストが通ることを確認**

Run: `cd backend && uv run pytest tests/api/handlers/test_agent.py -v`
Expected: ALL PASS

**Step 5: コミット**

```bash
git add backend/src/api/handlers/agent.py backend/tests/api/handlers/test_agent.py
git commit -m "feat: APIハンドラーに確率/EVフィルターのバリデーション追加"
```

---

### Task 3: EV proposer にフィルター値の読み取りとフィルタリング反映

**Files:**
- Modify: `backend/agentcore/tools/ev_proposer.py`
- Test: `backend/tests/agentcore/test_ev_proposer.py`

**Step 1: 失敗するテストを書く**

`backend/tests/agentcore/test_ev_proposer.py` に以下のインポートを追加:

```python
from tools.ev_proposer import (
    _propose_bets_impl,
    _make_odds_key,
    _lookup_real_odds,
    _resolve_bet_types,
    _resolve_ev_filter,
    DEFAULT_BET_TYPES,
)
```

そしてファイル末尾に新しいテストクラスを追加:

```python
class TestResolveEvFilter:
    """_resolve_ev_filter のテスト."""

    def test_Noneの場合はデフォルト値(self):
        result = _resolve_ev_filter(None)
        assert result == (0.01, 0.50, 1.0, 10.0)

    def test_空辞書の場合はデフォルト値(self):
        result = _resolve_ev_filter({})
        assert result == (0.01, 0.50, 1.0, 10.0)

    def test_フィルター値が反映される(self):
        pref = {
            "bet_type_preference": "auto",
            "min_probability": 0.05,
            "max_probability": 0.30,
            "min_ev": 1.5,
            "max_ev": 5.0,
        }
        result = _resolve_ev_filter(pref)
        assert result == (0.05, 0.30, 1.5, 5.0)

    def test_一部だけ指定の場合は残りデフォルト(self):
        pref = {"min_probability": 0.03}
        result = _resolve_ev_filter(pref)
        assert result == (0.03, 0.50, 1.0, 10.0)


class TestEvFilterIntegration:
    """確率/EVフィルターの統合テスト."""

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_max_probabilityで高確率の組合せが除外される(self, mock_narrator):
        """max_probability=0.10 で確率10%超の組合せは除外される."""
        runners = _make_runners(4)
        # 馬1の勝率50%。単勝1番は確率50%でmax超→除外されるはず
        win_probs = {1: 0.50, 2: 0.25, 3: 0.15, 4: 0.10}

        from tools.ev_proposer import set_betting_preference
        set_betting_preference({
            "min_probability": 0.01,
            "max_probability": 0.10,
            "min_ev": 1.0,
            "max_ev": 10.0,
        })

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=4,
            budget=5000,
            preferred_bet_types=["win"],
            all_odds=_make_all_odds(runners),
        )

        # 確率10%超のwinベットは除外される
        for bet in result["proposed_bets"]:
            assert bet["combination_probability"] <= 0.10

        set_betting_preference(None)  # クリーンアップ

    @patch("tools.ev_proposer._invoke_haiku_narrator", return_value=None)
    def test_max_evで高EV組合せが除外される(self, mock_narrator):
        """max_ev=3.0 で EV > 3.0 の組合せは除外される."""
        runners = _make_runners(6)
        win_probs = {1: 0.40, 2: 0.25, 3: 0.15, 4: 0.10, 5: 0.06, 6: 0.04}

        from tools.ev_proposer import set_betting_preference
        set_betting_preference({
            "min_probability": 0.01,
            "max_probability": 0.50,
            "min_ev": 1.0,
            "max_ev": 3.0,
        })

        result = _propose_bets_impl(
            race_id="test",
            win_probabilities=win_probs,
            runners_data=runners,
            total_runners=6,
            budget=5000,
            all_odds=_make_all_odds(runners),
        )

        for bet in result["proposed_bets"]:
            assert bet["expected_value"] <= 3.0

        set_betting_preference(None)  # クリーンアップ
```

**Step 2: テストが失敗することを確認**

Run: `cd backend && uv run pytest tests/agentcore/test_ev_proposer.py::TestResolveEvFilter -v`
Expected: FAIL (ImportError: cannot import name '_resolve_ev_filter')

**Step 3: 実装**

`backend/agentcore/tools/ev_proposer.py` に以下の変更を加える:

1. `_resolve_ev_filter` 関数を追加（`_resolve_bet_types` の直後）:

```python
def _resolve_ev_filter(
    betting_preference: dict | None,
) -> tuple[float, float, float, float]:
    """好み設定から確率/EVフィルター値を解決する.

    Returns:
        (min_probability, max_probability, min_ev, max_ev)
    """
    if not betting_preference:
        return (0.01, 0.50, 1.0, 10.0)
    return (
        float(betting_preference.get("min_probability", 0.01)),
        float(betting_preference.get("max_probability", 0.50)),
        float(betting_preference.get("min_ev", 1.0)),
        float(betting_preference.get("max_ev", 10.0)),
    )
```

2. `_generate_ev_candidates` 関数のシグネチャに `ev_filter` パラメータを追加:

```python
def _generate_ev_candidates(
    win_probs: dict[int, float],
    runners_map: dict[int, dict],
    bet_types: list[str],
    total_runners: int,
    all_odds: dict,
    ev_filter: tuple[float, float, float, float] | None = None,
) -> list[dict]:
```

3. 関数冒頭でフィルター値を展開:

```python
min_prob_filter, max_prob_filter, min_ev_filter, max_ev_filter = ev_filter or (0.01, 0.50, 1.0, 10.0)
```

4. `eligible` のフィルタリングで `MIN_PROB_FOR_COMBINATION` を `min_prob_filter` に変更:

```python
eligible = sorted(
    [hn for hn, p in win_probs.items() if p >= min_prob_filter],
    key=lambda hn: win_probs[hn],
    reverse=True,
)
```

5. 各券種ループ内の `if ev >= EV_THRESHOLD:` を以下に変更（3箇所すべて）:

```python
if min_ev_filter <= ev <= max_ev_filter and min_prob_filter <= prob <= max_prob_filter:
```

6. `_propose_bets_impl` でフィルター解決を追加し `_generate_ev_candidates` に渡す:

`_propose_bets_impl` 内の `candidates = _generate_ev_candidates(...)` 呼び出しの直前に:
```python
ev_filter = _resolve_ev_filter(_current_betting_preference)
```

呼び出しを:
```python
candidates = _generate_ev_candidates(
    win_probabilities, runners_map, bet_types, total_runners, all_odds,
    ev_filter=ev_filter,
)
```

**Step 4: テストが通ることを確認**

Run: `cd backend && uv run pytest tests/agentcore/test_ev_proposer.py -v`
Expected: ALL PASS

**Step 5: 全バックエンドテスト確認**

Run: `cd backend && uv run pytest --ignore=tests/batch -x -q`
Expected: ALL PASS

**Step 6: コミット**

```bash
git add backend/agentcore/tools/ev_proposer.py backend/tests/agentcore/test_ev_proposer.py
git commit -m "feat: EV proposerに確率/EVフィルター適用を実装"
```

---

### Task 4: フロントエンド型定義とデュアルレンジスライダーUI

**Files:**
- Modify: `frontend/src/types/index.ts:521-523`
- Modify: `frontend/src/pages/AgentProfilePage.tsx:291-424`

**Step 1: TypeScript型定義を更新**

`frontend/src/types/index.ts` の `BettingPreference` インターフェースを以下に変更:

```typescript
export interface BettingPreference {
  bet_type_preference: BetTypePreference;
  min_probability?: number;
  max_probability?: number;
  min_ev?: number;
  max_ev?: number;
}
```

**Step 2: DualRangeSlider コンポーネントを AgentProfilePage.tsx に追加**

`frontend/src/pages/AgentProfilePage.tsx` のファイル末尾（`BettingPreferenceForm` の前）に `DualRangeSlider` コンポーネントを追加:

```tsx
function DualRangeSlider({
  label,
  minValue,
  maxValue,
  min,
  max,
  step,
  formatValue,
  onMinChange,
  onMaxChange,
}: {
  label: string;
  minValue: number;
  maxValue: number;
  min: number;
  max: number;
  step: number;
  formatValue: (v: number) => string;
  onMinChange: (v: number) => void;
  onMaxChange: (v: number) => void;
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ fontSize: 12, color: '#666' }}>{label}</div>
        <div style={{ fontSize: 12, color: '#1a73e8', fontWeight: 600 }}>
          {formatValue(minValue)} ～ {formatValue(maxValue)}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: '#999', minWidth: 32 }}>下限</span>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={minValue}
          onChange={(e) => {
            const v = Number(e.target.value);
            if (v <= maxValue) onMinChange(v);
          }}
          style={{ flex: 1, accentColor: '#1a73e8' }}
        />
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 4 }}>
        <span style={{ fontSize: 11, color: '#999', minWidth: 32 }}>上限</span>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={maxValue}
          onChange={(e) => {
            const v = Number(e.target.value);
            if (v >= minValue) onMaxChange(v);
          }}
          style={{ flex: 1, accentColor: '#1a73e8' }}
        />
      </div>
    </div>
  );
}
```

**Step 3: BettingPreferenceForm にスライダーのstateと保存ロジックを追加**

`BettingPreferenceForm` コンポーネント内に state を追加（既存の state 宣言の後）:

```tsx
const [minProb, setMinProb] = useState<number>((agent.betting_preference?.min_probability ?? 0.01) * 100);
const [maxProb, setMaxProb] = useState<number>((agent.betting_preference?.max_probability ?? 0.50) * 100);
const [minEv, setMinEv] = useState<number>(agent.betting_preference?.min_ev ?? 1.0);
const [maxEv, setMaxEv] = useState<number>(agent.betting_preference?.max_ev ?? 10.0);
```

注意: 確率スライダーはUI上は 1-50（%表示）で操作し、保存時に 0.01-0.50 に変換する。

券種の好みセクション（`</div>` の後、`{/* 追加指示 */}` の前）にスライダーを追加:

```tsx
{/* 確率フィルター */}
<DualRangeSlider
  label="確率フィルター"
  minValue={minProb}
  maxValue={maxProb}
  min={1}
  max={50}
  step={1}
  formatValue={(v) => `${v}%`}
  onMinChange={setMinProb}
  onMaxChange={setMaxProb}
/>

{/* EVフィルター */}
<DualRangeSlider
  label="期待値(EV)フィルター"
  minValue={minEv}
  maxValue={maxEv}
  min={1.0}
  max={10.0}
  step={0.5}
  formatValue={(v) => `${v.toFixed(1)}`}
  onMinChange={setMinEv}
  onMaxChange={setMaxEv}
/>
```

保存ボタンの `onClick` 内の `updateAgent` 呼び出しを変更:

```tsx
const success = await updateAgent(
  undefined,
  {
    bet_type_preference: betTypePref,
    min_probability: minProb / 100,
    max_probability: maxProb / 100,
    min_ev: minEv,
    max_ev: maxEv,
  },
  customInstructions === '' ? null : customInstructions,
);
```

**Step 4: ビルド確認**

Run: `cd frontend && npx tsc --noEmit`
Expected: 0 errors

**Step 5: フロントエンドテスト確認**

Run: `cd frontend && npm install && npx vitest --run`
Expected: ALL PASS

**Step 6: コミット**

```bash
git add frontend/src/types/index.ts frontend/src/pages/AgentProfilePage.tsx
git commit -m "feat: 確率/EVフィルターのデュアルレンジスライダーUIを追加"
```

---

### Task 5: 全テスト実行と最終確認

**Files:** なし（テスト実行のみ）

**Step 1: バックエンドテスト全実行**

Run: `cd backend && uv run pytest --ignore=tests/batch -x -q`
Expected: ALL PASS

**Step 2: フロントエンドテスト全実行**

Run: `cd frontend && npx vitest --run`
Expected: ALL PASS

**Step 3: 問題があれば修正、なければコミット不要**
