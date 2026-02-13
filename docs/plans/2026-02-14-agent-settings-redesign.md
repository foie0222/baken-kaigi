# エージェント設定改善 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** エージェントの名前を固定、スタイルを変更可能にし、能力値（AgentStats）を削除する

**Architecture:** バックエンドのAgentエンティティからstatsフィールドを除去し、update_name→update_styleに切り替え。フロントエンドのAgentProfilePageにインラインスタイル変更UIを追加。振り返り生成からstats_change計算を削除。

**Tech Stack:** Python (pytest), React + TypeScript, Zustand, DynamoDB

---

### Task 1: Agentエンティティからstatsを削除し、update_styleを追加

**Files:**
- Modify: `backend/src/domain/entities/agent.py`
- Modify: `backend/tests/domain/test_agent.py`

**Step 1: テストを修正（stats関連テスト削除、update_style追加）**

`backend/tests/domain/test_agent.py` を以下のように変更:

- `test_エージェントを作成できる`: `assert agent.stats.risk_management == 50` の行を削除
- `test_名前を変更できる`: テスト全体を削除
- `test_能力値を変更できる`: テスト全体を削除
- 以下の新しいテストを追加:

```python
def test_スタイルを変更できる(self):
    agent = Agent.create(
        agent_id=AgentId("agt_001"),
        user_id=UserId("usr_001"),
        name=AgentName("ハヤテ"),
        base_style=AgentStyle.SOLID,
    )
    agent.update_style(AgentStyle.DATA)
    assert agent.base_style == AgentStyle.DATA
```

`TestAgentStats` クラス全体を削除。

**Step 2: テストを実行して失敗を確認**

Run: `cd backend && uv run pytest tests/domain/test_agent.py -v`
Expected: FAIL — `update_style` が存在しない、stats参照でエラー

**Step 3: Agentエンティティを修正**

`backend/src/domain/entities/agent.py`:
- `stats` フィールドを削除
- `update_name()` メソッドを削除
- `apply_stats_change()` メソッドを削除
- `update_style()` メソッドを追加:

```python
def update_style(self, style: AgentStyle) -> None:
    """分析スタイルを変更する."""
    self.base_style = style
    self.updated_at = datetime.now(timezone.utc)
```

- `create()` から `stats=AgentStats.initial_for_style(base_style.value)` を削除
- importから `AgentStats` を削除

**Step 4: テストを実行して成功を確認**

Run: `cd backend && uv run pytest tests/domain/test_agent.py -v`
Expected: PASS

**Step 5: コミット**

```bash
git add backend/src/domain/entities/agent.py backend/tests/domain/test_agent.py
git commit -m "refactor: Agentエンティティからstatsを削除し、update_styleを追加"
```

---

### Task 2: UpdateAgentUseCaseをname→base_styleに変更

**Files:**
- Modify: `backend/src/application/use_cases/update_agent.py`
- Modify: `backend/tests/application/test_agent_use_cases.py`

**Step 1: テストを修正**

`backend/tests/application/test_agent_use_cases.py` の `TestUpdateAgentUseCase`:

- `test_名前を更新できる` → `test_スタイルを更新できる` に変更:

```python
def test_スタイルを更新できる(self):
    repo = InMemoryAgentRepository()
    create_uc = CreateAgentUseCase(repo)
    create_uc.execute("usr_001", "ハヤテ", "solid")

    update_uc = UpdateAgentUseCase(repo)
    result = update_uc.execute("usr_001", base_style="data")

    assert result.agent.base_style == AgentStyle.DATA
```

- `test_存在しないユーザーはエラー` を修正: `name="テスト"` → `base_style="data"`

- 新しいテストを追加:

```python
def test_不正なスタイルはエラー(self):
    repo = InMemoryAgentRepository()
    create_uc = CreateAgentUseCase(repo)
    create_uc.execute("usr_001", "ハヤテ", "solid")

    update_uc = UpdateAgentUseCase(repo)
    with pytest.raises(ValueError):
        update_uc.execute("usr_001", base_style="invalid")
```

**Step 2: テストを実行して失敗を確認**

Run: `cd backend && uv run pytest tests/application/test_agent_use_cases.py::TestUpdateAgentUseCase -v`
Expected: FAIL

