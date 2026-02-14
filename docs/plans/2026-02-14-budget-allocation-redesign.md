# 資金配分ロジック再設計

## 背景

現状の `bet_proposal.py` は `budget`（1レースの予算）を受け取り、`MAX_BETS=8` で買い目を強制カットした後、信頼度別（high/medium/low）に予算配分する。この設計には以下の問題がある。

- 買い目が常に8点前後に固定される（MAX_BETS=8 + MAX_PARTNERS=4 の設計一致）
- 1レースの掛け金を動的に決めるロジックがない
- レースの自信度に応じたメリハリがない

## 設計方針

世の中の知見（ケリー基準、定率法、ダッチング、プロの資金管理）を踏まえ、以下を採用する。

- **レース間配分**: 定率法 + 見送りスコアによる信頼度傾斜
- **レース内配分**: ダッチング（均等払い戻し）
- **買い目選定**: 期待値 > 1.0 の全買い目を採用（MAX_BETS 撤廃）

## 全体フロー

```
bankroll（1日の総資金）
  │
  ├── [第1段階] レース間配分
  │     race_budget = bankroll × base_rate × confidence_factor
  │
  └── [第2段階] レース内配分（ダッチング）
        各買い目の金額 = race_budget × (1/オッズi) ÷ Σ(1/オッズj)
        → どの買い目が的中しても同額の払い戻し
```

## 第1段階: レース間配分

### 入力の変更

| 項目 | 現状 | 新設計 |
|------|------|--------|
| ツール引数 | `budget: int`（1レース予算） | `bankroll: int`（1日の総資金） |
| 後方互換 | - | `budget` 引数も残す。指定時はそのまま使用 |

### 計算式

```
race_budget = bankroll × base_rate × confidence_factor
```

- `bankroll`: 1日の総資金（ユーザー入力）
- `base_rate`: 基本投入率。デフォルト 0.03（3%）。ペルソナで変動
- `confidence_factor`: 見送りスコアから算出。0.0〜2.0

### confidence_factor の算出

見送りスコア(0〜10)から線形マッピング:

```python
def _calculate_confidence_factor(skip_score: int) -> float:
    """見送りスコアから信頼度係数を算出する."""
    if skip_score >= 9:
        return 0.0  # 見送り
    # skip_score 0 → 2.0, skip_score 8 → 0.25
    return max(0.0, 2.0 - skip_score * (1.75 / 8))
```

| 見送りスコア | confidence_factor | 解釈 |
|------------|-------------------|------|
| 0 | 2.00 | 最高自信。base_rateの2倍 |
| 2 | 1.56 | 高自信 |
| 4 | 1.13 | やや自信あり |
| 5 | 0.91 | 標準 |
| 6 | 0.69 | やや不安 |
| 8 | 0.25 | 低自信。最低限 |
| 9-10 | 0.00 | 見送り（配分ゼロ） |

### ペルソナ別 base_rate

| ペルソナ | base_rate | 備考 |
|---------|-----------|------|
| analyst | 0.03 (3%) | 標準。バランス型 |
| conservative | 0.02 (2%) | 保守的。1レースのリスクを抑える |
| intuition | 0.03 (3%) | 標準 |
| aggressive | 0.05 (5%) | 積極的。プロ推奨上限 |

### 安全上限

```python
MAX_RACE_BUDGET_RATIO = 0.10  # bankrollの10%を絶対に超えない
race_budget = min(race_budget, bankroll * MAX_RACE_BUDGET_RATIO)
```

## 第2段階: レース内配分（ダッチング）

### 買い目選定の変更

| 項目 | 現状 | 新設計 |
|------|------|--------|
| 上限 | `MAX_BETS=8` で強制カット | なし。予算内で自然に決定 |
| 足切り | トリガミ閾値（合成オッズ2.0倍未満除外） | 期待値 > 1.0 の買い目のみ採用 |

### ダッチング配分の計算

