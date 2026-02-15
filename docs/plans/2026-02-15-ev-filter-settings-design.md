# 確率/EVフィルター設定 設計ドキュメント

## 背景

EV proposer は `確率 × オッズ = EV` で全組合せをスコアリングし、EV降順でソートして提案する。
現状は `EV_THRESHOLD = 1.0`、`MIN_PROB_FOR_COMBINATION = 0.02` がハードコードされており、
高オッズ × 低確率 = 高EV の大穴馬券ばかりが上位に来る偏りがある。

ユーザーが確率とEVの範囲をスライダーで設定できるようにし、本命〜大穴のバランスを制御可能にする。

## データモデル

### BettingPreference 値オブジェクト（拡張）

```python
@dataclass(frozen=True)
class BettingPreference:
    bet_type_preference: BetTypePreference
    min_probability: float = 0.01   # 1%
    max_probability: float = 0.50   # 50%
    min_ev: float = 1.0
    max_ev: float = 10.0
```

デフォルト値はフィルターなし相当（広い範囲）。

### DynamoDB 保存形式

```json
{
  "bet_type_preference": "auto",
  "min_probability": 0.01,
  "max_probability": 0.50,
  "min_ev": 1.0,
  "max_ev": 10.0
}
```

既存データには新フィールドがないため、`from_dict()` で `data.get()` のデフォルト値で吸収。マイグレーション不要。

## バリデーション

| フィールド | 型 | 範囲 | 制約 |
|-----------|-----|------|------|
| min_probability | float | 0.01 - 0.50 | min <= max |
| max_probability | float | 0.01 - 0.50 | min <= max |
| min_ev | float | 1.0 - 10.0 | min <= max |
| max_ev | float | 1.0 - 10.0 | min <= max |

API ハンドラで範囲チェックと min <= max 制約を検証。

## EV Proposer 変更

`_generate_ev_candidates()` のフィルタリング条件を変更:

**Before:**
```python
if ev >= EV_THRESHOLD and prob >= MIN_PROB_FOR_COMBINATION:
```

**After:**
```python
if min_ev <= ev <= max_ev and min_prob <= prob <= max_prob:
```

フィルター値は `_current_betting_preference` dict から取得。未設定時はデフォルト値を使用。

## フロントエンド UI

エージェント設定ページ（`/agent`）の好み設定セクションに、券種の好みの下にスライダーを追加:

### 確率スライダー
- デュアルレンジスライダー（min/max）
- 範囲: 1% 〜 50%
- ステップ: 1%
- 表示: 「1% ～ 50%」

### EVスライダー
- デュアルレンジスライダー（min/max）
- 範囲: 1.0 〜 10.0
- ステップ: 0.5
- 表示: 「1.0 ～ 10.0」

スライダーは `<input type="range">` × 2 のカスタムコンポーネントで実装。

## データフロー

```
Frontend (slider操作)
  → API PUT /agents/me { betting_preference: { min_probability: 0.05, ... } }
  → DynamoDB Agent レコード更新
  → AgentCore invoke() → agent.py で set_betting_preference() 呼び出し
  → ev_proposer._current_betting_preference にフィルター値セット
  → _generate_ev_candidates() でフィルター適用
```