**Step 3: UpdateAgentUseCaseを修正**

`backend/src/application/use_cases/update_agent.py`:
- `name` パラメータを `base_style` に変更
- `AgentName` のインポートを `AgentStyle` に変更
- `agent.update_name(AgentName(name))` → `agent.update_style(AgentStyle(base_style))`

```python
from src.domain.enums import AgentStyle

def execute(self, user_id: str, base_style: str | None = None) -> UpdateAgentResult:
    uid = UserId(user_id)
    agent = self._agent_repository.find_by_user_id(uid)

    if agent is None:
        raise AgentNotFoundError(f"Agent not found for user: {user_id}")

    if base_style is not None:
        agent.update_style(AgentStyle(base_style))

    self._agent_repository.save(agent)
    return UpdateAgentResult(agent=agent)
```

**Step 4: テストを実行して成功を確認**

Run: `cd backend && uv run pytest tests/application/test_agent_use_cases.py -v`
Expected: PASS

**Step 5: コミット**

```bash
git add backend/src/application/use_cases/update_agent.py backend/tests/application/test_agent_use_cases.py
git commit -m "refactor: UpdateAgentUseCaseをname→base_styleに変更"
```

---

### Task 3: 振り返りからstats_changeを削除

**Files:**
- Modify: `backend/src/application/use_cases/create_agent_review.py`
- Modify: `backend/src/domain/entities/agent_review.py`
- Modify: `backend/tests/application/test_agent_review_use_cases.py`

**Step 1: テストを修正**

`backend/tests/application/test_agent_review_use_cases.py`:
- `test_エージェントのステータスが変化する` テストを削除
- `test_ステータス変化にスタイル別ボーナスが反映される` テストを削除

**Step 2: テストを実行して成功を確認（テスト削除のみなので通るはず）**

Run: `cd backend && uv run pytest tests/application/test_agent_review_use_cases.py -v`
Expected: PASS

**Step 3: create_agent_review.pyからstats関連を削除**

`backend/src/application/use_cases/create_agent_review.py`:
- `_calculate_stats_change()` メソッドを削除
- `execute()` 内の `stats_change = self._calculate_stats_change(...)` を削除
- `execute()` 内の `agent.apply_stats_change(**stats_change)` を削除
- `AgentReview` コンストラクタの `stats_change` 引数を空dict `{}` に変更

**Step 4: テストを実行して成功を確認**

Run: `cd backend && uv run pytest tests/application/test_agent_review_use_cases.py -v`
Expected: PASS

**Step 5: コミット**

```bash
git add backend/src/application/use_cases/create_agent_review.py backend/tests/application/test_agent_review_use_cases.py
git commit -m "refactor: 振り返りからstats_change計算を削除"
```

---

### Task 4: APIハンドラー修正（PUT仕様変更、レスポンスからstats除去）

**Files:**
- Modify: `backend/src/api/handlers/agent.py`
- Modify: `backend/tests/api/handlers/test_agent.py`

**Step 1: テストを修正**

`backend/tests/api/handlers/test_agent.py`:

`TestUpdateAgent`:
- `test_名前を更新できる` → `test_スタイルを更新できる` に変更:

```python
def test_スタイルを更新できる(self):
    create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ", "base_style": "solid"})
    agent_handler(create_event, None)

    event = _make_event(method="PUT", path="/agents/me", body={"base_style": "data"})
    response = agent_handler(event, None)
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["base_style"] == "data"
```

- `test_未作成は404` を修正: `body={"name": "カゼ"}` → `body={"base_style": "data"}`

- 新テスト追加:

```python
def test_不正なスタイルは400(self):
    create_event = _make_event(method="POST", path="/agents", body={"name": "ハヤテ", "base_style": "solid"})
    agent_handler(create_event, None)

    event = _make_event(method="PUT", path="/agents/me", body={"base_style": "invalid"})
    response = agent_handler(event, None)
    assert response["statusCode"] == 400
```

**Step 2: テストを実行して失敗を確認**

Run: `cd backend && uv run pytest tests/api/handlers/test_agent.py::TestUpdateAgent -v`
Expected: FAIL

**Step 3: ハンドラーを修正**

`backend/src/api/handlers/agent.py`:

