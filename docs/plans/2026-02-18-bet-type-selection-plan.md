# 券種選択の直接指定化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 「券種の好み」（抽象的な5択）を廃止し、購入する券種を7種から直接複数選択するUIに変更する。

**Architecture:** `BetTypePreference` enum を完全削除し、`BettingPreference` に `selected_bet_types: list[str]` を持たせる。フロントエンドは複数選択トグルボタン。バックエンド ev_proposer は `selected_bet_types` をそのまま使用。

**Tech Stack:** React + TypeScript (frontend), Python (backend), DynamoDB (storage)

---

### Task 1: Backend Domain - BettingPreference値オブジェクト変更

**Files:**
- Modify: `backend/src/domain/value_objects/betting_preference.py`
- Modify: `backend/src/domain/enums/__init__.py`
- Delete: `backend/src/domain/enums/bet_type_preference.py`

**Step 1: テストを書き換える（test_betting_preference_enums.py）**

`backend/tests/domain/test_betting_preference_enums.py` を以下に書き換え:

```python
"""好み設定値オブジェクトのテスト."""
from src.domain.value_objects import BettingPreference


class TestBettingPreference:
    """BettingPreference値オブジェクトのテスト."""

    def test_デフォルト値で作成できる(self):
        pref = BettingPreference.default()
        assert pref.selected_bet_types == []

    def test_指定した券種で作成できる(self):
        pref = BettingPreference(
            selected_bet_types=["win", "trio"],
        )
        assert pref.selected_bet_types == ["win", "trio"]

    def test_to_dictで辞書に変換できる(self):
        pref = BettingPreference.default()
        d = pref.to_dict()
        assert d == {
            "selected_bet_types": [],
            "min_probability": 0.0,
            "min_ev": 0.0,
            "max_probability": None,
            "max_ev": None,
            "race_budget": 0,
        }

    def test_from_dictで復元できる(self):
        data = {
            "selected_bet_types": ["quinella", "trio"],
        }
        pref = BettingPreference.from_dict(data)
        assert pref.selected_bet_types == ["quinella", "trio"]

    def test_from_dictで空辞書はデフォルト(self):
        pref = BettingPreference.from_dict({})
        assert pref == BettingPreference.default()

    def test_from_dictでNoneはデフォルト(self):
        pref = BettingPreference.from_dict(None)
        assert pref == BettingPreference.default()

    def test_フィルターフィールド付きで作成できる(self):
        pref = BettingPreference(
            selected_bet_types=[],
            min_probability=0.05,
            min_ev=1.5,
        )
        assert pref.min_probability == 0.05
        assert pref.min_ev == 1.5

    def test_デフォルト値にフィルターフィールドが含まれる(self):
        pref = BettingPreference.default()
        assert pref.min_probability == 0.0
        assert pref.min_ev == 0.0
        assert pref.max_probability is None
        assert pref.max_ev is None

    def test_to_dictにフィルターフィールドが含まれる(self):
        pref = BettingPreference(
            selected_bet_types=["win"],
            min_probability=0.05,
            min_ev=1.5,
            max_probability=0.30,
            max_ev=5.0,
        )
        d = pref.to_dict()
        assert d == {
            "selected_bet_types": ["win"],
            "min_probability": 0.05,
            "min_ev": 1.5,
            "max_probability": 0.30,
            "max_ev": 5.0,
            "race_budget": 0,
        }

    def test_from_dictでフィルターフィールドを復元できる(self):
        data = {
            "selected_bet_types": ["trio"],
            "min_probability": 0.03,
            "min_ev": 1.2,
            "max_probability": 0.25,
            "max_ev": 4.0,
        }
        pref = BettingPreference.from_dict(data)
        assert pref.min_probability == 0.03
        assert pref.min_ev == 1.2
        assert pref.max_probability == 0.25
        assert pref.max_ev == 4.0

    def test_from_dictでフィルターフィールドなしはデフォルト値(self):
        data = {"selected_bet_types": []}
        pref = BettingPreference.from_dict(data)
        assert pref.min_probability == 0.0
        assert pref.min_ev == 0.0
        assert pref.max_probability is None
        assert pref.max_ev is None

    def test_from_dictでmaxがNoneの場合は上限なし(self):
        data = {
            "selected_bet_types": [],
            "min_probability": 0.05,
            "max_probability": None,
            "min_ev": 1.5,
            "max_ev": None,
        }
        pref = BettingPreference.from_dict(data)
        assert pref.max_probability is None
        assert pref.max_ev is None
```

**Step 2: テスト実行して失敗を確認**

Run: `cd backend && uv run pytest tests/domain/test_betting_preference_enums.py -v`
Expected: FAIL (selected_bet_types が未定義)

**Step 3: BettingPreference値オブジェクトを変更**

`backend/src/domain/value_objects/betting_preference.py` を以下に書き換え:

```python
"""好み設定値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BettingPreference:
    """ユーザーの馬券購入好み設定."""

    selected_bet_types: list[str] = field(default_factory=list)
    min_probability: float = 0.0
    min_ev: float = 0.0
    max_probability: float | None = None
    max_ev: float | None = None
    race_budget: int = 0  # 1レースあたりの予算（円）

    @classmethod
    def default(cls) -> BettingPreference:
        """デフォルト値で作成する."""
        return cls()

    def to_dict(self) -> dict:
        """辞書に変換する."""
        return {
            "selected_bet_types": list(self.selected_bet_types),
            "min_probability": self.min_probability,
            "min_ev": self.min_ev,
            "max_probability": self.max_probability,
            "max_ev": self.max_ev,
            "race_budget": self.race_budget,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> BettingPreference:
        """辞書から復元する."""
        if not data:
            return cls.default()
        max_prob_raw = data.get("max_probability")
        max_ev_raw = data.get("max_ev")
        raw_types = data.get("selected_bet_types")
        return cls(
            selected_bet_types=list(raw_types) if raw_types else [],
            min_probability=float(data.get("min_probability", 0.0)),
            min_ev=float(data.get("min_ev", 0.0)),
            max_probability=float(max_prob_raw) if max_prob_raw is not None else None,
            max_ev=float(max_ev_raw) if max_ev_raw is not None else None,
            race_budget=int(data.get("race_budget", 0)),
        )
```

**Step 4: BetTypePreference enum を削除し __init__.py を更新**

`backend/src/domain/enums/bet_type_preference.py` を削除。

`backend/src/domain/enums/__init__.py` から `BetTypePreference` の import と `__all__` エントリを削除。

**Step 5: テスト実行して成功を確認**

Run: `cd backend && uv run pytest tests/domain/test_betting_preference_enums.py -v`
Expected: ALL PASS

**Step 6: コミット**

```bash
git add -A && git commit -m "feat: BetTypePreference enum廃止、selected_bet_typesに変更"
```

---

### Task 2: Backend Domain - Agent関連テスト修正

**Files:**
- Modify: `backend/tests/domain/test_agent.py`
- Modify: `backend/tests/infrastructure/repositories/test_dynamodb_agent_repository_serialization.py`

**Step 1: test_agent.py の BetTypePreference 参照を修正**

`BetTypePreference` の import を削除し、`BettingPreference(bet_type_preference=BetTypePreference.TRIO_FOCUSED)` → `BettingPreference(selected_bet_types=["trio", "trifecta"])` に変更。
assert も `pref.bet_type_preference == BetTypePreference.TRIO_FOCUSED` → `pref.selected_bet_types == ["trio", "trifecta"]` に変更。

**Step 2: test_dynamodb_agent_repository_serialization.py を修正**

`BetTypePreference` import 削除。テストデータの `bet_type_preference=BetTypePreference.TRIO_FOCUSED` → `selected_bet_types=["trio", "trifecta"]`。
シリアライズ結果の assert も `"bet_type_preference": "trio_focused"` → `"selected_bet_types": ["trio", "trifecta"]` に変更。

**Step 3: テスト実行**

Run: `cd backend && uv run pytest tests/domain/test_agent.py tests/infrastructure/repositories/test_dynamodb_agent_repository_serialization.py -v`
Expected: ALL PASS

**Step 4: コミット**

```bash
git add -A && git commit -m "test: Agent関連テストをselected_bet_typesに対応"
```

---

### Task 3: Backend API - バリデーション変更

**Files:**
- Modify: `backend/src/api/handlers/agent.py`
- Modify: `backend/tests/api/handlers/test_agent.py`

**Step 1: test_agent.py のテストデータを修正**

`"bet_type_preference": "trio_focused"` → `"selected_bet_types": ["trio", "trifecta"]` に変更。
assert も同様に変更。

**Step 2: agent.py のバリデーションを変更**

`_VALID_BET_TYPE_PREFERENCES` を削除。代わりに:

```python
_VALID_BET_TYPES = {"win", "place", "quinella", "quinella_place", "exacta", "trio", "trifecta"}
```

バリデーション部分:
```python
# selected_bet_types バリデーション
sbt = betting_preference.get("selected_bet_types")
if sbt is not None:
    if not isinstance(sbt, list):
        return bad_request_response("selected_bet_types must be a list", event=event)
    if any(t not in _VALID_BET_TYPES for t in sbt):
        return bad_request_response(
            f"selected_bet_types must contain only: {', '.join(sorted(_VALID_BET_TYPES))}", event=event
        )
```

旧フィールド `bet_type_preference` のバリデーションは削除。

**Step 3: テスト実行**

Run: `cd backend && uv run pytest tests/api/handlers/test_agent.py -v`
Expected: ALL PASS

