# カート画面改善 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** カート画面で購入金額を直接編集可能にし、JRA実オッズを全7券種で表示する

**Architecture:** JRA-VAN API (EC2 FastAPI) に券種別オッズ取得エンドポイントを追加し、バックエンド Lambda がプロキシ。フロントエンド CartPage に金額編集UIとオッズ表示を追加する。

**Tech Stack:** Python (FastAPI, pg8000), Python (Lambda), TypeScript (React, Zustand)

**設計ドキュメント:** `docs/plans/2026-02-14-cart-improvement-design.md`

---

## Task 1: JRA-VAN API — 馬連オッズ取得 (jvd_o2)

**Files:**
- Modify: `jravan-api/database.py` (末尾に追加)
- Test: `jravan-api/test_odds.py` (新規テスト追加)

**背景:**
jvd_o2 テーブルには馬連オッズが格納されている。JRA-VAN仕様ではカラム名等の正確な構造はテーブルスキーマ確認が必要。まずテーブル構造を調査してから実装する。

**Step 1: jvd_o2 テーブルのスキーマを確認**

jravan-api の EC2 環境で PostgreSQL のカラム構造を確認する:
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'jvd_o2' ORDER BY ordinal_position;
```

**Step 2: テスト作成**

`jravan-api/test_odds.py` にテストを追加。既存の `_parse_tansho_odds`, `_parse_fukusho_odds` のテストパターンを参考にする。

```python
def test_get_quinella_odds_正常取得():
    """馬連オッズが正常に取得できること."""
    # テスト内容はスキーマ調査後に確定
    pass

def test_get_quinella_odds_データなし():
    """データがない場合Noneを返すこと."""
    pass
```

**Step 3: database.py に `get_quinella_odds` 実装**

既存の `get_place_odds()` と同じパターンで実装:
- `_parse_race_id()` でレースID解析
- jvd_o2 からデータ取得
- パース関数でオッズ抽出

**Step 4: テスト実行で通ることを確認**

**Step 5: コミット**
```bash
git add jravan-api/database.py jravan-api/test_odds.py
git commit -m "feat: 馬連オッズ取得関数追加 (jvd_o2)"
```

---

## Task 2: JRA-VAN API — ワイドオッズ取得 (jvd_o3)

**Files:**
- Modify: `jravan-api/database.py`
- Test: `jravan-api/test_odds.py`

**Step 1: jvd_o3 テーブルのスキーマを確認**

ワイドは幅のあるオッズ (odds_min, odds_max) を返す。複勝と同様のデータ構造の可能性が高い。

**Step 2: テスト作成**

```python
def test_get_wide_odds_正常取得():
    """ワイドオッズが min/max で取得できること."""
    pass

def test_get_wide_odds_データなし():
    """データがない場合Noneを返すこと."""
    pass
```

**Step 3: `get_wide_odds` 実装**

**Step 4: テスト実行確認**

**Step 5: コミット**
```bash
git commit -m "feat: ワイドオッズ取得関数追加 (jvd_o3)"
```

---

## Task 3: JRA-VAN API — 馬単・三連複・三連単オッズ取得 (jvd_o4, o5, o6)

**Files:**
- Modify: `jravan-api/database.py`
- Test: `jravan-api/test_odds.py`

**Step 1: jvd_o4, jvd_o5, jvd_o6 テーブルのスキーマを確認**

**Step 2: テスト作成**

各券種ごとに正常ケース + データなしケース:
- `test_get_exacta_odds_正常取得` / `test_get_exacta_odds_データなし`
- `test_get_trio_odds_正常取得` / `test_get_trio_odds_データなし`
- `test_get_trifecta_odds_正常取得` / `test_get_trifecta_odds_データなし`

**Step 3: `get_exacta_odds`, `get_trio_odds`, `get_trifecta_odds` 実装**

**Step 4: テスト実行確認**

**Step 5: コミット**
```bash
git commit -m "feat: 馬単・三連複・三連単オッズ取得関数追加 (jvd_o4〜o6)"
```

---

## Task 4: JRA-VAN API — bet-odds エンドポイント追加

**Files:**
- Modify: `jravan-api/main.py`

**Step 1: レスポンスモデル追加**

```python
class BetOddsResponse(BaseModel):
    """券種別オッズレスポンス."""
    bet_type: str
    horse_numbers: list[int]
    odds: float | None = None
    odds_min: float | None = None
    odds_max: float | None = None
