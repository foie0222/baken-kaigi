# エージェント買い目生成 + ユーザー好み設定

## 概要

エージェント作成後のストーリー拡張。エージェントが「買い目を考えて」指示で買い目を生成し、ユーザーの好み設定を反映する。手動での買い目選択も引き続き可能。

## アプローチ

**A+Cハイブリッド**: プリセット選択（券種・狙い方・重視ポイント）+ 自然言語の追加指示

## ドメインモデル

### Agent エンティティ拡張

```
Agent (集約ルート)
  ├─ base_style: AgentStyle（既存: solid/longshot/data/pace）
  ├─ betting_preference: BettingPreference（新規・値オブジェクト）
  │    ├─ bet_type_preference: BetTypePreference
  │    │    → TRIO_FOCUSED / EXACTA_FOCUSED / QUINELLA_FOCUSED / WIDE_FOCUSED / AUTO
  │    ├─ target_style: TargetStyle
  │    │    → HONMEI / MEDIUM_LONGSHOT / BIG_LONGSHOT
  │    └─ priority: BettingPriority
  │         → HIT_RATE / ROI / BALANCED
  ├─ custom_instructions: str | None（最大200文字）
  └─ （既存フィールドはそのまま）
```

### デフォルト値

- `bet_type_preference`: AUTO
- `target_style`: MEDIUM_LONGSHOT
- `priority`: BALANCED
- `custom_instructions`: None

### 棲み分け

- `base_style` = エージェントの性格（分析アプローチ）
- `betting_preference` = ユーザーの投資好み（券種・リスク・目標）
- `custom_instructions` = ニュアンス補完（自然言語）

## 買い目生成への反映

### プリセット → 数値変換

```python
# target_style → DIFFICULTY_BET_TYPESのキー選択に影響
TARGET_STYLE_RISK = {
    "HONMEI": 2,
    "MEDIUM_LONGSHOT": 3,
    "BIG_LONGSHOT": 5,
}

# bet_type_preference → 券種候補のフィルタリング
BET_TYPE_FILTER = {
    "TRIO_FOCUSED": ["trio", "trio_quinella"],
    "EXACTA_FOCUSED": ["exacta", "quinella"],
    "QUINELLA_FOCUSED": ["quinella", "quinella_place"],
    "WIDE_FOCUSED": ["quinella_place", "wide"],
    "AUTO": None,
}

# priority → 軸馬・相手馬選定の調整
PRIORITY_WEIGHTS = {
    "HIT_RATE": {"max_partners": 5, "axis_threshold": 0.6},
    "ROI":      {"max_partners": 3, "axis_threshold": 0.4},
    "BALANCED": {"max_partners": 4, "axis_threshold": 0.5},
}
```

### 自然言語 → プロンプト注入

`custom_instructions` をAgentCoreシステムプロンプトに追加:

```
既存プロンプト
+ base_style による性格設定（既存）
+ 「ユーザーの追加指示: {custom_instructions}」（新規）
```

## API

### 好み設定の保存

```
PUT /agents/me  ← 既存エンドポイント拡張
body: {
  betting_preference: {
    bet_type_preference: "TRIO_FOCUSED",
    target_style: "MEDIUM_LONGSHOT",
    priority: "ROI"
  },
  custom_instructions: "三連単の1着固定が好き"
}
```

### 買い目生成時のペイロード

```
AgentCore呼び出し時:
payload.agent_data: {
  ...(既存),
  betting_preference: {...},
  custom_instructions: "..."
}
```

## フロントエンドUI

AgentProfilePage に「好み設定」セクション追加:

```
[エージェントプロフィール画面]
├─ エージェント名（既存）
├─ スタイル選択（既存）
├─ ─── 好み設定 ───
│   ├─ 券種の好み:   [三連系] [馬連系] [ワイド] [おまかせ]  ← チップ選択
│   ├─ 狙い方:       [本命] [中穴] [大穴]                    ← チップ選択
│   ├─ 重視ポイント: [的中率] [回収率] [バランス]              ← チップ選択
│   └─ 追加指示:     [テキストエリア 200文字]                  ← 自由記述
└─ [保存]
```

## データフロー

```
フロント → PUT /agents/me → Lambda → DynamoDB（好み保存）

フロント → チャット「買い目を考えて」
  → AgentCore（preference + instructions付きペイロード）
  → システムプロンプトにinstructions注入
  → generate_bet_proposal（preference反映）
  → 買い目提案を返す
  → フロント表示（既存UIで表示可能）
```

## 手動買い目との共存

- 既存のカート機能はそのまま維持
- エージェント提案 → 「カートに追加」で手動フローに合流
