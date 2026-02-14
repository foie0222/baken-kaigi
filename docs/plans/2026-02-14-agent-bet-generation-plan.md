# エージェント買い目生成 + ユーザー好み設定 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** エージェントに好み設定（券種・狙い方・重視ポイント＋自由記述）を追加し、買い目生成に反映する

**Architecture:** Agentエンティティに `BettingPreference` 値オブジェクトと `custom_instructions` フィールドを追加。`PUT /agents/me` APIを拡張して好み設定を受け付け、AgentCoreの `bet_proposal.py` と `agent_prompt.py` に反映する。フロントエンドではAgentProfilePageに好み設定UIを追加。

**Tech Stack:** Python (backend domain/API/AgentCore), TypeScript/React (frontend), DynamoDB, TDD

**作業ディレクトリ:** `/home/inoue-d/dev/baken-kaigi/feat-agent-preference/`

**テスト実行:** `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest`

**設計ドキュメント:** `docs/plans/2026-02-14-agent-bet-generation-design.md`

---

### Task 1: 列挙型の追加（BetTypePreference, TargetStyle, BettingPriority）

**Files:**
- Create: `backend/src/domain/enums/bet_type_preference.py`
- Create: `backend/src/domain/enums/target_style.py`
- Create: `backend/src/domain/enums/betting_priority.py`
- Modify: `backend/src/domain/enums/__init__.py`
- Create: `backend/tests/domain/test_betting_preference_enums.py`

**Step 1: Write the failing test**

```python
# backend/tests/domain/test_betting_preference_enums.py
"""好み設定列挙型のテスト."""
import pytest

from src.domain.enums import BetTypePreference, TargetStyle, BettingPriority


class TestBetTypePreference:
    """券種好み列挙型のテスト."""

    def test_全ての値が定義されている(self):
        assert BetTypePreference.TRIO_FOCUSED.value == "trio_focused"
        assert BetTypePreference.EXACTA_FOCUSED.value == "exacta_focused"
        assert BetTypePreference.QUINELLA_FOCUSED.value == "quinella_focused"
        assert BetTypePreference.WIDE_FOCUSED.value == "wide_focused"
        assert BetTypePreference.AUTO.value == "auto"

    def test_文字列から変換できる(self):
        assert BetTypePreference("trio_focused") == BetTypePreference.TRIO_FOCUSED


class TestTargetStyle:
    """狙い方列挙型のテスト."""

    def test_全ての値が定義されている(self):
        assert TargetStyle.HONMEI.value == "honmei"
        assert TargetStyle.MEDIUM_LONGSHOT.value == "medium_longshot"
        assert TargetStyle.BIG_LONGSHOT.value == "big_longshot"


class TestBettingPriority:
    """重視ポイント列挙型のテスト."""

    def test_全ての値が定義されている(self):
        assert BettingPriority.HIT_RATE.value == "hit_rate"
        assert BettingPriority.ROI.value == "roi"
        assert BettingPriority.BALANCED.value == "balanced"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/domain/test_betting_preference_enums.py -v`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

```python
# backend/src/domain/enums/bet_type_preference.py
"""券種好み列挙型."""
from enum import Enum


class BetTypePreference(str, Enum):
    """券種の好み."""

    TRIO_FOCUSED = "trio_focused"
    EXACTA_FOCUSED = "exacta_focused"
    QUINELLA_FOCUSED = "quinella_focused"
    WIDE_FOCUSED = "wide_focused"
    AUTO = "auto"
```

```python
# backend/src/domain/enums/target_style.py
"""狙い方列挙型."""
from enum import Enum


class TargetStyle(str, Enum):
    """狙い方."""

    HONMEI = "honmei"
    MEDIUM_LONGSHOT = "medium_longshot"
    BIG_LONGSHOT = "big_longshot"
```

```python
# backend/src/domain/enums/betting_priority.py
"""重視ポイント列挙型."""
from enum import Enum


class BettingPriority(str, Enum):
    """重視ポイント."""

    HIT_RATE = "hit_rate"
    ROI = "roi"
    BALANCED = "balanced"
```

`backend/src/domain/enums/__init__.py` に3つのimportと`__all__`エントリを追加。