```

**Step 2: エンドポイント実装**

```python
@app.get("/races/{race_id}/bet-odds", response_model=BetOddsResponse)
def get_bet_odds(
    race_id: str,
    bet_type: str = Query(..., description="券種 (win/place/quinella/wide/exacta/trio/trifecta)"),
    horses: str = Query(..., description="馬番 (カンマ区切り, 例: 3,7)"),
):
    """指定した買い目のオッズを取得する."""
    # horsesをパース
    horse_numbers = [int(h.strip()) for h in horses.split(",")]

    # bet_typeに応じてDB関数を呼び出し
    # win → 既存 get_win_odds → 該当馬番のオッズ抽出
    # place → 既存 get_place_odds → 該当馬番のmin/max抽出
    # quinella → get_quinella_odds
    # wide → get_wide_odds
    # exacta → get_exacta_odds
    # trio → get_trio_odds
    # trifecta → get_trifecta_odds
```

**Step 3: 手動テスト**

```bash
curl "http://localhost:8000/races/20260215_05_01/bet-odds?bet_type=win&horses=3"
```

**Step 4: コミット**
```bash
git commit -m "feat: 券種別オッズ取得エンドポイント追加 (GET /races/{id}/bet-odds)"
```

---

## Task 5: バックエンド — BetOddsData ドメインモデル追加

**Files:**
- Modify: `backend/src/domain/ports/race_data_provider.py`
- Test: 型定義のみなのでテスト不要

**Step 1: BetOddsData を追加**

`race_data_provider.py` の既存 `@dataclass` 定義群の後に追加:

```python
@dataclass(frozen=True)
class BetOddsData:
    """券種別オッズデータ."""
    bet_type: str
    horse_numbers: list[int]
    odds: float | None = None
    odds_min: float | None = None
    odds_max: float | None = None
```

**Step 2: RaceDataProvider ABC に `get_bet_odds` メソッド追加**

```python
@abstractmethod
def get_bet_odds(self, race_id: RaceId, bet_type: str, horse_numbers: list[int]) -> BetOddsData | None:
    """指定した買い目のオッズを取得する."""
```

**Step 3: コミット**
```bash
git commit -m "feat: BetOddsData ドメインモデルとポート定義追加"
```

---

## Task 6: バックエンド — JraVanRaceDataProvider に get_bet_odds 実装

**Files:**
- Modify: `backend/src/infrastructure/providers/jravan_race_data_provider.py`
- Test: `backend/tests/infrastructure/` (ユニットテスト)

**Step 1: テスト作成**

```python
def test_get_bet_odds_単勝():
    """単勝オッズを取得できること."""
    # JRA-VAN APIのレスポンスをモック
    pass

def test_get_bet_odds_ワイド():
    """ワイドオッズがmin/maxで取得できること."""
    pass

def test_get_bet_odds_不正なbet_type():
    """不正な券種でNoneを返すこと."""
    pass
```

**Step 2: `get_bet_odds` 実装**

JRA-VAN API の `/races/{race_id}/bet-odds` をHTTP GETで呼び出し、
レスポンスを `BetOddsData` に変換して返す。

```python
def get_bet_odds(self, race_id: RaceId, bet_type: str, horse_numbers: list[int]) -> BetOddsData | None:
    horses_param = ",".join(str(h) for h in horse_numbers)
    response = self._session.get(
        f"{self._base_url}/races/{race_id.value}/bet-odds",
        params={"bet_type": bet_type, "horses": horses_param},
        timeout=self._timeout,
    )
    if response.status_code != 200:
        return None
    data = response.json()
    return BetOddsData(
        bet_type=data["bet_type"],
        horse_numbers=data["horse_numbers"],
        odds=data.get("odds"),
        odds_min=data.get("odds_min"),
        odds_max=data.get("odds_max"),
    )