`_agent_to_dict()`: `"stats": agent.stats.to_dict()` を削除

`_update_agent()`:

```python
def _update_agent(event: dict) -> dict:
    try:
        user_id = require_authenticated_user_id(event)
    except AuthenticationError:
        return unauthorized_response(event=event)

    try:
        body = get_body(event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    base_style = body.get("base_style")

    if base_style is not None and not isinstance(base_style, str):
        return bad_request_response("base_style must be a string", event=event)
    if base_style is None:
        return bad_request_response("base_style is required for update", event=event)
    if base_style not in ("solid", "longshot", "data", "pace"):
        return bad_request_response(
            "base_style must be one of: solid, longshot, data, pace", event=event
        )

    repository = Dependencies.get_agent_repository()
    use_case = UpdateAgentUseCase(repository)

    try:
        result = use_case.execute(user_id, base_style=base_style)
    except AgentNotFoundError:
        return not_found_response("Agent", event=event)
    except ValueError as e:
        return bad_request_response(str(e), event=event)

    return success_response(_agent_to_dict(result.agent), event=event)
```

**Step 4: テストを実行して成功を確認**

Run: `cd backend && uv run pytest tests/api/handlers/test_agent.py -v`
Expected: PASS

**Step 5: コミット**

```bash
git add backend/src/api/handlers/agent.py backend/tests/api/handlers/test_agent.py
git commit -m "refactor: PUT /agents/me をスタイル変更APIに変更、レスポンスからstats除去"
```

---

### Task 5: DynamoDBリポジトリとAgent.createからstats除去

**Files:**
- Modify: `backend/src/infrastructure/repositories/dynamodb_agent_repository.py`
- Modify: `backend/src/infrastructure/repositories/in_memory_agent_repository.py`（確認のみ）
- Modify: `backend/src/domain/entities/agent.py`（すでにTask 1で対応済み、ここではDynamoDB互換対応）

**Step 1: DynamoDBリポジトリを修正**

`backend/src/infrastructure/repositories/dynamodb_agent_repository.py`:
- `_to_dynamodb_item()`: `"stats": agent.stats.to_dict()` を削除
- `_from_dynamodb_item()`: `stats=AgentStats(...)` の構築を削除
- importから `AgentStats` を削除

既存のDynamoDBデータにはstatsが残っているが、読み込み時に無視するだけなので互換性問題なし。

**Step 2: 全テストを実行**

Run: `cd backend && uv run pytest tests/ -v --timeout=10`
Expected: PASS（CreateAgentUseCase内のAgent.createがstatsを返さなくなるので、全体に波及しないか確認）

**Step 3: コミット**

```bash
git add backend/src/infrastructure/repositories/dynamodb_agent_repository.py
git commit -m "refactor: DynamoDBリポジトリからstats読み書きを削除"
```

---

### Task 6: フロントエンド型定義とAPI修正

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/stores/agentStore.ts`

**Step 1: 型定義を修正**

`frontend/src/types/index.ts`:
- `AgentStats` インターフェースを削除
- `Agent` インターフェースから `stats: AgentStats` を削除
- `AgentData` インターフェースから `stats: AgentStats` を削除
- `AgentReview` インターフェースから `stats_change: Record<string, number>` を削除

**Step 2: apiClient.updateAgentを修正**

`frontend/src/api/client.ts`:
- `updateAgent(name: string)` → `updateAgent(baseStyle: AgentStyleId)` に変更
- リクエストボディ: `{ name }` → `{ base_style: baseStyle }`

**Step 3: agentStoreを修正**

`frontend/src/stores/agentStore.ts`:
- `updateAgent: (name: string)` → `updateAgent: (baseStyle: AgentStyleId)`
- `getAgentData()` から `stats` プロパティを削除

**Step 4: TypeScriptビルド確認**

Run: `cd frontend && npx tsc --noEmit`
Expected: エラーがあれば次のTaskで対処

**Step 5: コミット**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/stores/agentStore.ts
git commit -m "refactor: フロントエンド型定義からstatsを削除、updateAgentをスタイル変更に変更"
```

---

### Task 7: OnboardingPageテキスト修正

**Files:**
- Modify: `frontend/src/pages/OnboardingPage.tsx`

**Step 1: テキストを修正**

