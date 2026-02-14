# EV（期待値）ベース買い目提案 設計ドキュメント

## 背景

現在の買い目提案パイプラインは完全に決定論的で、LLMの自律的判断が入らない。
複合スコア（AI指数重み+オッズ乖離+ペース相性+スピード指数+近走フォーム）による順位付けで
軸馬・券種・組合せを決定しているが、これを**確率ベースの期待値計算**に置き換える。

### 現状の問題

1. LLMはツールルーティングとナレーション生成しかしておらず、買い目選定に関与しない
2. 複合スコアは「順位付け」であり「確率」ではない。期待値計算が本質的でない
3. 券種選定がレース難易度ベースの固定マッピングで、柔軟性がない
4. bet_proposalフローではLLMが分析結果を見ることすらない

## ゴール

```
確率算出 → 期待値計算（確率 × オッズ） → 期待値で買い目選定
```

LLMが分析データを見て各馬の勝率を判断し、その確率から期待値を計算して買い目を決める。

## アーキテクチャ: 2フェーズ分離方式

### 全体フロー

```
┌──────────────────────────────────────────────────────────────┐
│  LLM (Strands Agent)                                         │
│                                                              │
│  1. analyze_race_for_betting(race_id) を呼ぶ                 │
│     → ベース確率・オッズ・レース分析データを受け取る          │
│                                                              │
│  2. 分析結果を見て、各馬の勝率を判断・調整                   │
│     例: 逃げ馬多い→ハイペース→差し馬の確率UP                 │
│     例: スピード指数突出→その馬の確率UP                      │
│                                                              │
│  3. propose_bets(win_probabilities, budget/bankroll) を呼ぶ   │
│     → 確率×オッズでEV計算→買い目選定→予算配分               │
└──────────────────────────────────────────────────────────────┘
```

### Tool 1: `analyze_race_for_betting(race_id: str)`

**役割**: データ収集 + ベース確率算出。LLMの判断材料を提供する。

**処理内容**:
1. レースデータ取得（race_detail API）
2. AI予想取得（3ソース: jiro8, kichiuma, daily）
3. 脚質データ取得
4. スピード指数取得
5. 過去成績取得
6. ベース確率算出（重み付き統合）
7. ペース予想・レース難易度・見送りスコア算出

**返り値**:
```python
{
  "race_info": {
    "race_id": str,
    "race_name": str,
    "venue": str,
    "distance": str,
    "surface": str,
    "total_runners": int,
    "difficulty": int,           # 1-5
    "predicted_pace": str,       # "ハイ"/"ミドル"/"スロー"
    "skip_score": int,           # 0-10
    "ai_consensus": str,         # "明確な上位"/"概ね合意"/"やや接戦"/"混戦"
    "confidence_factor": float,  # 0.0-2.0 (見送りスコアから算出)
  },
  "horses": [
    {
      "number": int,
      "name": str,
      "odds": float,
      "base_win_probability": float,     # 重み付き統合確率
      "ai_scores": {                     # ソース別生スコア
        "jiro8": float | None,
        "kichiuma": float | None,
        "daily": float | None,
      },
      "running_style": str | None,       # "逃げ"/"先行"/"差し"/"追込"/"自在"
      "pace_compatibility": float,       # -1.0〜1.0
      "speed_index": {                   # なければ None
        "latest": float | None,
        "avg": float | None,
      } | None,
      "recent_form": list[int] | None,   # 直近5走の着順
    },
    ...
  ],
  "source_weights": {"jiro8": float, "kichiuma": float, "daily": float},
}
```

**ソース重み付けの改善**:
- 現在: 単純平均（`sum(ps) / len(ps)`）
- 改善: ソースごとの重みで加重平均
- 初期重み: `{"jiro8": 0.4, "kichiuma": 0.35, "daily": 0.25}`
- 定数として管理（将来的にはLLMや実績ベースで調整可能に）

### Tool 2: `propose_bets(race_id, win_probabilities, budget/bankroll, ...)`

**役割**: 確率→EV計算→買い目選定→予算配分。純粋な計算ツール。

