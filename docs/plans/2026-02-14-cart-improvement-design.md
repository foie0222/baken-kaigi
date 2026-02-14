# カート画面改善設計

## 概要

カート選択画面に2つの改善を実施する:

1. **購入金額の変更機能**: カート内で金額を直接編集可能にする
2. **JRA実オッズの表示**: 全7券種の実オッズをカートに表示する

## 1. JRA-VAN API: 券種別オッズ取得

### 対応テーブル

| テーブル | 券種 | 関数 | オッズ形式 |
|---------|------|------|-----------|
| jvd_o1 | 単勝 (win) | `get_win_odds()` (既存) | 単一値 |
| jvd_o1 | 複勝 (place) | `get_place_odds()` (既存) | 幅 (min〜max) |
| jvd_o2 | 馬連 (quinella) | `get_quinella_odds()` (新規) | 単一値 |
| jvd_o3 | ワイド (wide) | `get_wide_odds()` (新規) | 幅 (min〜max) |
| jvd_o4 | 馬単 (exacta) | `get_exacta_odds()` (新規) | 単一値 |
| jvd_o5 | 三連複 (trio) | `get_trio_odds()` (新規) | 単一値 |
| jvd_o6 | 三連単 (trifecta) | `get_trifecta_odds()` (新規) | 単一値 |

### 新規APIエンドポイント (`jravan-api/main.py`)

```
GET /races/{race_id}/bet-odds?bet_type={type}&horses={comma_separated}
```

レスポンス例:

```json
// 単勝: ?bet_type=win&horses=3
{ "odds": 5.2 }

// 複勝: ?bet_type=place&horses=3
{ "odds_min": 2.4, "odds_max": 3.3 }

// 馬連: ?bet_type=quinella&horses=3,7
{ "odds": 15.3 }

// ワイド: ?bet_type=wide&horses=3,7
{ "odds_min": 3.2, "odds_max": 5.8 }

// 馬単: ?bet_type=exacta&horses=3,7 (着順: 1着=3, 2着=7)
{ "odds": 28.5 }

// 三連複: ?bet_type=trio&horses=3,5,7
{ "odds": 45.2 }

// 三連単: ?bet_type=trifecta&horses=3,5,7 (着順: 1着=3, 2着=5, 3着=7)
{ "odds": 215.8 }
```

### データベース関数 (`jravan-api/database.py`)

新規追加:
- `get_quinella_odds(race_id, horse_a, horse_b)` → jvd_o2
- `get_wide_odds(race_id, horse_a, horse_b)` → jvd_o3 (min/max)
- `get_exacta_odds(race_id, first, second)` → jvd_o4
- `get_trio_odds(race_id, horse_a, horse_b, horse_c)` → jvd_o5
- `get_trifecta_odds(race_id, first, second, third)` → jvd_o6

## 2. バックエンドAPI (Lambda)

### 新規エンドポイント (`backend/src/api/handlers/races.py`)

```
GET /races/{race_id}/bet-odds?bet_type={type}&horses={csv}
```

JRA-VAN APIへのプロキシ。フロントエンドからのリクエストを中継する。

### ドメインモデル (`race_data_provider.py`)

```python
@dataclass(frozen=True)
class BetOddsData:
    bet_type: str               # win, place, quinella, wide, exacta, trio, trifecta
    horse_numbers: list[int]
    odds: float | None          # 単一値の場合
    odds_min: float | None      # 幅の場合（ワイド・複勝）
    odds_max: float | None      # 幅の場合（ワイド・複勝）
```

### データフロー

```
Frontend → Lambda API → JRA-VAN API (EC2) → PC-KEIBA DB (jvd_o1〜o6)
Frontend ← Lambda API ← JRA-VAN API ← レスポンス
```

## 3. フロントエンド

### CartItem型の拡張 (`types/index.ts`)

```typescript
interface CartItem {
  // ...既存フィールド...
  odds?: number;        // 単一オッズ値（単勝、馬連、馬単、三連複、三連単）
  oddsMin?: number;     // 幅のあるオッズ下限（複勝、ワイド）
  oddsMax?: number;     // 幅のあるオッズ上限（複勝、ワイド）
}
```

### CartPage UI変更

```
各CartItem:
  ├── レース情報 (会場+R+レース名)
  ├── 買い目情報 (券種+馬番表示+点数)
  ├── オッズ表示 (NEW!)
  │   ├── 単一値: "15.3倍"
  │   └── 幅あり: "3.2〜5.8倍"
  ├── 金額入力 (CHANGED! 表示のみ→直接入力可能)
  │   └── 直接入力フィールド (100円単位、MIN: 100円、MAX: 100,000円)
  └── 削除ボタン (×)
```

### 金額変更の動作

- 金額フィールドをタップすると入力モードに切り替え
- `cartStore.updateItemAmount(id, newAmount)` を呼び出し（既存関数を活用）
- 100円単位に丸め、バリデーション適用（100〜100,000円）
- 合計金額がリアルタイム更新

### オッズ取得タイミング

- カート追加時: レース詳細ページでカートに入れる際にbet-odds APIを呼び出し、オッズをCartItemに保存
- カート表示時: 保存されたオッズを表示（リアルタイム更新はしない）

## 対象ファイル

### JRA-VAN API
- `jravan-api/database.py` - 新規クエリ関数追加
- `jravan-api/main.py` - 新規エンドポイント追加

### バックエンド
- `backend/src/api/handlers/races.py` - プロキシエンドポイント追加
- `backend/src/domain/ports/race_data_provider.py` - BetOddsData型追加
- `backend/src/infrastructure/providers/jravan_race_data_provider.py` - 実装

### フロントエンド
- `frontend/src/types/index.ts` - CartItem型拡張
- `frontend/src/stores/cartStore.ts` - オッズ保存対応
- `frontend/src/pages/CartPage.tsx` - UI変更（オッズ表示+金額編集）
- `frontend/src/pages/RaceDetailPage.tsx` - カート追加時にオッズ取得
- `frontend/src/api/client.ts` - bet-odds API呼び出し関数追加
