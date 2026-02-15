# オッズAPI統合 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** オッズ取得を `GET /races/{race_id}/odds`（全券種一括）に統合し、`bet-odds` を削除する。AgentCoreの403エラーを解消する。

**Architecture:** Lambda `get_all_odds` → EC2 FastAPI `/races/{race_id}/odds` → jvd_o1~o6。フロントエンドは全券種を一括取得し、クライアント側で必要な券種を抽出する。`get_bet_odds` は完全削除。

**Tech Stack:** Python (Lambda/FastAPI), TypeScript (React), AWS CDK, pytest, vitest

**Worktree:** `/home/inoue-d/dev/baken-kaigi/odds-api-fix` (branch: `feature/odds-api-fix`)

---

## Task 1: ドメイン層 — AllOddsData モデル + get_all_odds ポート追加

**Files:**
- Modify: `backend/src/domain/ports/race_data_provider.py:469-880`
- Test: `backend/tests/api/handlers/test_races.py` (MockRaceDataProvider更新)

**Step 1: AllOddsData モデルを追加**

`race_data_provider.py` の `BetOddsData`（L469-476）を `AllOddsData` に置換する:

```python
@dataclass(frozen=True)
class AllOddsData:
    """全券種オッズデータ."""

    race_id: str
    win: dict[str, float]
    place: dict[str, dict[str, float]]
    quinella: dict[str, float]
    quinella_place: dict[str, float]
    exacta: dict[str, float]
    trio: dict[str, float]
    trifecta: dict[str, float]
```

**Step 2: RaceDataProvider に get_all_odds を追加し、get_bet_odds を削除**

`get_bet_odds`（L866-880）を削除して `get_all_odds` に置換:

```python
@abstractmethod
def get_all_odds(self, race_id: RaceId) -> AllOddsData | None:
    """全券種のオッズを一括取得する.

    Args:
        race_id: レースID

    Returns:
        全券種オッズデータ、見つからない場合はNone
    """
    pass
```

**Step 3: 全テストのMockRaceDataProviderを更新**

以下のファイルで `get_bet_odds` → `get_all_odds` に変更:
- `backend/tests/api/handlers/test_races.py:58,76-78,255-257`
- `backend/tests/api/handlers/test_statistics.py:234`
- `backend/tests/api/handlers/test_stallions.py:237`
- `backend/tests/domain/ports/test_race_data_provider.py:277`
- `backend/tests/application/use_cases/test_get_race_detail.py:224`
- `backend/tests/application/use_cases/test_get_race_list.py:233`

MockRaceDataProviderのパターン:

```python
# 旧: self._bet_odds: dict[str, BetOddsData] = {}
# 新:
self._all_odds: dict[str, AllOddsData] = {}

# 旧: def add_bet_odds(...) / def get_bet_odds(...)
# 新:
def add_all_odds(self, race_id: str, all_odds: AllOddsData) -> None:
    self._all_odds[race_id] = all_odds

def get_all_odds(self, race_id: RaceId) -> AllOddsData | None:
    return self._all_odds.get(str(race_id))
```

**Step 4: テスト実行**

Run: `cd backend && uv run pytest tests/domain/ports/test_race_data_provider.py -v`
Expected: PASS

**Step 5: コミット**

```bash
git add backend/src/domain/ports/race_data_provider.py backend/tests/
git commit -m "refactor: BetOddsDataをAllOddsDataに置換、get_bet_oddsをget_all_oddsに変更"
```

---

## Task 2: インフラ層 — JraVanRaceDataProvider.get_all_odds 実装

**Files:**
- Modify: `backend/src/infrastructure/providers/jravan_race_data_provider.py:1321-1342`
- Test: `backend/tests/infrastructure/providers/` (既存テストあれば更新)

**Step 1: get_bet_odds を get_all_odds に置換**

`jravan_race_data_provider.py` L1321-1342 の `get_bet_odds` を削除し:

```python
def get_all_odds(self, race_id: RaceId) -> AllOddsData | None:
    """全券種のオッズを一括取得する."""
    try:
        response = self._session.get(
            f"{self._base_url}/races/{race_id.value}/odds",
            timeout=self._timeout,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return AllOddsData(
            race_id=data["race_id"],
            win=data.get("win", {}),
            place=data.get("place", {}),
            quinella=data.get("quinella", {}),
            quinella_place=data.get("quinella_place", {}),
            exacta=data.get("exacta", {}),
            trio=data.get("trio", {}),
            trifecta=data.get("trifecta", {}),
        )
    except requests.RequestException as e:
        logger.warning(f"Could not get all odds for race {race_id}: {e}")
        return None
```

**Step 2: import 更新**

`BetOddsData` → `AllOddsData` に変更。

**Step 3: テスト実行**

Run: `cd backend && uv run pytest tests/ -k "not agentcore" --timeout=30 -x -q`
Expected: PASS

**Step 4: コミット**

```bash
git add backend/src/infrastructure/providers/jravan_race_data_provider.py
git commit -m "feat: JraVanRaceDataProvider.get_all_oddsを実装（EC2 /odds経由）"
```

---

## Task 3: Lambda ハンドラ — get_bet_odds → get_all_odds 置換

**Files:**
- Modify: `backend/src/api/handlers/races.py:355-398`
- Modify: `backend/tests/api/handlers/test_races.py:1044-1256` (TestGetBetOddsHandler)

**Step 1: テストを先に書く（TDD: Red）**

`test_races.py` の `TestGetBetOddsHandler`（L1044-1256）を完全に削除し、新しいテストクラスに置換:

```python
class TestGetAllOddsHandler:
    """GET /races/{race_id}/odds ハンドラーのテスト."""

    def test_全券種オッズを取得できる(self) -> None:
        from src.api.handlers.races import get_all_odds

        provider = MockRaceDataProvider()
        provider.add_all_odds(
            "2024060111",
            AllOddsData(
                race_id="2024060111",
                win={"1": 3.5, "2": 12.0},
                place={"1": {"min": 1.2, "max": 1.5}},
                quinella={"1-2": 64.8},
                quinella_place={"1-2": 10.5},
                exacta={"1-2": 128.5},
                trio={"1-2-3": 341.9},
                trifecta={"1-2-3": 2048.3},
            ),
        )
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"race_id": "2024060111"},
        }

        response = get_all_odds(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["race_id"] == "2024060111"
        assert body["win"]["1"] == 3.5
        assert body["place"]["1"]["min"] == 1.2
        assert body["quinella"]["1-2"] == 64.8
        assert body["trifecta"]["1-2-3"] == 2048.3

    def test_オッズが見つからない場合は404(self) -> None:
        from src.api.handlers.races import get_all_odds

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {"race_id": "2024060111"},
        }

        response = get_all_odds(event, None)

        assert response["statusCode"] == 404

    def test_race_idが指定されていない場合は400(self) -> None:
        from src.api.handlers.races import get_all_odds

        provider = MockRaceDataProvider()
        Dependencies.set_race_data_provider(provider)

        event = {
            "pathParameters": {},
            "queryStringParameters": None,
        }

        response = get_all_odds(event, None)

        assert response["statusCode"] == 400
```

**Step 2: テスト実行（Red確認）**

Run: `cd backend && uv run pytest tests/api/handlers/test_races.py::TestGetAllOddsHandler -v`
Expected: FAIL（`get_all_odds` が存在しない）

**Step 3: ハンドラ実装（Green）**

`races.py` の `get_bet_odds`（L355-398）を削除し:

```python
def get_all_odds(event: dict, context: Any) -> dict:
    """全券種のオッズを一括取得する.

    GET /races/{race_id}/odds

    Path Parameters:
        race_id: レースID

    Returns:
        全券種オッズデータ
    """
    race_id_str = get_path_parameter(event, "race_id")
    if not race_id_str:
        return bad_request_response("race_id is required", event=event)

    provider = Dependencies.get_race_data_provider()
    result = provider.get_all_odds(RaceId(race_id_str))

    if result is None:
        return not_found_response("オッズデータが見つかりません", event=event)

    return success_response({
        "race_id": result.race_id,
        "win": result.win,
        "place": result.place,
        "quinella": result.quinella,
        "quinella_place": result.quinella_place,
        "exacta": result.exacta,
        "trio": result.trio,
        "trifecta": result.trifecta,
    }, event=event)
```

