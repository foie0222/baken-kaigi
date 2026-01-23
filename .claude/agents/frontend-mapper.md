---
name: frontend-mapper
description: バックエンドAPIレスポンスからTypeScript型とマッピング関数を自動生成
version: 1.0.0
type: agent
tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# フロントエンドマッピング生成サブエージェント

## 概要

バックエンドAPIのレスポンス定義から、フロントエンド用のTypeScript型定義とマッピング関数を自動生成します。型安全性を保証し、API変更時のフロントエンド更新作業を効率化します。

## 実行タイミング

以下の状況で本エージェントを起動してください:

- 新しいAPIエンドポイントを追加した時
- 既存APIレスポンスにフィールドを追加/変更した時
- データ構造の大幅な変更がある時

## マッピング戦略

### 命名規則

**バックエンド（Python）**:
- snake_case（例: `race_id`, `horse_count`）
- データクラス: PascalCase（例: `RaceData`, `RunnerData`）

**フロントエンド（TypeScript）**:
- API型: `Api` プレフィックス + snake_case（例: `ApiRace`, `ApiRunner`）
- 表示用型: PascalCase + camelCase フィールド（例: `Race`, `Runner`）

### 型マッピングルール

| Python型 | TypeScript API型 | TypeScript表示用型 |
|---------|-----------------|------------------|
| `str` | `string` | `string` |
| `int` | `number` | `number` |
| `float` | `number` | `number` |
| `bool` | `boolean` | `boolean` |
| `datetime` | `string` (ISO形式) | `string` (表示形式) |
| `list[T]` | `T[]` | `T[]` |
| `dict[K, V]` | `Record<K, V>` | `Record<K, V>` |
| `T \| None` | `T \| undefined` | `T?` (optional) |

## 実行プロセス

### ステップ1: バックエンドAPIの分析

#### 対象ファイル
- `main/backend/src/api/handlers/*.py`
- `main/backend/src/domain/ports/*.py`

#### 抽出情報
1. エンドポイントパス
2. レスポンス構造
3. フィールド名と型
4. オプショナルフィールド

**分析例（races.py）**:
```python
def get_race_detail(event: dict, context: Any) -> dict:
    # ...
    return success_response({
        "race": {
            "race_id": str,
            "race_name": str,
            "race_number": int,
            "venue": str,
            "start_time": str,  # ISO format
            "track_condition": str,
            "distance": int | None,
        },
        "runners": list[{
            "horse_number": int,
            "horse_name": str,
            "jockey_name": str,
            "odds": str,
            "weight": int | None,
        }]
    })
```

### ステップ2: TypeScript API型の生成

**ファイル**: `main/frontend/src/types/index.ts`

**生成パターン**:
```typescript
// バックエンドレスポンス型（API型）
export interface ApiRace {
  race_id: string;
  race_name: string;
  race_number: number;
  venue: string;
  start_time: string;  // ISO 8601形式
  track_condition: string;
  distance?: number;   // オプショナル
}

export interface ApiRunner {
  horse_number: number;
  horse_name: string;
  jockey_name: string;
  odds: string;
  weight?: number;
}

export interface ApiRaceDetailResponse {
  race: ApiRace;
  runners: ApiRunner[];
}
```

**重要な原則**:
- フィールド名はバックエンドと完全一致（snake_case）
- オプショナルフィールドは `?` で表現
- ネストした型も個別に定義

### ステップ3: フロントエンド表示用型の生成

**生成パターン**:
```typescript
// フロントエンド表示用型（camelCase）
export interface Race {
  id: string;
  name: string;
  number: string;      // 表示用に "1R" 形式
  venue: string;
  time: string;        // "15:40" 形式
  condition: string;
  distance?: number;
}

export interface Runner {
  number: number;
  name: string;
  jockey: string;
  odds: number;        // 文字列を数値に変換
  weight?: number;
}

export interface RaceDetail {
  race: Race;
  runners: Runner[];
}
```

**変換ルール**:
1. **レース番号**: `race_number: number` → `number: string` ("1R")
2. **時刻**: `start_time: string` → `time: string` ("15:40")
3. **オッズ**: `odds: string` → `odds: number` (parseFloat)

### ステップ4: マッピング関数の生成

**生成パターン**:
```typescript
export function mapApiRaceToRace(apiRace: ApiRace): Race {
  const startTime = new Date(apiRace.start_time);
  const hours = startTime.getHours().toString().padStart(2, '0');
  const minutes = startTime.getMinutes().toString().padStart(2, '0');

  return {
    id: apiRace.race_id,
    name: apiRace.race_name,
    number: `${apiRace.race_number}R`,
    venue: apiRace.venue,
    time: `${hours}:${minutes}`,
    condition: apiRace.track_condition,
    distance: apiRace.distance,
  };
}

export function mapApiRunnerToRunner(apiRunner: ApiRunner): Runner {
  return {
    number: apiRunner.horse_number,
    name: apiRunner.horse_name,
    jockey: apiRunner.jockey_name,
    odds: parseFloat(apiRunner.odds),
    weight: apiRunner.weight,
  };
}

export function mapApiRaceDetailToRaceDetail(
  apiRace: ApiRace,
  runners: ApiRunner[]
): RaceDetail {
  return {
    race: mapApiRaceToRace(apiRace),
    runners: runners.map(mapApiRunnerToRunner),
  };
}
```