```

**Step 3: テスト実行確認**

Run: `cd backend && uv run pytest tests/ -k "bet_odds" -v`

**Step 4: コミット**
```bash
git commit -m "feat: JraVanRaceDataProvider に get_bet_odds 実装"
```

---

## Task 7: バックエンド — bet-odds API ハンドラー追加

**Files:**
- Modify: `backend/src/api/handlers/races.py`
- Modify: `backend/src/api/router.py` (ルーティング追加)
- Test: `backend/tests/api/`

**Step 1: テスト作成**

```python
def test_get_bet_odds_正常():
    """bet-oddsエンドポイントが正常にオッズを返すこと."""
    pass

def test_get_bet_odds_パラメータ不足():
    """必須パラメータが欠けている場合400を返すこと."""
    pass
```

**Step 2: ハンドラー実装**

`backend/src/api/handlers/races.py` に追加:

```python
def get_bet_odds(event: dict, context: Any) -> dict:
    """買い目のオッズを取得する.

    GET /races/{race_id}/bet-odds?bet_type={type}&horses={csv}
    """
    race_id_str = get_path_parameter(event, "race_id")
    if not race_id_str:
        return bad_request_response("race_id is required", event=event)

    bet_type = get_query_parameter(event, "bet_type")
    horses_str = get_query_parameter(event, "horses")
    if not bet_type or not horses_str:
        return bad_request_response("bet_type and horses are required", event=event)

    horse_numbers = [int(h.strip()) for h in horses_str.split(",")]

    provider = Dependencies.get_race_data_provider()
    result = provider.get_bet_odds(RaceId(race_id_str), bet_type, horse_numbers)

    if result is None:
        return not_found_response("オッズデータが見つかりません", event=event)

    return success_response({
        "bet_type": result.bet_type,
        "horse_numbers": result.horse_numbers,
        "odds": result.odds,
        "odds_min": result.odds_min,
        "odds_max": result.odds_max,
    })
```

**Step 3: ルーティング追加**

`router.py` の既存レースルートに追加:
```python
("GET", "/races/{race_id}/bet-odds", races.get_bet_odds),
```

**Step 4: テスト実行確認**

Run: `cd backend && uv run pytest tests/ -k "bet_odds" -v`

**Step 5: コミット**
```bash
git commit -m "feat: bet-odds APIハンドラー追加 (GET /races/{id}/bet-odds)"
```

---

## Task 8: フロントエンド — CartItem 型にオッズフィールド追加

**Files:**
- Modify: `frontend/src/types/index.ts:312-324`

**Step 1: CartItem インターフェースにオッズフィールド追加**

```typescript
export interface CartItem {
  id: string;
  raceId: string;
  raceName: string;
  raceVenue: string;
  raceNumber: string;
  betType: BetType;
  betMethod?: BetMethod;
  horseNumbers: number[];
  betDisplay?: string;
  betCount?: number;
  amount: number;
  odds?: number;        // 単一オッズ値（単勝、馬連、馬単、三連複、三連単）
  oddsMin?: number;     // 幅のあるオッズ下限（複勝、ワイド）
  oddsMax?: number;     // 幅のあるオッズ上限（複勝、ワイド）
}
```

**Step 2: コミット**
```bash
git commit -m "feat: CartItem型にオッズフィールド追加"
```

---

## Task 9: フロントエンド — API クライアントに getBetOdds 追加

**Files:**
- Modify: `frontend/src/api/client.ts`

**Step 1: BetOddsResponse 型定義**

`types/index.ts` に追加:
```typescript
export interface BetOddsResponse {
  bet_type: string;
  horse_numbers: number[];
  odds: number | null;
  odds_min: number | null;
  odds_max: number | null;
}
```

**Step 2: ApiClient に getBetOdds メソッド追加**

```typescript
async getBetOdds(
  raceId: string,
  betType: string,
  horseNumbers: number[],
): Promise<ApiResponse<BetOddsResponse>> {
  const params = new URLSearchParams({
    bet_type: betType,
    horses: horseNumbers.join(','),
  });
  return this.request<BetOddsResponse>(
    `/races/${encodeURIComponent(raceId)}/bet-odds?${params}`
  );
}
```

**Step 3: コミット**
```bash
git commit -m "feat: APIクライアントにgetBetOdds追加"
```

---

## Task 10: フロントエンド — CartPage に金額編集UI追加

**Files:**
- Modify: `frontend/src/pages/CartPage.tsx`

**Step 1: CartPage のインポート更新**

```typescript
import { useState } from 'react';
```
(既存の `useEffect` インポートに `useState` を追加)

**Step 2: 金額表示部分を編集可能に変更**

現在の表示のみの行 (L79-81):
```tsx
<div className="cart-item-amount">
  ¥{item.amount.toLocaleString()}
