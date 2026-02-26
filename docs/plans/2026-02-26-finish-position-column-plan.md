# 着順カラム追加 Implementation Plan

**Goal:** RaceDashboardPage の出走馬テーブルに着順カラムを常時表示する（未確定は「-」、1〜3着はハイライト）

**Architecture:** `get_race_detail` APIレスポンスに `finish_position` を追加し、フロントエンドで表示。DB（`baken-kaigi-runners`テーブル）にはすでに `finish_position` が保存されているため、新規データソースは不要。

**Tech Stack:** Python (Lambda backend), React + TypeScript (frontend), DynamoDB

---

### Task 1: バックエンド — RunnerData に finish_position フィールド追加

**Files:**
- Modify: `backend/src/domain/ports/race_data_provider.py:33-43`
- Modify: `backend/src/infrastructure/providers/dynamodb_race_data_provider.py:158-169`
- Modify: `backend/src/api/handlers/races.py:196-211`
- Test: `backend/tests/api/handlers/test_races.py`

**Step 1: Write the failing test**

`backend/tests/api/handlers/test_races.py` の `TestGetRaceDetailHandler` クラスに追加:

```python
def test_着順がレスポンスに含まれる(self) -> None:
    """着順付きのランナーがレスポンスに含まれることを確認."""
    from src.api.handlers.races import get_race_detail

    provider = MockRaceDataProvider()
    provider.add_race(
        RaceData(
            race_id="2024060111",
            race_name="テストレース",
            race_number=11,
            venue="東京",
            start_time=datetime(2024, 6, 1, 15, 40),
            betting_deadline=datetime(2024, 6, 1, 15, 35),
            track_condition="良",
        )
    )
    provider.add_runners(
        "2024060111",
        [
            RunnerData(
                horse_number=1,
                horse_name="一着馬",
                horse_id="h1",
                jockey_name="騎手A",
                jockey_id="j1",
                odds="3.5",
                popularity=1,
                finish_position=1,
            ),
            RunnerData(
                horse_number=2,
                horse_name="未確定馬",
                horse_id="h2",
                jockey_name="騎手B",
                jockey_id="j2",
                odds="10.0",
                popularity=5,
            ),
        ],
    )
    Dependencies.set_race_data_provider(provider)

    event = {"pathParameters": {"race_id": "2024060111"}}
    response = get_race_detail(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["runners"][0]["finish_position"] == 1
    assert body["runners"][1].get("finish_position") is None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/handlers/test_races.py::TestGetRaceDetailHandler::test_着順がレスポンスに含まれる -v`
Expected: FAIL — `RunnerData` に `finish_position` パラメータがない

**Step 3: Write minimal implementation**

3a. `backend/src/domain/ports/race_data_provider.py:43` — `RunnerData` にフィールド追加:
```python
waku_ban: int = 0  # 枠番（1-8）
finish_position: int | None = None  # 着順（未確定はNone）
```

3b. `backend/src/infrastructure/providers/dynamodb_race_data_provider.py:160-169` — `_to_runner_data` でマッピング:
```python
@staticmethod
def _to_runner_data(item: dict) -> RunnerData:
    """DynamoDB アイテムを RunnerData に変換する."""
    fp = item.get("finish_position")
    return RunnerData(
        horse_number=int(item["horse_number"]),
        horse_name=item["horse_name"],
        horse_id=item["horse_id"],
        jockey_name=item["jockey_name"],
        jockey_id=item["jockey_id"],
        odds=str(item.get("odds", "0")),
        popularity=int(item.get("popularity", 0)),
        waku_ban=int(item.get("waku_ban", 0)),
        finish_position=int(fp) if fp is not None else None,
    )
```

3c. `backend/src/api/handlers/races.py:196-211` — `get_race_detail` の runner_dict 構築に追加:
```python
runner_dict = {
    "horse_number": r.horse_number,
    "waku_ban": r.waku_ban,
    "horse_name": r.horse_name,
    "jockey_name": r.jockey_name,
    "odds": r.odds,
    "popularity": r.popularity,
    "finish_position": r.finish_position,
}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/api/handlers/test_races.py::TestGetRaceDetailHandler -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/src/domain/ports/race_data_provider.py backend/src/infrastructure/providers/dynamodb_race_data_provider.py backend/src/api/handlers/races.py backend/tests/api/handlers/test_races.py
git commit -m "feat: get_race_detail APIに着順を追加"
```

---

### Task 2: フロントエンド — 型定義とマッピング

**Files:**
- Modify: `frontend/src/types/index.ts:62-71` (ApiRunner)
- Modify: `frontend/src/types/index.ts:134-145` (Horse)
- Modify: `frontend/src/types/index.ts:195-209` (mapApiRaceDetailToRaceDetail)
- Test: `frontend/src/types/index.test.ts`

**Step 1: Write the failing test**

`frontend/src/types/index.test.ts` の `describe('mapApiRaceDetailToRaceDetail')` 内に追加:

```typescript
it('着順データが正しく変換される', () => {
  const runnersWithFinish: ApiRunner[] = [
    {
      horse_number: 1,
      waku_ban: 1,
      horse_name: '一着馬',
      jockey_name: '騎手A',
      odds: '3.5',
      popularity: 1,
      finish_position: 1,
    },
    {
      horse_number: 2,
      waku_ban: 2,
      horse_name: '未確定馬',
      jockey_name: '騎手B',
      odds: '10.0',
      popularity: 5,
    },
  ]

  const detail = mapApiRaceDetailToRaceDetail(mockApiRace, runnersWithFinish)

  expect(detail.horses[0].finishPosition).toBe(1)
  expect(detail.horses[1].finishPosition).toBeUndefined()
})
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/types/index.test.ts`
Expected: FAIL — `finish_position` は `ApiRunner` に存在しない

**Step 3: Write minimal implementation**

3a. `frontend/src/types/index.ts:62-71` — `ApiRunner` に追加:
```typescript
export interface ApiRunner {
  horse_number: number;
  waku_ban: number;
  horse_name: string;
  jockey_name: string;
  odds: string;
  popularity: number;
  weight?: number;       // 馬体重(kg)
  weight_diff?: number;  // 前走比増減
  finish_position?: number;  // 着順（未確定はundefined）
}
```

3b. `frontend/src/types/index.ts:134-145` — `Horse` に追加:
```typescript
export interface Horse {
  number: number;
  wakuBan: number;
  name: string;
  jockey: string;
  odds: number;
  popularity: number;
  color: string;
  textColor: string;
  weight?: number;
  weightDiff?: number;
  finishPosition?: number;  // 着順（未確定はundefined）
}
```

3c. `frontend/src/types/index.ts:195-209` — マッピング関数に追加:
```typescript
horses: runners.map((runner) => {
  const wakuColor = getWakuColor(runner.waku_ban);
  return {
    number: runner.horse_number,
    wakuBan: runner.waku_ban,
    name: runner.horse_name,
    jockey: runner.jockey_name,
    odds: parseFloat(runner.odds),
    popularity: runner.popularity,
    color: wakuColor.background,
    textColor: wakuColor.text,
    weight: runner.weight,
    weightDiff: runner.weight_diff,
    finishPosition: runner.finish_position,
  };
}),
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/types/index.test.ts`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/types/index.test.ts
git commit -m "feat: フロントエンド型定義に着順フィールドを追加"
```

---

### Task 3: フロントエンド — テーブルに着順カラムを表示

**Files:**
- Modify: `frontend/src/pages/RaceDashboardPage.tsx:386-405` (thead) + `:450-468` (tbody)
- Modify: `frontend/src/pages/RaceDashboardPage.css`

**Step 1: RaceDashboardPage.tsx に着順カラムを追加**

テーブルヘッダ（`<thead>` 内、体重 `<th>` の前に追加）:
```tsx
<th>着順</th>
```

テーブルボディ（各行の `{/* Weight */}` セクションの前に追加）:
```tsx
{/* Finish position */}
<td className="td-finish-position">
  {horse.finishPosition != null ? (
    <span className={`finish-badge ${horse.finishPosition <= 3 ? `finish-${horse.finishPosition}` : ''}`}>
      {horse.finishPosition}
    </span>
  ) : (
    <span className="no-data">-</span>
  )}
</td>
```

**Step 2: RaceDashboardPage.css にスタイル追加**

ファイル末尾に追加:
```css
/* Finish position column */
.td-finish-position {
  min-width: 36px;
  font-weight: 700;
  font-size: 14px;
}

.finish-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
  padding: 0 4px;
  color: var(--color-text-muted);
}

.finish-badge.finish-1 {
  background: rgba(233, 69, 96, 0.2);
  color: var(--color-primary);
}

.finish-badge.finish-2 {
  background: rgba(245, 158, 11, 0.2);
  color: var(--color-warning);
}

.finish-badge.finish-3 {
  background: rgba(74, 222, 128, 0.2);
  color: var(--color-success);
}
```

**Step 3: 目視確認**

Run: `cd frontend && npm run dev`
ブラウザでレース詳細ページを開き、着順カラムが表示されることを確認。

**Step 4: Commit**

```bash
git add frontend/src/pages/RaceDashboardPage.tsx frontend/src/pages/RaceDashboardPage.css
git commit -m "feat: RaceDashboardPageに着順カラムを追加"
```

---

### Task 4: 全テスト実行 & PR作成

**Step 1: バックエンドテスト全体を実行**

Run: `cd backend && uv run pytest tests/api/handlers/test_races.py -v`
Expected: ALL PASS

**Step 2: フロントエンドテスト全体を実行**

Run: `cd frontend && npx vitest run`
Expected: ALL PASS

**Step 3: PR作成**

```bash
git push -u origin feat/finish-position-column
gh pr create --title "feat: RaceDashboardPageに着順カラムを追加" --body "..."
```