**Step 4: テスト実行（Green確認）**

Run: `cd backend && uv run pytest tests/api/handlers/test_races.py::TestGetAllOddsHandler -v`
Expected: PASS

**Step 5: 全テスト実行**

Run: `cd backend && uv run pytest tests/api/ -v --timeout=30 -x -q`
Expected: PASS

**Step 6: コミット**

```bash
git add backend/src/api/handlers/races.py backend/tests/api/handlers/test_races.py
git commit -m "feat: get_all_odds Lambdaハンドラ追加、get_bet_odds削除"
```

---

## Task 4: CDK — GetBetOdds Lambda → GetAllOdds Lambda 置換

**Files:**
- Modify: `cdk/stacks/api_stack.py:823-835` (Lambda定義), `1307-1311` (APIGWルート)
- Modify: `cdk/tests/test_api_stack.py:64` (Lambda関数数のコメント更新)

**Step 1: Lambda関数定義を置換**

`api_stack.py` L823-835 の `GetBetOddsFunction` を:

```python
        # 全券種オッズAPI
        get_all_odds_fn = lambda_.Function(
            self,
            "GetAllOddsFunction",
            handler="src.api.handlers.races.get_all_odds",
            code=lambda_.Code.from_asset(
                str(project_root / "backend"),
                exclude=["tests", ".venv", ".git", "__pycache__", "*.pyc"],
            ),
            function_name="baken-kaigi-get-all-odds",
            description="全券種オッズ一括取得",
            **lambda_common_props,
        )
```

**Step 2: APIGWルートを置換**

`api_stack.py` L1307-1311 を:

```python
        # /races/{race_id}/odds
        race_odds = race.add_resource("odds")
        race_odds.add_method(
            "GET", apigw.LambdaIntegration(get_all_odds_fn), api_key_required=True
        )
```

**Step 3: CDKテストのコメント更新**

`cdk/tests/test_api_stack.py` L64:
```python
"""Lambda関数が44個作成されること（API 32 + IPAT 7 + 賭け履歴 1 + 損失制限 1 + エージェント 2 + オッズ 1）."""
```
Lambda関数数は44のまま変わらない（1削除 + 1追加 = ±0）。コメントのみ確認。

**Step 4: CDKテスト実行**

Run: `cd cdk && npx jest --silent 2>&1 | tail -20`
Expected: PASS

**Step 5: コミット**

```bash
git add cdk/stacks/api_stack.py cdk/tests/
git commit -m "feat: CDKでGetAllOdds Lambda + /odds APIGWルート追加、GetBetOdds削除"
```

---

## Task 5: フロントエンド — getBetOdds → getAllOdds + クライアント側抽出

**Files:**
- Modify: `frontend/src/api/client.ts:228-243`
- Modify: `frontend/src/types/index.ts:238-255`
- Modify: `frontend/src/pages/RaceDetailPage.tsx:133-147`
- Modify: `frontend/src/components/proposal/BetProposalContent.tsx:187-201,248-271`
- Modify: `frontend/src/api/client.test.ts:614-670`

**Step 1: 型定義を変更**

`types/index.ts` の `BetOddsResponse`（L249-254）を `AllOddsResponse` に置換:

```typescript
// 全券種オッズAPIレスポンス
export interface AllOddsResponse {
  race_id: string;
  win: Record<string, number>;
  place: Record<string, { min: number; max: number }>;
  quinella: Record<string, number>;
  quinella_place: Record<string, number>;
  exacta: Record<string, number>;
  trio: Record<string, number>;
  trifecta: Record<string, number>;
}
```

`BetTypeToApiName`（L238-246）は不要になるため削除。

**Step 2: APIクライアントを変更**

`client.ts` の `getBetOdds`（L228-243）を:

```typescript
  // オッズ取得
  async getAllOdds(raceId: string): Promise<ApiResponse<AllOddsResponse>> {
    return this.request<AllOddsResponse>(
      `/races/${encodeURIComponent(raceId)}/odds`
    );
  }
```

**Step 3: オッズ抽出ヘルパー関数を追加**

`types/index.ts` にヘルパーを追加:

```typescript
/**
 * AllOddsResponseから指定した買い目のオッズを抽出する.
 */
export function extractOdds(
  allOdds: AllOddsResponse,
  betType: BetType,
  horseNumbers: number[],
): { odds?: number; oddsMin?: number; oddsMax?: number } {
  // 券種名マッピング（quinella_place はレスポンスキーと同じ）
  const typeKey = betType as keyof Omit<AllOddsResponse, 'race_id'>;
  const oddsMap = allOdds[typeKey];
  if (!oddsMap) return {};

  if (betType === 'place') {
    const key = String(horseNumbers[0]);
    const entry = (oddsMap as Record<string, { min: number; max: number }>)[key];
    if (!entry) return {};
    return { oddsMin: entry.min, oddsMax: entry.max };
  }

  // キー生成: 単勝は馬番のみ、馬連/ワイド/三連複は昇順、馬単/三連単は着順のまま
  let key: string;
  if (horseNumbers.length === 1) {
    key = String(horseNumbers[0]);
  } else if (['quinella', 'quinella_place', 'trio'].includes(betType)) {
    key = [...horseNumbers].sort((a, b) => a - b).join('-');
  } else {
    key = horseNumbers.join('-');
  }

  const odds = (oddsMap as Record<string, number>)[key];
  return odds != null ? { odds } : {};
}
```

**Step 4: RaceDetailPage.tsx を更新**

L133-147 のオッズ取得部分を:

```typescript
    // オッズ取得（失敗してもカート追加はブロックしない）
    let odds: number | undefined;
    let oddsMin: number | undefined;
    let oddsMax: number | undefined;
    try {
      const oddsResult = await apiClient.getAllOdds(race.id);
      if (oddsResult.success && oddsResult.data) {
        const extracted = extractOdds(oddsResult.data, betType, horseNumbersDisplay);
        odds = extracted.odds;
        oddsMin = extracted.oddsMin;
        oddsMax = extracted.oddsMax;
      }
    } catch (error: unknown) {
      console.warn('Failed to fetch odds when adding item to cart:', error);
    }
```

import に `extractOdds` を追加。`BetTypeToApiName` の import を削除。

**Step 5: BetProposalContent.tsx を更新**

`handleAddSingle`（L187-201）と `handleAddAll`（L248-271）を同様に更新。

`handleAddAll` は全買い目分の並列 getBetOdds 呼び出しを **1回の getAllOdds 呼び出し** に統合:

```typescript
    // 全券種オッズを1回で取得
    let allOdds: AllOddsResponse | undefined;
    try {
      const oddsResult = await apiClient.getAllOdds(race.id);
      if (oddsResult.success && oddsResult.data) {
        allOdds = oddsResult.data;
      }
    } catch (error) {
      console.warn('Failed to fetch all odds:', error);
    }

    betsToAdd.forEach(({ bet, index }, i) => {
      const oddsData = allOdds
        ? extractOdds(allOdds, bet.bet_type as BetType, bet.horse_numbers)
        : { odds: undefined, oddsMin: undefined, oddsMax: undefined };
      // ... 以降の addItem 呼び出しは同じ
```

**Step 6: テスト更新**

`client.test.ts` の `getBetOdds` テスト（L614-670）を `getAllOdds` テストに置換:

```typescript
  describe('getAllOdds', () => {
    it('全券種オッズを正常に取得できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          race_id: 'race_001',
          win: { '1': 3.5 },
          place: { '1': { min: 1.2, max: 1.5 } },
          quinella: {},
          quinella_place: {},
          exacta: {},
          trio: {},
          trifecta: {},
        }),
      })

      const client = await getApiClient()
      const result = await client.getAllOdds('race_001')

      expect(result.success).toBe(true)
      expect(result.data?.win['1']).toBe(3.5)
      expect(result.data?.place['1'].min).toBe(1.2)
    })

    it('APIエラー時はエラーを返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ message: 'Not found' }),
      })

      const client = await getApiClient()
      const result = await client.getAllOdds('invalid_race')

      expect(result.success).toBe(false)
    })

    it('race_idがURLエンコードされる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ race_id: 'race/001', win: {}, place: {}, quinella: {}, quinella_place: {}, exacta: {}, trio: {}, trifecta: {} }),
      })

      const client = await getApiClient()
      await client.getAllOdds('race/001')

      const calledUrl = mockFetch.mock.calls[0][0]
      expect(calledUrl).toContain('race%2F001')
    })
  })
```