**入力パラメータ**:
```python
race_id: str                                  # レースID
win_probabilities: dict[str, float]           # {"1": 0.25, "3": 0.18, ...} 馬番→勝率
budget: int = 0                               # 従来モード予算（円）
bankroll: int = 0                             # bankrollモード総資金（円）
preferred_bet_types: list[str] | None = None  # 券種フィルタ
max_bets: int | None = None                   # 買い目上限
```

**処理パイプライン**:
1. 勝率からHarvilleモデルで各組合せの確率を算出
   - 馬連: `P(A,B) = harville_exacta(A,B) + harville_exacta(B,A)`
   - 馬単: `P(A→B) = harville_exacta(A,B)`
   - 三連複: 6順列のharville_trifecta合算
   - 三連単: `harville_trifecta(A,B,C)`
   - ワイド: 全非選択馬Cの6順列trifecta合算
2. 推定オッズ算出（単勝オッズの積 × 券種補正係数）
3. 確率 × 推定オッズ = 期待値（EV）を全組合せで計算
4. EV > 1.0 の組合せをフィルタ（期待値がプラス）
5. EV降順でソート、上位N件を選択
6. 予算配分（ダッチングまたはEV比例）
7. ナレーション生成（`_invoke_haiku_narrator`）

**返り値**: 現在の`generate_bet_proposal`と同じ構造（フロントエンド互換性維持）

### システムプロンプト変更

```
現在: 「generate_bet_proposal だけを呼べ。他のツールは禁止。」

新: 「1. analyze_race_for_betting を呼んでレース分析データを取得せよ
      2. 分析結果を見て、各馬の勝率を判断せよ
         - ベース確率を参考にしつつ、展開・スピード指数・近走成績を考慮して調整
         - 合計が1.0になるように正規化すること
      3. propose_bets に勝率を渡して買い目提案を生成せよ」
```

## 廃止されるもの

| 既存コンポーネント | 理由 |
|---|---|
| `_calculate_composite_score()` | 確率ベースに置換。「スコアで順位付け」→「確率でEV計算」に |
| `_select_axis_horses()` | 軸馬の概念自体が不要に。EVが高い組合せを選ぶだけ |
| `_select_bet_types_by_difficulty()` | 難易度→券種の固定マッピング不要。EV > 1.0 で自動選定 |
| `CHARACTER_PROFILES` | ペルソナの重み調整はLLMの判断に吸収 |
| `BettingPreference` 関連マッピング | ユーザー好みはシステムプロンプトでLLMに伝える |
| `DIFFICULTY_BET_TYPES` | 同上 |
| `generate_bet_proposal` (既存ツール) | 新2ツールに分離して廃止 |

## 再利用されるもの

| 既存コンポーネント | 用途 |
|---|---|
| `_compute_unified_win_probabilities()` | Tool 1 内で重み付き版に改善して使用 |
| `_calculate_combination_ev()` | Tool 2 の中核。Harvilleモデル+EV計算 |
| `_harville_exacta()` / `_harville_trifecta()` | Harvilleモデルの確率計算 |
| `BET_TYPE_ODDS_MULTIPLIER` | 推定オッズ算出の補正係数 |
| `_allocate_budget()` / `_allocate_budget_dutching()` | 予算配分ロジック |
| `_invoke_haiku_narrator()` | LLMナレーション生成 |
| `_assess_race_difficulty()` / `_predict_pace()` | レース分析（Tool 1で使用） |
| `_assess_skip_recommendation()` | 見送り判定（Tool 1で使用） |

## テスト戦略

### Tool 1 のテスト
- ソース重み付け: 各ソースに異なるスコア → 重み付き平均が正しいか
- データ欠損: ソースが1つしかない場合、スピード指数がない場合 etc.
- 確率の合計が1.0になることの検証

### Tool 2 のテスト
- EV計算: 既知の確率とオッズ → 正しいEVが算出されるか
- 買い目選定: EV > 1.0 のものだけが選ばれるか
- 予算配分: ダッチング/従来モードが正しく動作するか
- エッジケース: 全組合せEV < 1.0 の場合（買い目ゼロ）

### 統合テスト
- LLMが確率を渡す → 期待通りの買い目が生成される
- フロントエンドの互換性: 返り値の構造が変わっていないこと