**Step 4: Run test to verify it passes**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/domain/test_betting_preference_enums.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/domain/enums/ backend/tests/domain/test_betting_preference_enums.py
git commit -m "feat: 好み設定列挙型を追加（BetTypePreference, TargetStyle, BettingPriority）"
```

---

### Task 2: BettingPreference 値オブジェクトの追加

**Files:**
- Create: `backend/src/domain/value_objects/betting_preference.py`
- Modify: `backend/src/domain/value_objects/__init__.py`
- Modify: `backend/tests/domain/test_betting_preference_enums.py`（テスト追加）

**Step 1: Write the failing test**

`backend/tests/domain/test_betting_preference_enums.py` に追加:

```python
from src.domain.value_objects import BettingPreference


class TestBettingPreference:
    """BettingPreference値オブジェクトのテスト."""

    def test_デフォルト値で作成できる(self):
        pref = BettingPreference.default()
        assert pref.bet_type_preference == BetTypePreference.AUTO
        assert pref.target_style == TargetStyle.MEDIUM_LONGSHOT
        assert pref.priority == BettingPriority.BALANCED

    def test_指定した値で作成できる(self):
        pref = BettingPreference(
            bet_type_preference=BetTypePreference.TRIO_FOCUSED,
            target_style=TargetStyle.BIG_LONGSHOT,
            priority=BettingPriority.ROI,
        )
        assert pref.bet_type_preference == BetTypePreference.TRIO_FOCUSED

    def test_to_dictで辞書に変換できる(self):
        pref = BettingPreference.default()
        d = pref.to_dict()
        assert d == {
            "bet_type_preference": "auto",
            "target_style": "medium_longshot",
            "priority": "balanced",
        }

    def test_from_dictで復元できる(self):
        data = {
            "bet_type_preference": "trio_focused",
            "target_style": "big_longshot",
            "priority": "roi",
        }
        pref = BettingPreference.from_dict(data)
        assert pref.bet_type_preference == BetTypePreference.TRIO_FOCUSED
        assert pref.target_style == TargetStyle.BIG_LONGSHOT
        assert pref.priority == BettingPriority.ROI

    def test_from_dictで空辞書はデフォルト(self):
        pref = BettingPreference.from_dict({})
        assert pref == BettingPreference.default()

    def test_from_dictでNoneはデフォルト(self):
        pref = BettingPreference.from_dict(None)
        assert pref == BettingPreference.default()
```

**Step 2: Run test to verify it fails**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/domain/test_betting_preference_enums.py::TestBettingPreference -v`
Expected: FAIL with ImportError

**Step 3: Write minimal implementation**

```python
# backend/src/domain/value_objects/betting_preference.py
"""好み設定値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass

from ..enums import BetTypePreference, BettingPriority, TargetStyle


@dataclass(frozen=True)
class BettingPreference:
    """ユーザーの馬券購入好み設定."""

    bet_type_preference: BetTypePreference
    target_style: TargetStyle
    priority: BettingPriority

    @classmethod
    def default(cls) -> BettingPreference:
        """デフォルト値で作成する."""
        return cls(
            bet_type_preference=BetTypePreference.AUTO,
            target_style=TargetStyle.MEDIUM_LONGSHOT,
            priority=BettingPriority.BALANCED,
        )

    def to_dict(self) -> dict:
        """辞書に変換する."""
        return {
            "bet_type_preference": self.bet_type_preference.value,
            "target_style": self.target_style.value,
            "priority": self.priority.value,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> BettingPreference:
        """辞書から復元する."""
        if not data:
            return cls.default()
        return cls(
            bet_type_preference=BetTypePreference(data.get("bet_type_preference", "auto")),
            target_style=TargetStyle(data.get("target_style", "medium_longshot")),
            priority=BettingPriority(data.get("priority", "balanced")),
        )
```

`backend/src/domain/value_objects/__init__.py` にimportと`__all__`エントリを追加。

**Step 4: Run test to verify it passes**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/domain/test_betting_preference_enums.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/src/domain/value_objects/ backend/tests/domain/test_betting_preference_enums.py
git commit -m "feat: BettingPreference値オブジェクトを追加"
```

---

### Task 3: Agentエンティティの拡張

**Files:**
- Modify: `backend/src/domain/entities/agent.py`
- Modify: `backend/tests/domain/test_agent.py`

**Step 1: Write the failing test**

`backend/tests/domain/test_agent.py` に追加:

```python
from src.domain.value_objects import BettingPreference
from src.domain.enums import BetTypePreference, TargetStyle, BettingPriority