</div>
```

これを直接入力フィールドに変更。`updateItemAmount` を使って更新:

```tsx
const { items, removeItem, clearCart, getTotalAmount, updateItemAmount } = useCartStore();

// 各アイテムの金額入力状態管理
// CartItemAmountInput コンポーネントを作成して状態をカプセル化

function CartItemAmountInput({ item }: { item: CartItem }) {
  const [inputValue, setInputValue] = useState(String(item.amount));
  const updateItemAmount = useCartStore((s) => s.updateItemAmount);

  const handleBlur = () => {
    const parsed = parseInt(inputValue, 10);
    if (isNaN(parsed) || parsed < 100) {
      setInputValue(String(item.amount)); // リセット
      return;
    }
    const rounded = Math.round(parsed / 100) * 100;
    const clamped = Math.min(100000, Math.max(100, rounded));
    updateItemAmount(item.id, clamped);
    setInputValue(String(clamped));
  };

  return (
    <div className="cart-item-amount">
      <span className="currency-symbol">¥</span>
      <input
        type="number"
        className="cart-amount-input"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onBlur={handleBlur}
        min={100}
        max={100000}
        step={100}
      />
    </div>
  );
}
```

**Step 3: CSS追加**

`frontend/src/App.css` に:
```css
.cart-amount-input {
  width: 80px;
  text-align: right;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 14px;
  font-weight: 600;
}
.cart-amount-input:focus {
  border-color: #1a73e8;
  outline: none;
}
```

**Step 4: 動作確認**

`cd frontend && npm run dev` で確認:
- 金額フィールドをタップして数値を変更できること
- フォーカスを外すと100円単位に丸められること
- 合計金額がリアルタイム更新されること

**Step 5: コミット**
```bash
git commit -m "feat: カートで購入金額を直接編集可能に"
```

---

## Task 11: フロントエンド — CartPage にオッズ表示追加

**Files:**
- Modify: `frontend/src/pages/CartPage.tsx`

**Step 1: オッズ表示ヘルパー関数追加**

```typescript
function formatOdds(item: CartItem): string | null {
  if (item.oddsMin != null && item.oddsMax != null) {
    return `${item.oddsMin.toFixed(1)}〜${item.oddsMax.toFixed(1)}倍`;
  }
  if (item.odds != null) {
    return `${item.odds.toFixed(1)}倍`;
  }
  return null;
}
```

**Step 2: CartItem 表示にオッズ行を追加**

買い目情報の後にオッズ表示を追加:
```tsx
{/* 既存: 買い目情報 */}
<div className="cart-item-bet">
  ...
</div>
{/* NEW: オッズ表示 */}
{formatOdds(item) && (
  <div className="cart-item-odds">
    {formatOdds(item)}
  </div>
)}
```

**Step 3: CSS追加**

```css
.cart-item-odds {
  font-size: 13px;
  color: #e65100;
  font-weight: 600;
  margin-top: 2px;
}
```

**Step 4: 動作確認**

オッズが設定されたCartItemが正しく表示されることを確認。
(この時点ではオッズは未取得なので表示されないが、次のTaskで取得ロジックを追加)

**Step 5: コミット**
```bash
git commit -m "feat: カートにオッズ表示を追加"
```

---

## Task 12: フロントエンド — カート追加時にオッズを取得

**Files:**
- Modify: `frontend/src/pages/RaceDetailPage.tsx`

**Step 1: オッズ取得ロジック追加**

`handleAddToCart` 関数内で、addItem 呼び出し前にオッズを取得:

```typescript
import { apiClient } from '../api/client';
import { BetTypeToApiName } from '../types'; // bet_type マッピング