```python
def _allocate_budget_dutching(bets: list[dict], budget: int) -> list[dict]:
    """ダッチング方式で予算を配分する.

    どの買い目が的中しても同額の払い戻しになるように、
    オッズの逆数に比例して配分する。
    """
    if not bets or budget <= 0:
        return bets

    # 期待値 > 1.0 の買い目のみ
    eligible = [b for b in bets if b.get("expected_value", 0) > 1.0]
    if not eligible:
        return []

    # オッズ逆数の合計 = 合成オッズの逆数
    inv_odds_sum = sum(1.0 / b["estimated_odds"] for b in eligible)
    composite_odds = 1.0 / inv_odds_sum

    # 各買い目の金額 = 予算 × 合成オッズ ÷ オッズi
    for bet in eligible:
        raw = budget * composite_odds / bet["estimated_odds"]
        bet["amount"] = max(MIN_BET_AMOUNT, math.floor(raw / MIN_BET_AMOUNT) * MIN_BET_AMOUNT)

    # 最低賭け金(100円)未満の買い目を除外して再計算
    funded = [b for b in eligible if b.get("amount", 0) >= MIN_BET_AMOUNT]
    if len(funded) < len(eligible):
        return _allocate_budget_dutching(funded, budget)

    # 余剰調整（丸め誤差分を配分が最も多い買い目に追加）
    total = sum(b["amount"] for b in funded)
    remaining = budget - total
    if remaining >= MIN_BET_AMOUNT and funded:
        funded[0]["amount"] += math.floor(remaining / MIN_BET_AMOUNT) * MIN_BET_AMOUNT

    # 合成オッズを結果に付与
    for bet in funded:
        bet["composite_odds"] = round(composite_odds, 2)

    return funded
```

### 合成オッズの表示

結果に `composite_odds` を含め、ユーザーにレース全体の収益性を示す。

## 削除・変更する定数・関数

### 削除

| 対象 | 理由 |
|------|------|
| `MAX_BETS = 8` | 点数制限を撤廃 |
| `ALLOCATION_HIGH / MEDIUM / LOW` | 信頼度別配分を廃止（ダッチングに置換） |
| `SKIP_BUDGET_REDUCTION = 0.5` | confidence_factorに統合 |
| `_assign_relative_confidence()` | 信頼度分類が不要に |
| `_allocate_budget()` | `_allocate_budget_dutching()` に置換 |

### 変更

| 対象 | 変更内容 |
|------|---------|
| `_generate_bet_candidates()` | `max_bets` パラメータ削除。`bets[:max_bets]` のスライスを除去 |
| `_generate_bet_proposal_impl()` | `budget` → `bankroll` 対応。confidence_factor算出を追加 |
| `generate_bet_proposal()` | `bankroll` 引数追加。`budget` は後方互換で残す |
| ペルソナ設定 | `max_bets` → `base_rate` に変更。allocation系を削除 |

## 後方互換

- `budget` 引数が指定された場合はそのまま1レース予算として使用（従来動作）
- `bankroll` 引数が指定された場合は新ロジックで race_budget を算出
- 両方指定された場合は `bankroll` を優先

## 出力の変更

```python
# 現状
{
    "total_amount": 8000,
    "budget_remaining": 2000,
}

# 新設計
{
    "total_amount": 1620,
    "race_budget": 1620,           # このレースの予算
    "composite_odds": 3.45,        # 合成オッズ
    "confidence_factor": 1.8,      # 信頼度係数
    "bankroll_usage_pct": 5.4,     # bankroll使用率(%)
}
```

## 具体例

### 例1: 自信のあるレース

```
bankroll = 30,000円、base_rate = 3%
見送りスコア = 2 → confidence_factor = 1.56
race_budget = 30,000 × 0.03 × 1.56 = 1,404円

EV>1.0 の買い目:
  馬連 1-3  オッズ8.0  EV=1.25 → 金額: 500円
  馬連 2-3  オッズ6.0  EV=1.10 → 金額: 500円
  馬連 1-5  オッズ12.0 EV=1.15 → 金額: 200円
  三連複 1-2-3 オッズ25.0 EV=1.30 → 金額: 100円

→ 4点買い、合計1,300円、合成オッズ ≒ 2.26倍
  どの買い目が的中しても約2,940円の払い戻し
```

### 例2: 不安なレース

```
bankroll = 30,000円、base_rate = 3%
見送りスコア = 7 → confidence_factor = 0.47
race_budget = 30,000 × 0.03 × 0.47 = 423円

EV>1.0 の買い目が2点 → ダッチングで2点に配分
→ 2点買い、合計400円
```

### 例3: 見送りレース

```
見送りスコア = 9 → confidence_factor = 0.0
race_budget = 0円 → 見送り
```

## テスト方針

1. `_calculate_confidence_factor()` の境界値テスト
2. `_allocate_budget_dutching()` の配分が均等払い戻しになることの検証
3. 期待値足切り: EV <= 1.0 の買い目が除外されること
4. 最低賭け金(100円)未満の買い目が再帰的に除外されること
5. `bankroll` / `budget` の後方互換テスト
6. 安全上限(10%)を超えないこと
7. 合成オッズの計算精度