class TestAgentBettingPreference:
    """エージェントの好み設定テスト."""

    def test_デフォルトの好み設定で作成される(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        assert agent.betting_preference == BettingPreference.default()
        assert agent.custom_instructions is None

    def test_好み設定を更新できる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        new_pref = BettingPreference(
            bet_type_preference=BetTypePreference.TRIO_FOCUSED,
            target_style=TargetStyle.BIG_LONGSHOT,
            priority=BettingPriority.ROI,
        )
        agent.update_preference(new_pref, "三連単の1着固定が好き")

        assert agent.betting_preference.bet_type_preference == BetTypePreference.TRIO_FOCUSED
        assert agent.custom_instructions == "三連単の1着固定が好き"

    def test_custom_instructionsは200文字以内(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        with pytest.raises(ValueError, match="200"):
            agent.update_preference(
                BettingPreference.default(),
                "あ" * 201,
            )

    def test_custom_instructionsがNoneでも更新できる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        agent.update_preference(BettingPreference.default(), None)
        assert agent.custom_instructions is None
```

**Step 2: Run test to verify it fails**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/domain/test_agent.py::TestAgentBettingPreference -v`
Expected: FAIL (AttributeError)

**Step 3: Write minimal implementation**

`backend/src/domain/entities/agent.py` を修正:

- import `BettingPreference` を追加
- `Agent` dataclass に `betting_preference: BettingPreference` と `custom_instructions: str | None = None` フィールドを追加（default_factory付き）
- `create()` で `betting_preference=BettingPreference.default()`, `custom_instructions=None` を設定
- `update_preference(preference, custom_instructions)` メソッドを追加（200文字バリデーション付き）

**Step 4: Run test to verify it passes**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/domain/test_agent.py -v`
Expected: ALL PASS（既存テストも含む）

**Step 5: Commit**

```bash
git add backend/src/domain/entities/agent.py backend/tests/domain/test_agent.py
git commit -m "feat: Agentエンティティにbetting_preferenceとcustom_instructionsを追加"
```

---

### Task 4: DynamoDBリポジトリの拡張

**Files:**
- Modify: `backend/src/infrastructure/repositories/dynamodb_agent_repository.py`
- Modify: `backend/src/infrastructure/repositories/in_memory_agent_repository.py`（InMemoryは変更不要だが確認）

**Step 1: Write the failing test**

既存の `tests/application/test_agent_use_cases.py` のテストが全部通ることを確認し、InMemoryリポジトリが新フィールドを正しく扱えることを確認:

```python
# tests/infrastructure/test_dynamodb_agent_repository_serialization.py
"""DynamoDBリポジトリのシリアライズテスト."""
from src.domain.entities import Agent
from src.domain.enums import AgentStyle, BetTypePreference, TargetStyle, BettingPriority
from src.domain.identifiers import AgentId, UserId
from src.domain.value_objects import AgentName, BettingPreference
from src.infrastructure.repositories.dynamodb_agent_repository import DynamoDBAgentRepository


class TestDynamoDBAgentSerialization:
    """DynamoDBシリアライズのテスト."""

    def test_好み設定ありのエージェントをシリアライズできる(self):
        agent = Agent.create(
            agent_id=AgentId("agt_001"),
            user_id=UserId("usr_001"),
            name=AgentName("ハヤテ"),
            base_style=AgentStyle.SOLID,
        )
        agent.update_preference(
            BettingPreference(
                bet_type_preference=BetTypePreference.TRIO_FOCUSED,
                target_style=TargetStyle.BIG_LONGSHOT,
                priority=BettingPriority.ROI,
            ),
            "三連単が好き",
        )
        item = DynamoDBAgentRepository._to_dynamodb_item(agent)
        assert item["betting_preference"] == {
            "bet_type_preference": "trio_focused",
            "target_style": "big_longshot",
            "priority": "roi",
        }
        assert item["custom_instructions"] == "三連単が好き"

    def test_好み設定ありのアイテムからエージェントを復元できる(self):
        item = {
            "agent_id": "agt_001",
            "user_id": "usr_001",
            "name": "ハヤテ",
            "base_style": "solid",
            "performance": {},
            "betting_preference": {
                "bet_type_preference": "trio_focused",
                "target_style": "big_longshot",
                "priority": "roi",
            },
            "custom_instructions": "三連単が好き",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        agent = DynamoDBAgentRepository._from_dynamodb_item(item)
        assert agent.betting_preference.bet_type_preference == BetTypePreference.TRIO_FOCUSED
        assert agent.custom_instructions == "三連単が好き"

    def test_好み設定なしの既存アイテムから復元するとデフォルト(self):
        item = {
            "agent_id": "agt_001",
            "user_id": "usr_001",
            "name": "ハヤテ",
            "base_style": "solid",
            "performance": {},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        agent = DynamoDBAgentRepository._from_dynamodb_item(item)
        assert agent.betting_preference == BettingPreference.default()
        assert agent.custom_instructions is None
```

**Step 2: Run test to verify it fails**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/infrastructure/test_dynamodb_agent_repository_serialization.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

`dynamodb_agent_repository.py` の `_to_dynamodb_item` に `betting_preference` と `custom_instructions` を追加。`_from_dynamodb_item` に `BettingPreference.from_dict()` での復元を追加（既存アイテム互換: キーがなければデフォルト）。

**Step 4: Run test to verify it passes**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/infrastructure/test_dynamodb_agent_repository_serialization.py -v`
Expected: ALL PASS

**Step 5: 既存テストが壊れていないか確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/domain/test_agent.py tests/application/test_agent_use_cases.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add backend/src/infrastructure/repositories/dynamodb_agent_repository.py backend/tests/infrastructure/test_dynamodb_agent_repository_serialization.py
git commit -m "feat: DynamoDBリポジトリにbetting_preference永続化を追加"
```

---

### Task 5: UpdateAgentUseCase の拡張

**Files:**
- Modify: `backend/src/application/use_cases/update_agent.py`
- Modify: `backend/tests/application/test_agent_use_cases.py`

**Step 1: Write the failing test**

`backend/tests/application/test_agent_use_cases.py` に追加:

```python
class TestUpdateAgentPreferenceUseCase:
    """エージェント好み設定更新のテスト."""

    def test_好み設定を更新できる(self):
        repo = InMemoryAgentRepository()
        CreateAgentUseCase(repo).execute("usr_001", "ハヤテ", "solid")
        uc = UpdateAgentUseCase(repo)

        result = uc.execute(
            "usr_001",
            betting_preference={
                "bet_type_preference": "trio_focused",
                "target_style": "big_longshot",
                "priority": "roi",
            },
            custom_instructions="三連単が好き",
        )
        assert result.agent.betting_preference.bet_type_preference.value == "trio_focused"
        assert result.agent.custom_instructions == "三連単が好き"

    def test_好み設定のみ更新でbase_styleは変わらない(self):
        repo = InMemoryAgentRepository()
        CreateAgentUseCase(repo).execute("usr_001", "ハヤテ", "solid")
        uc = UpdateAgentUseCase(repo)

        result = uc.execute(
            "usr_001",
            betting_preference={
                "bet_type_preference": "wide_focused",
                "target_style": "honmei",
                "priority": "hit_rate",
            },
        )
        assert result.agent.base_style == AgentStyle.SOLID
        assert result.agent.betting_preference.bet_type_preference.value == "wide_focused"

    def test_base_styleと好み設定を同時に更新できる(self):
        repo = InMemoryAgentRepository()
        CreateAgentUseCase(repo).execute("usr_001", "ハヤテ", "solid")
        uc = UpdateAgentUseCase(repo)

        result = uc.execute(
            "usr_001",
            base_style="longshot",
            betting_preference={
                "bet_type_preference": "exacta_focused",
                "target_style": "big_longshot",
                "priority": "roi",
            },
        )
        assert result.agent.base_style == AgentStyle.LONGSHOT
        assert result.agent.betting_preference.bet_type_preference.value == "exacta_focused"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/application/test_agent_use_cases.py::TestUpdateAgentPreferenceUseCase -v`
Expected: FAIL (TypeError)

**Step 3: Write minimal implementation**

`update_agent.py` の `execute()` に `betting_preference: dict | None = None` と `custom_instructions: str | None = ...` (sentinel) パラメータを追加。`betting_preference` が渡されたら `BettingPreference.from_dict()` で変換して `agent.update_preference()` を呼ぶ。

**Step 4: Run test to verify it passes**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/application/test_agent_use_cases.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/src/application/use_cases/update_agent.py backend/tests/application/test_agent_use_cases.py
git commit -m "feat: UpdateAgentUseCaseにbetting_preference更新を追加"
```

---

### Task 6: APIハンドラーの拡張

**Files:**
- Modify: `backend/src/api/handlers/agent.py`
- Modify: `backend/tests/api/handlers/test_agent.py`

**Step 1: Write the failing test**

`backend/tests/api/handlers/test_agent.py` に追加（既存テストのパターンに合わせる）:

```python
def test_好み設定を更新できる(self):
    # まずエージェント作成
    # ...（既存パターンに合わせて）

    # 好み設定を更新
    event = self._make_event(
        method="PUT",
        path="/agents/me",
        body={
            "betting_preference": {
                "bet_type_preference": "trio_focused",
                "target_style": "big_longshot",
                "priority": "roi",
            },
            "custom_instructions": "三連単が好き",
        },
        user_id="usr_001",
    )
    response = agent_handler(event, None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["data"]["betting_preference"]["bet_type_preference"] == "trio_focused"
    assert body["data"]["custom_instructions"] == "三連単が好き"
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**

`_update_agent()` で `betting_preference` と `custom_instructions` をbodyから取得し、`use_case.execute()` に渡す。`_agent_to_dict()` にも `betting_preference` と `custom_instructions` を追加。

バリデーション:
- `betting_preference` は省略可（dict型チェック）
- `bet_type_preference` の値は `trio_focused/exacta_focused/quinella_focused/wide_focused/auto` のみ
- `target_style` の値は `honmei/medium_longshot/big_longshot` のみ
- `priority` の値は `hit_rate/roi/balanced` のみ
- `custom_instructions` は省略可（str型、200文字チェック）

**Step 4: Run test to verify it passes**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/api/handlers/test_agent.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/src/api/handlers/agent.py backend/tests/api/handlers/test_agent.py
git commit -m "feat: PUT /agents/me APIにbetting_preference対応を追加"
```

---

### Task 7: AgentCoreプロンプトへのcustom_instructions反映

**Files:**
- Modify: `backend/agentcore/prompts/agent_prompt.py`
- Modify: `backend/tests/agentcore/test_agent_prompt.py`

**Step 1: Write the failing test**

```python
def test_custom_instructionsがプロンプトに含まれる(self):
    agent_data = {
        "name": "ハヤテ",
        "base_style": "solid",
        "stats": {},
        "performance": {},
        "level": 1,
        "custom_instructions": "三連単の1着固定が好き",
    }
    prompt = get_agent_prompt_addition(agent_data)
    assert "ユーザーの追加指示" in prompt
    assert "三連単の1着固定が好き" in prompt

def test_custom_instructionsがNoneの場合はセクションなし(self):
    agent_data = {
        "name": "ハヤテ",
        "base_style": "solid",
        "stats": {},
        "performance": {},
        "level": 1,
    }
    prompt = get_agent_prompt_addition(agent_data)
    assert "ユーザーの追加指示" not in prompt
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**

`get_agent_prompt_addition()` の末尾に `custom_instructions` セクションを追加:

```python
custom_instructions = agent_data.get("custom_instructions")
custom_section = ""
if custom_instructions:
    custom_section = f"""### ユーザーの追加指示
- {custom_instructions}
"""
```

返値のフォーマット文字列に `{custom_section}` を追加。

**Step 4: Run test to verify it passes**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/agentcore/test_agent_prompt.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/agentcore/prompts/agent_prompt.py backend/tests/agentcore/test_agent_prompt.py
git commit -m "feat: エージェントプロンプトにcustom_instructionsを反映"
```

---

### Task 8: bet_proposal.py への好み設定反映

**Files:**
- Modify: `backend/agentcore/tools/bet_proposal.py`
- Modify: `backend/tests/agentcore/test_bet_proposal.py`

**Step 1: Write the failing tests**

好み設定の3つの軸について、それぞれ影響するロジックのテストを追加:

```python
class TestBettingPreferenceIntegration:
    """好み設定が買い目生成に反映されるテスト."""

    def test_bet_type_preferenceがTRIO_FOCUSEDの場合は三連系が優先される(self):
        # _get_character_config に preference を渡して券種が変わることを確認
        config = _get_preference_config(
            character_type="analyst",
            betting_preference={"bet_type_preference": "trio_focused"},
        )
        # difficulty_bet_types の全レベルで trio 系が含まれる
        for level, bet_types in config["difficulty_bet_types"].items():
            assert any("trio" in bt for bt in bet_types)

    def test_target_styleがBIG_LONGSHOTの場合はリスクレベルが高い(self):
        config = _get_preference_config(
            character_type="analyst",
            betting_preference={"target_style": "big_longshot"},
        )
        # 高リスク券種が出現する
        assert "trio" in config["difficulty_bet_types"][3] or "trifecta" in config["difficulty_bet_types"][3]

    def test_priorityがHIT_RATEの場合はmax_partnersが多い(self):
        config = _get_preference_config(
            character_type="analyst",
            betting_preference={"priority": "hit_rate"},
        )
        assert config["max_partners"] >= 5

    def test_priorityがROIの場合はmax_partnersが少ない(self):
        config = _get_preference_config(
            character_type="analyst",
            betting_preference={"priority": "roi"},
        )
        assert config["max_partners"] <= 3

    def test_好み設定なしの場合はデフォルト(self):
        config = _get_preference_config(character_type="analyst", betting_preference=None)
        assert config["max_partners"] == MAX_PARTNERS  # デフォルト値
```

**Step 2: Run test to verify it fails**

**Step 3: Write minimal implementation**

`bet_proposal.py` に以下を追加:

1. 好み設定の定数マッピング（設計ドキュメント通り `TARGET_STYLE_RISK`, `BET_TYPE_FILTER`, `PRIORITY_WEIGHTS`）
2. `_get_preference_config(character_type, betting_preference)` 関数: `_get_character_config()` の結果に好み設定を上書きする
3. 既存の `generate_bet_proposal` ツール関数で `betting_preference` パラメータを受け取り、`_get_preference_config()` を使うように変更

**Step 4: Run test to verify it passes**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest tests/agentcore/test_bet_proposal.py -v`
Expected: ALL PASS（既存テストも含む）

**Step 5: Commit**

```bash
git add backend/agentcore/tools/bet_proposal.py backend/tests/agentcore/test_bet_proposal.py
git commit -m "feat: bet_proposalに好み設定（券種/狙い方/重視ポイント）の反映を追加"
```

---

### Task 9: フロントエンド型定義とAPIクライアント拡張

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/stores/agentStore.ts`

**Step 1: 型定義を追加**

`frontend/src/types/index.ts` に追加:

```typescript
// 好み設定
export type BetTypePreference = 'trio_focused' | 'exacta_focused' | 'quinella_focused' | 'wide_focused' | 'auto';
export type TargetStyle = 'honmei' | 'medium_longshot' | 'big_longshot';
export type BettingPriorityType = 'hit_rate' | 'roi' | 'balanced';

export interface BettingPreference {
  bet_type_preference: BetTypePreference;
  target_style: TargetStyle;
  priority: BettingPriorityType;
}

// Agent インターフェースにフィールド追加
// betting_preference?: BettingPreference;
// custom_instructions?: string | null;

// AgentData インターフェースにもフィールド追加
// betting_preference?: BettingPreference;
// custom_instructions?: string | null;
```

既存の `Agent` と `AgentData` インターフェースに `betting_preference` と `custom_instructions` を追加。

**Step 2: APIクライアント拡張**

`frontend/src/api/client.ts` の `updateAgent()` メソッドのシグネチャを拡張:

```typescript
updateAgent(
  baseStyle?: AgentStyleId,
  bettingPreference?: BettingPreference,
  customInstructions?: string | null,
)
```

**Step 3: agentStore拡張**

`agentStore.ts` の `updateAgent` を拡張してpreference引数を受け取れるようにする。`getAgentData` にも `betting_preference` と `custom_instructions` を含める。

**Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/stores/agentStore.ts
git commit -m "feat: フロントエンド型定義・APIクライアント・storeにbetting_preference対応を追加"
```

---

### Task 10: フロントエンドUI（好み設定セクション）

**Files:**
- Modify: `frontend/src/pages/AgentProfilePage.tsx`
- Create: `frontend/src/constants/bettingPreferences.ts`（ラベル定数）

**Step 1: ラベル定数を作成**

```typescript
// frontend/src/constants/bettingPreferences.ts
export const BET_TYPE_PREFERENCE_OPTIONS = [
  { value: 'trio_focused', label: '三連系重視' },
  { value: 'exacta_focused', label: '馬連系重視' },
  { value: 'quinella_focused', label: 'ワイド重視' },
  { value: 'auto', label: 'おまかせ' },
] as const;

export const TARGET_STYLE_OPTIONS = [
  { value: 'honmei', label: '本命' },
  { value: 'medium_longshot', label: '中穴' },
  { value: 'big_longshot', label: '大穴' },
] as const;

export const BETTING_PRIORITY_OPTIONS = [
  { value: 'hit_rate', label: '的中率重視' },
  { value: 'roi', label: '回収率重視' },
  { value: 'balanced', label: 'バランス' },
] as const;
```

**Step 2: AgentProfilePageに好み設定セクションを追加**

既存のスタイル選択UIの下に:
- 券種の好み: チップ選択（`BET_TYPE_PREFERENCE_OPTIONS`）
- 狙い方: チップ選択（`TARGET_STYLE_OPTIONS`）
- 重視ポイント: チップ選択（`BETTING_PRIORITY_OPTIONS`）
- 追加指示: テキストエリア（200文字制限、文字数カウンター付き）
- 保存ボタン（既存の更新処理を拡張）

UIパターンは既存のスタイル選択チップに合わせる。

**Step 3: 動作確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/frontend && npm run dev`
- エージェントプロフィール画面で好み設定セクションが表示される
- チップ選択で値が切り替わる
- テキストエリアに入力できる
- 保存で `PUT /agents/me` にリクエストが飛ぶ

**Step 4: Commit**

```bash
git add frontend/src/constants/bettingPreferences.ts frontend/src/pages/AgentProfilePage.tsx
git commit -m "feat: AgentProfilePageに好み設定UIを追加"
```

---

### Task 11: AgentCoreペイロードへの好み設定転送

**Files:**
- 確認: `frontend/src/stores/agentStore.ts` の `getAgentData()`
- 確認: `backend/agentcore/agent.py` の `_get_agent()` がペイロードの `agent_data` を正しく処理

**Step 1: getAgentData が好み設定を含むことを確認**

Task 9で `getAgentData` に `betting_preference` と `custom_instructions` を追加済み。チャットUIがAgentCoreに送るペイロードにこれらが含まれることを確認。

**Step 2: AgentCoreの agent.py で betting_preference を bet_proposal ツールに渡す**

`backend/agentcore/agent.py` 内で `agent_data` から `betting_preference` を取り出し、`generate_bet_proposal` ツール呼び出し時にパラメータとして渡されるようにする。具体的には、ツールの `@tool` デコレータが付いた関数に `betting_preference` 引数を追加済み（Task 8）なので、エージェントのシステムプロンプトでツール使用時にこの情報を渡すよう指示する。

**Step 3: Commit**

```bash
git add backend/agentcore/agent.py
git commit -m "feat: AgentCoreペイロードにbetting_preferenceを転送"
```

---

### Task 12: 全体テスト実行と回帰確認

**Step 1: バックエンド全テスト実行**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/backend && uv run pytest -v`
Expected: ALL PASS

**Step 2: フロントエンドビルド確認**

Run: `cd /home/inoue-d/dev/baken-kaigi/feat-agent-preference/frontend && npm run build`
Expected: SUCCESS

**Step 3: DDD設計ドキュメント更新**

`aidlc-docs/construction/unit_01_ai_dialog_public/docs/` の以下を更新:
- `value_objects.md` に `BettingPreference` を追加
- `entities.md` の Agent に `betting_preference` と `custom_instructions` を追加

**Step 4: Commit**

```bash
git add aidlc-docs/
git commit -m "docs: DDD設計ドキュメントにBettingPreference関連を追加"
```