`extractOdds` のユニットテストも追加:

```typescript
describe('extractOdds', () => {
  const allOdds: AllOddsResponse = {
    race_id: 'test',
    win: { '1': 3.5, '2': 12.0 },
    place: { '1': { min: 1.2, max: 1.5 } },
    quinella: { '1-2': 64.8 },
    quinella_place: { '1-2': 10.5 },
    exacta: { '1-2': 128.5 },
    trio: { '1-2-3': 341.9 },
    trifecta: { '1-2-3': 2048.3 },
  }

  it('単勝オッズを抽出できる', () => {
    expect(extractOdds(allOdds, 'win', [1])).toEqual({ odds: 3.5 })
  })

  it('複勝オッズを抽出できる', () => {
    expect(extractOdds(allOdds, 'place', [1])).toEqual({ oddsMin: 1.2, oddsMax: 1.5 })
  })

  it('馬連オッズを昇順キーで抽出できる', () => {
    expect(extractOdds(allOdds, 'quinella', [2, 1])).toEqual({ odds: 64.8 })
  })

  it('馬単オッズを着順キーで抽出できる', () => {
    expect(extractOdds(allOdds, 'exacta', [1, 2])).toEqual({ odds: 128.5 })
  })

  it('存在しないキーは空を返す', () => {
    expect(extractOdds(allOdds, 'win', [99])).toEqual({})
  })
})
```

**Step 7: フロントエンドテスト実行**

Run: `cd frontend && npm test -- --run 2>&1 | tail -20`
Expected: PASS

**Step 8: コミット**

```bash
git add frontend/src/
git commit -m "feat: getBetOddsをgetAllOdds+クライアント側抽出に統合"
```

---

## Task 6: 全体テスト + クリーンアップ

**Step 1: バックエンド全テスト実行**

Run: `cd backend && uv run pytest --timeout=30 -x -q 2>&1 | tail -20`
Expected: PASS

**Step 2: フロントエンド全テスト実行**

Run: `cd frontend && npm test -- --run 2>&1 | tail -20`
Expected: PASS

**Step 3: CDKテスト実行**

Run: `cd cdk && npx jest --silent 2>&1 | tail -20`
Expected: PASS

**Step 4: 不要なimportのクリーンアップ**

`BetOddsData` や `BetTypeToApiName` の参照が残っていないか確認:

Run: `grep -rn "BetOddsData\|BetTypeToApiName\|get_bet_odds\|getBetOdds\|bet-odds" backend/src/ frontend/src/ cdk/stacks/`
Expected: マッチなし

**Step 5: コミット（必要に応じて）**

```bash
git add -A
git commit -m "chore: bet-odds関連の残留参照をクリーンアップ"
```

---

## 変更サマリー

| 操作 | ファイル | 概要 |
|------|---------|------|
| 置換 | `race_data_provider.py` | `BetOddsData` → `AllOddsData`, `get_bet_odds` → `get_all_odds` |
| 置換 | `jravan_race_data_provider.py` | EC2 `/bet-odds` → `/odds` に変更 |
| 置換 | `races.py` (handler) | `get_bet_odds` → `get_all_odds` ハンドラ |
| 置換 | `api_stack.py` (CDK) | `GetBetOdds` → `GetAllOdds` Lambda + `/odds` ルート |
| 置換 | `client.ts` | `getBetOdds()` → `getAllOdds()` |
| 置換 | `types/index.ts` | `BetOddsResponse` → `AllOddsResponse` + `extractOdds` ヘルパー |
| 更新 | `RaceDetailPage.tsx` | オッズ取得を `getAllOdds` + `extractOdds` に |
| 更新 | `BetProposalContent.tsx` | N回の個別取得 → 1回の一括取得に最適化 |
| 削除 | `BetTypeToApiName` | クライアント側抽出により不要 |
| 更新 | 全MockRaceDataProvider | `get_bet_odds` → `get_all_odds` |