**重要な原則**:
- 関数名: `mapApi<Type>To<Type>`
- 純粋関数（副作用なし）
- null/undefined ハンドリング

### ステップ5: APIクライアントの更新

**ファイル**: `main/frontend/src/api/client.ts`

**生成パターン**:
```typescript
async getRaceDetail(raceId: string): Promise<ApiResponse<RaceDetail>> {
  const response = await this.request<ApiRaceDetailResponse>(
    `/races/${encodeURIComponent(raceId)}`
  );

  if (!response.success || !response.data) {
    return { success: false, error: response.error };
  }

  return {
    success: true,
    data: mapApiRaceDetailToRaceDetail(
      response.data.race,
      response.data.runners
    ),
  };
}
```

**重要な原則**:
- URLパラメータは `encodeURIComponent()` でエンコード
- エラーハンドリングを統一
- マッピング関数を使用して変換

### ステップ6: 型チェックと検証

**コマンド**:
```bash
cd main/frontend
npm run typecheck
```

**検証項目**:
- [ ] API型とバックエンドレスポンスの一致
- [ ] マッピング関数の型安全性
- [ ] オプショナルフィールドの適切な扱い
- [ ] 型エラーがないこと

## 出力形式

### マッピング生成開始時

```
🔄 フロントエンドマッピング生成開始

対象API: GET /races/{race_id}

バックエンドレスポンス:
- race: ApiRace
  - race_id: string
  - race_name: string
  - race_number: number
  - start_time: string (datetime)
  - distance?: number
- runners: ApiRunner[]
  - horse_number: number
  - horse_name: string
  - weight?: number
```

### 型生成完了時

```
✅ TypeScript型定義生成完了

追加した型:
- ApiRace (API型)
- ApiRunner (API型)
- ApiRaceDetailResponse (API型)
- Race (表示用型)
- Runner (表示用型)
- RaceDetail (表示用型)

マッピング関数:
- mapApiRaceToRace()
- mapApiRunnerToRunner()
- mapApiRaceDetailToRaceDetail()

更新ファイル:
- frontend/src/types/index.ts
- frontend/src/api/client.ts
```

### 型チェック結果

```
🔍 型チェック実行中...

✅ 型エラーなし

次のアクション:
- [ ] npm run build で動作確認
- [ ] UIコンポーネントでの利用
```

## エラーハンドリング

### よくあるエラー

1. **型不整合**
   ```
   Type 'string' is not assignable to type 'number'
   ```
   - 対処: バックエンドとフロントエンドの型定義を再確認

2. **オプショナル型エラー**
   ```
   Property 'distance' may be undefined
   ```
   - 対処: オプショナルチェイニング `?.` を使用

3. **Date変換エラー**
   ```
   Invalid Date
   ```
   - 対処: ISO形式の文字列か確認、`new Date()` の前にバリデーション

## 使用例

### 例1: 新しいフィールド追加（馬体重）

```
入力:
バックエンドに weight, weight_diff フィールドを追加

出力:

// API型に追加
export interface ApiRunner {
  // ... 既存フィールド
  weight?: number;       // 追加
  weight_diff?: number;  // 追加
}

// 表示用型に追加
export interface Runner {
  // ... 既存フィールド
  weight?: number;
  weightDiff?: number;   // camelCase変換
}

// マッピング関数更新
export function mapApiRunnerToRunner(apiRunner: ApiRunner): Runner {
  return {
    // ... 既存マッピング
    weight: apiRunner.weight,
    weightDiff: apiRunner.weight_diff,
  };
}
```

### 例2: ネストした型のマッピング

```
バックエンドレスポンス:
{
  "race": { ... },
  "runners": [
    {
      "horse_number": 1,
      "pedigree": {
        "sire_name": "ディープインパクト",
        "dam_name": "ウインドインハーヘア"
      }
    }
  ]
}

生成される型:

export interface ApiPedigree {
  sire_name: string;
  dam_name: string;
}

export interface ApiRunner {
  horse_number: number;
  pedigree?: ApiPedigree;
}

export interface Pedigree {
  sireName: string;
  damName: string;
}

export interface Runner {
  number: number;
  pedigree?: Pedigree;
}

function mapApiPedigreeTopedigree(api: ApiPedigree): Pedigree {
  return {
    sireName: api.sire_name,
    damName: api.dam_name,
  };
}
```

## 参照ファイル

- **バックエンドHandler**: `main/backend/src/api/handlers/races.py`
- **型定義**: `main/frontend/src/types/index.ts`
- **APIクライアント**: `main/frontend/src/api/client.ts`

## 注意事項

- **API型は変更しない**: バックエンドと完全一致を保つ
- **マッピング関数でのみ変換**: 表示用型への変換はマッピング関数で
- **型安全性**: `npm run typecheck` で必ず確認
- **命名規則**: camelCase変換ルールを統一