2箇所を変更:
- L46: `あなた好みの分析ができるようになります` → `あなたの好みで分析できるようになります`
- L164: `スタイルは後から変更できませんが、名前は変更できます` → `名前は後から変更できませんが、スタイルは変更できます`

**Step 2: コミット**

```bash
git add frontend/src/pages/OnboardingPage.tsx
git commit -m "fix: OnboardingPageのテキストを修正"
```

---

### Task 8: AgentProfilePageから能力値削除、スタイル変更UI追加

**Files:**
- Modify: `frontend/src/pages/AgentProfilePage.tsx`

**Step 1: 能力値セクションを削除**

- `StatBar` コンポーネント全体を削除
- `STAT_LABELS` 定数を削除
- 能力値セクション（L228-L242 `{/* 能力値 */}` 〜 `</div>`）を削除
- 振り返りカードの `stats_change` バッジ表示を削除（ReviewCardコンポーネント内の `stats_change` 関連JSXを削除）

**Step 2: スタイル変更UIを追加**

- `import { AGENT_STYLES, AGENT_STYLE_MAP } from '../constants/agentStyles';` に変更（AGENT_STYLESを追加）
- `import { useAgentStore } from '../stores/agentStore';` で `updateAgent` も取得
- `useState` で `isEditingStyle` と `isUpdating` を管理
- スタイルバッジの横に「変更」リンクを追加
- `isEditingStyle` が `true` のときOnboardingPageと同じ2x2グリッドを表示
- 選択時に `updateAgent(newStyle)` を呼び出し、成功したらグリッドを閉じる

ヘッダーのスタイルバッジ部分を以下のように変更:

```tsx
<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 4 }}>
  <span style={{
    fontSize: 12,
    fontWeight: 600,
    color,
    background: `${color}12`,
    padding: '2px 10px',
    borderRadius: 10,
  }}>
    {styleInfo?.label || agent.base_style}
  </span>
  <span style={{ fontSize: 13, color: '#666' }}>Lv.{agent.level} {levelTitle}</span>
  <button
    type="button"
    onClick={() => setIsEditingStyle(!isEditingStyle)}
    style={{
      fontSize: 12,
      color: '#1a73e8',
      background: 'none',
      border: 'none',
      cursor: 'pointer',
      padding: 0,
    }}
  >
    {isEditingStyle ? '閉じる' : '変更'}
  </button>
</div>

{isEditingStyle && (
  <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
    {AGENT_STYLES.map((style) => {
      const isSelected = agent.base_style === style.id;
      return (
        <button
          key={style.id}
          type="button"
          disabled={isUpdating}
          onClick={async () => {
            if (style.id === agent.base_style) return;
            setIsUpdating(true);
            const success = await updateAgent(style.id);
            if (success) {
              setIsEditingStyle(false);
              await fetchAgent();
            }
            setIsUpdating(false);
          }}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: 12,
            border: isSelected ? `2px solid ${style.color}` : '2px solid #e5e7eb',
            borderRadius: 10,
            background: isSelected ? `${style.color}08` : 'white',
            cursor: isSelected ? 'default' : 'pointer',
            opacity: isUpdating ? 0.5 : 1,
          }}
        >
          <span style={{ fontSize: 24, marginBottom: 4 }}>{style.icon}</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: isSelected ? style.color : '#333' }}>
            {style.label}
          </span>
        </button>
      );
    })}
  </div>
)}
```

**Step 3: TypeScript型エラーがないか確認**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS

**Step 4: コミット**

```bash
git add frontend/src/pages/AgentProfilePage.tsx
git commit -m "feat: AgentProfilePageから能力値削除、インラインスタイル変更UI追加"
```

---

### Task 9: 全体テスト実行と残りの型エラー修正

**Files:**
- 必要に応じて複数ファイル

**Step 1: バックエンド全テスト実行**

Run: `cd backend && uv run pytest tests/ -v --timeout=10`
Expected: PASS（stats関連でコンパイルエラーがあれば修正）

**Step 2: フロントエンドビルド確認**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS（AgentData内のstats参照が残っていれば修正）

**Step 3: 残りの問題を修正して最終コミット**

```bash
git add -A
git commit -m "fix: 全テスト・型チェック通過を確認"
```