**Step 4: コミット**

```bash
git add -A && git commit -m "feat: APIバリデーションをselected_bet_typesに変更"
```

---

### Task 4: Backend Use Cases テスト修正

**Files:**
- Modify: `backend/tests/application/test_agent_use_cases.py`

**Step 1: テストデータを修正**

`"bet_type_preference": "trio_focused"` → `"selected_bet_types": ["trio", "trifecta"]`。
assert も `.bet_type_preference.value == "trio_focused"` → `.selected_bet_types == ["trio", "trifecta"]` に変更。

**Step 2: テスト実行**

Run: `cd backend && uv run pytest tests/application/test_agent_use_cases.py -v`
Expected: ALL PASS

**Step 3: コミット**

```bash
git add -A && git commit -m "test: use caseテストをselected_bet_typesに対応"
```

---

### Task 5: AgentCore - ev_proposer簡略化

**Files:**
- Modify: `backend/agentcore/tools/ev_proposer.py`
- Modify: `backend/tests/agentcore/test_ev_proposer.py`

**Step 1: test_ev_proposer.py の TestResolveBetTypes を書き換え**

```python
class TestResolveBetTypes:
    """_resolve_bet_types のテスト."""

    def test_Noneの場合はデフォルト券種(self):
        assert _resolve_bet_types(None) == DEFAULT_BET_TYPES

    def test_空辞書の場合はデフォルト券種(self):
        assert _resolve_bet_types({}) == DEFAULT_BET_TYPES

    def test_selected_bet_typesが空の場合はデフォルト券種(self):
        assert _resolve_bet_types({"selected_bet_types": []}) == DEFAULT_BET_TYPES

    def test_selected_bet_typesが指定されている場合はそのまま返す(self):
        result = _resolve_bet_types({"selected_bet_types": ["win", "trio"]})
        assert result == ["win", "trio"]

    def test_selected_bet_types単一券種(self):
        result = _resolve_bet_types({"selected_bet_types": ["quinella_place"]})
        assert result == ["quinella_place"]
```

**Step 2: テスト実行して失敗を確認**

Run: `cd backend && uv run pytest tests/agentcore/test_ev_proposer.py::TestResolveBetTypes -v`
Expected: FAIL

**Step 3: ev_proposer.py の _resolve_bet_types を簡略化**

`_BET_TYPE_PREFERENCE_MAP` を削除。`_resolve_bet_types` を以下に変更:

```python
def _resolve_bet_types(betting_preference: dict | None) -> list[str]:
    """好み設定から対象券種を解決する."""
    if not betting_preference:
        return DEFAULT_BET_TYPES
    selected = betting_preference.get("selected_bet_types")
    if not selected:
        return DEFAULT_BET_TYPES
    return list(selected)
```

**Step 4: テスト実行して成功を確認**

Run: `cd backend && uv run pytest tests/agentcore/test_ev_proposer.py::TestResolveBetTypes -v`
Expected: ALL PASS

**Step 5: コミット**

```bash
git add -A && git commit -m "refactor: ev_proposerのbet_type_preference mapを削除、selected_bet_typesを直接使用"
```

---

### Task 6: AgentCore - 残りのテスト修正

**Files:**
- Modify: `backend/tests/agentcore/test_agent.py`
- Modify: `backend/tests/agentcore/test_ev_proposer.py` (TestResolveBetTypes以外の箇所)
- Modify: `backend/tests/agentcore/test_bet_proposal.py` (該当箇所あれば)

**Step 1: test_agent.py の `bet_type_preference` 参照を修正**

`"bet_type_preference": "trio_focused"` → `"selected_bet_types": ["trio", "trifecta"]` に変更。

**Step 2: test_ev_proposer.py 内のその他テストで `bet_type_preference` を使っている箇所を `selected_bet_types` に修正**

**Step 3: テスト実行**

Run: `cd backend && uv run pytest tests/agentcore/ -v`
Expected: ALL PASS

**Step 4: コミット**

```bash
git add -A && git commit -m "test: agentcoreテストをselected_bet_typesに対応"
```

---

### Task 7: Backend全体テスト通過確認

**Step 1: 全テスト実行**

Run: `cd backend && uv run pytest -x -q`
Expected: ALL PASS (2000+件)

grep で残っている `BetTypePreference` や `bet_type_preference` の参照がないか確認:
Run: `grep -r "BetTypePreference\|bet_type_preference" backend/src/ backend/agentcore/ backend/tests/ --include="*.py"`
Expected: 0件

**Step 2: 修正があればここで対応してコミット**

---

### Task 8: Frontend - 型定義と定数の変更

**Files:**
- Modify: `frontend/src/types/index.ts`
- Delete: `frontend/src/constants/bettingPreferences.ts`

**Step 1: types/index.ts を修正**

`BetTypePreference` 型を削除。`BettingPreference` インターフェースを変更:

```typescript
export interface BettingPreference {
  selected_bet_types: BetType[];
  min_probability?: number;
  min_ev?: number;
  max_probability?: number | null;
  max_ev?: number | null;
  race_budget?: number;
}
```

**Step 2: bettingPreferences.ts を削除**

このファイルは `BET_TYPE_PREFERENCE_OPTIONS` のみを定義しており、新UIでは不要。

**Step 3: コミット**

```bash
git add -A && git commit -m "feat: フロントエンド型定義をselected_bet_typesに変更"
```

---

### Task 9: Frontend - AgentProfilePage UI変更

**Files:**
- Modify: `frontend/src/pages/AgentProfilePage.tsx`

**Step 1: UIを複数選択トグルに変更**

- `BetTypePreference` の import を削除
- `BET_TYPE_PREFERENCE_OPTIONS` の import を削除
- `BetTypeLabels` (既存の `types/index.ts` にある) を使用
- state: `betTypePref` (単一) → `selectedBetTypes` (配列)
- 保存時: `bet_type_preference: betTypePref` → `selected_bet_types: selectedBetTypes`
- ラベル: 「券種の好み」→「購入する券種」

BettingPreferenceForm内の券種セクションを以下に変更:

```tsx
import { BetTypeLabels, type BetType } from '../types';

// state
const [selectedBetTypes, setSelectedBetTypes] = useState<BetType[]>(
  agent.betting_preference?.selected_bet_types ?? []
);

// トグル関数
const toggleBetType = (bt: BetType) => {
  setSelectedBetTypes(prev =>
    prev.includes(bt) ? prev.filter(t => t !== bt) : [...prev, bt]
  );
};

// JSX
<div style={{ marginBottom: 16 }}>
  <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>購入する券種</div>
  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
    {(Object.entries(BetTypeLabels) as [BetType, string][]).map(([value, label]) => {
      const isSelected = selectedBetTypes.includes(value);
      return (
        <button
          key={value}
          type="button"
          onClick={() => toggleBetType(value)}
          aria-pressed={isSelected}
          style={{
            fontSize: 13,
            fontWeight: isSelected ? 600 : 400,
            color: isSelected ? '#1a73e8' : '#555',
            background: isSelected ? '#e8f0fe' : '#f5f5f5',
            border: isSelected ? '1.5px solid #1a73e8' : '1.5px solid transparent',
            borderRadius: 20,
            padding: '6px 14px',
            cursor: 'pointer',
            transition: 'all 0.15s',
          }}
        >
          {label}
        </button>
      );
    })}
  </div>
</div>
```

保存時のペイロード:
```tsx
{
  selected_bet_types: selectedBetTypes,
  min_probability: minProb / 100,
  // ...
}
```

**Step 2: コミット**

```bash
git add -A && git commit -m "feat: 券種選択UIを複数選択トグルに変更"
```

---

### Task 10: Frontend - テスト修正

**Files:**
- Modify: `frontend/src/components/proposal/BetProposalSheet.test.tsx`
- Modify: `frontend/src/stores/appStore.test.ts` (該当箇所あれば)
- Modify: `frontend/src/api/client.test.ts` (該当箇所あれば)
- Modify: `frontend/src/types/index.test.ts` (該当箇所あれば)

**Step 1: テストデータの `bet_type_preference: 'auto'` → `selected_bet_types: []` に変更**

BetProposalSheet.test.tsx:
```typescript
betting_preference: { selected_bet_types: [] },
```

**Step 2: 他のテストファイルでも同様に修正**

grep で `bet_type_preference` を検索して全て修正。

**Step 3: テスト実行**

Run: `cd frontend && npm test -- --run`
Expected: ALL PASS

**Step 4: コミット**

```bash
git add -A && git commit -m "test: フロントエンドテストをselected_bet_typesに対応"
```

---

### Task 11: DDD設計ドキュメント更新

**Files:**
- Modify: `aidlc-docs/construction/unit_01_ai_dialog_public/docs/value_objects.md`

**Step 1: BetTypePreference → selected_bet_types に記述を更新**

**Step 2: コミット**

```bash
git add -A && git commit -m "docs: DDD設計ドキュメントをselected_bet_typesに更新"
```

---

### Task 12: 最終確認とPR作成

**Step 1: バックエンド全テスト**

Run: `cd backend && uv run pytest -x -q`
Expected: ALL PASS

**Step 2: フロントエンド全テスト**

Run: `cd frontend && npm test -- --run`
Expected: ALL PASS

**Step 3: 残留チェック**

Run: `grep -r "BetTypePreference\|bet_type_preference\|BET_TYPE_PREFERENCE" --include="*.py" --include="*.ts" --include="*.tsx" backend/ frontend/ agentcore/`
Expected: 0件 (docs以外)

**Step 4: PR作成**