// カート追加時にオッズを取得
let odds: number | undefined;
let oddsMin: number | undefined;
let oddsMax: number | undefined;

const betTypeApiName = mapBetTypeToApiName(betType); // win, place, quinella, etc.
const oddsResult = await apiClient.getBetOdds(race.id, betTypeApiName, horseNumbersDisplay);
if (oddsResult.success && oddsResult.data) {
  odds = oddsResult.data.odds ?? undefined;
  oddsMin = oddsResult.data.odds_min ?? undefined;
  oddsMax = oddsResult.data.odds_max ?? undefined;
}

const result = addItem({
  raceId: race.id,
  // ... 既存フィールド ...
  odds,
  oddsMin,
  oddsMax,
  runnersData: race.horses.map((h) => ({ ... })),
});
```

**Step 2: BetType → API名のマッピング追加**

`types/index.ts` に追加:
```typescript
export const BetTypeToApiName: Record<BetType, string> = {
  win: 'win',
  place: 'place',
  quinella: 'quinella',
  quinella_place: 'wide',
  exacta: 'exacta',
  trio: 'trio',
  trifecta: 'trifecta',
};
```

**Step 3: handleAddToCart を async に変更**

注意: 既存の `handleAddToCart` は同期関数。async に変更してオッズ取得を非同期で行う。オッズ取得に失敗してもカート追加自体はブロックしない。

**Step 4: 動作確認**

`cd frontend && npm run dev` で確認:
- レース詳細でカートに追加するとオッズが取得されること
- カート画面でオッズが表示されること
- オッズ取得失敗時もカート追加は成功すること

**Step 5: コミット**
```bash
git commit -m "feat: カート追加時にJRA実オッズを取得して保存"
```

---

## Task 13: AI提案からのカート追加時にもオッズを取得

**Files:**
- Modify: `frontend/src/components/proposal/BetProposalContent.tsx`

**背景:**
AI提案の「カートに追加」ボタンからもカートに追加するフローがある。
ここでもオッズ取得が必要。

**Step 1: 既存の addToCart ロジックを確認**

`BetProposalContent.tsx` 内のカート追加処理を確認し、
Task 12 と同様にオッズ取得ロジックを追加する。

**Step 2: 実装**

**Step 3: 動作確認**

**Step 4: コミット**
```bash
git commit -m "feat: AI提案カート追加時にもオッズ取得"
```

---

## Task 14: 全体の結合テスト・動作確認

**Step 1: バックエンドテスト全体実行**

```bash
cd backend && uv run pytest
```

全テストがパスすることを確認。

**Step 2: フロントエンドビルド確認**

```bash
cd frontend && npm run build
```

ビルドエラーがないことを確認。

**Step 3: ローカルで E2E 確認**

1. JRA-VAN API にbet-oddsエンドポイントが応答すること
2. Lambda API がプロキシとして動作すること
3. カート画面で金額が編集できること
4. カート画面でオッズが表示されること

**Step 4: コミット (もし修正があれば)**

```bash
git commit -m "fix: 結合テストで発見された問題を修正"
```

---

## 実装順序と依存関係

```
Task 1〜3 (JRA-VAN DB関数) → Task 4 (JRA-VAN エンドポイント) → Task 6 (Provider実装) → Task 7 (Lambda ハンドラー)
                                                                                            ↓
Task 5 (ドメインモデル) ──────────────────────────────────────────────────────────────────→ Task 7
                                                                                            ↓
Task 8 (CartItem型) → Task 9 (APIクライアント) → Task 12 (オッズ取得) → Task 13 (AI提案) → Task 14
                         ↓
Task 10 (金額編集UI) → Task 11 (オッズ表示) ──────────────────────────────────────────────→ Task 14
```

**並列実行可能なグループ:**
- Group A (JRA-VAN API): Task 1, 2, 3 → 4
- Group B (バックエンド): Task 5, 6, 7 (Task 4 完了後)
- Group C (フロントエンド型+API): Task 8, 9 (Task 7 完了後)
- Group D (フロントエンドUI): Task 10, 11 (Task 8 と並行可能)
- Group E (統合): Task 12, 13, 14 (Group B, C, D 完了後)
