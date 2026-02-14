# LLMナレーション設計: 買い目提案の根拠テキスト生成

## 背景

現在の `_generate_proposal_reasoning()` はテンプレート文字列で根拠テキストを生成しており、毎回同じ文面になる。レースごとの文脈に応じた洞察（過去成績の傾向、スピード指数の推移、展開の読み等）をLLMに語らせたい。

## 方針

- Phase 0-6（データ収集〜予算配分）は既存Pythonロジックを一切変更しない
- Phase 7（提案理由生成）のみ、Haiku 4.5 による自然言語生成に置換
- フロントエンドの表示ロジック（【セクション名】パース）は変更しない

## アーキテクチャ

```
generate_bet_proposal()
  │
  ├── Phase 0-6: 既存ロジック（変更なし）
  │     → structured_data (dict)
  │
  └── Phase 7: LLMナレーション（変更箇所）
        │
        ├── _build_narration_context()
        │     構造化データ + 生データ → context dict
        │
        ├── _invoke_haiku_narrator(context)
        │     Bedrock API → Haiku 4.5 → テキスト生成
        │
        └── フォールバック: 失敗時は既存テンプレート生成
```

## narrator プロンプト

### システムプロンプト

```
あなたは競馬データアナリストです。
以下のデータを元に、買い目提案の根拠を4セクションで書いてください。

## 出力フォーマット（厳守）
以下の4セクションを改行区切りで出力すること。セクション名は【】で囲む。

【軸馬選定】...
【券種】...
【組み合わせ】...
【リスク】...

## ルール
- 4セクション（【軸馬選定】【券種】【組み合わせ】【リスク】）は必須
- 各セクション1〜3文で簡潔に
- データの数値（AI指数順位・スコア・オッズ等）は正確に引用すること
- レースごとの特徴や注目ポイントを自分の言葉で解説すること
- 過去成績がある場合は、具体的な着順推移や距離適性に言及
- スピード指数がある場合は、指数の位置づけや推移に言及
- 「おすすめ」「買うべき」等の推奨表現は禁止

## トーン制御
- AI合議が「明確な上位」「概ね合意」→ 確信的に語る
- AI合議が「やや接戦」「混戦」→ 慎重に、リスクにも触れながら語る
- 見送りスコア≥7 → 警戒的に、予算削減を強調
```

### ユーザーメッセージ

context_json をそのまま渡す。

### context_json 構造

```json
{
  "axis_horses": [
    {
      "horse_number": 1,
      "horse_name": "ドリームコア",
      "composite_score": 79.6,
      "ai_rank": 6,
      "ai_score": 339,
      "odds": 3.4,
      "speed_index_score": 100,
      "form_score": 77.0
    }
  ],
  "partner_horses": [
    {
      "horse_number": 8,
      "horse_name": "ラヴノー",
      "ai_rank": 4,
      "max_expected_value": 0.38
    }
  ],
  "difficulty": {
    "difficulty_stars": 3,
    "difficulty_label": "標準"
  },
  "predicted_pace": "スロー",
  "ai_consensus": "やや接戦",
  "skip": {
    "skip_score": 2,
    "reasons": [],
    "recommendation": "通常判断"
  },
  "bets": [
    {
      "bet_type_name": "馬連",
      "horse_numbers": [1, 8],
      "expected_value": 1.5,
      "composite_odds": 12.0,
      "confidence": "high"
    }
  ],
  "speed_index_raw": {
    "1": {"avg_index": 85.2, "rank": 1, "indices": [84, 86, 86]},
    "8": {"avg_index": 82.1, "rank": 3, "indices": [80, 82, 84]}
  },
  "past_performance_raw": {
    "1": {"recent_results": [1, 3, 2, 5, 8], "form_score": 77.0},
    "8": {"recent_results": [2, 1, 4, 3, 6], "form_score": 72.5}
  }
}
```

## 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `tools/bet_proposal.py` | `_generate_proposal_reasoning()` をHaiku呼び出しに置換 |
| `tools/bet_proposal.py` | `_build_narration_context()` 新規追加 |
| `tools/bet_proposal.py` | `_invoke_haiku_narrator()` 新規追加 |
| `tests/agentcore/test_bet_proposal.py` | ナレーション関連テストの更新 |

## 変更しないもの

- Phase 0-6 のロジック
- フロントエンドの表示ロジック（`BetProposalContent.tsx` の【】パース）
- エージェントプロンプト（`prompts/bet_proposal.py`）

## テスト方針

- `_build_narration_context()`: 入力データから正しい context dict が構築されるか
- `_invoke_haiku_narrator()`: Bedrock クライアントをモックし、4セクションが返ることを検証
- `_generate_proposal_reasoning()`: 統合テスト（モック経由）
- 既存テスト: 影響なしを確認（proposal_reasoning の完全一致テストは緩和）

## フォールバック

Haiku 呼び出しが失敗した場合（タイムアウト、APIエラー等）は、既存のテンプレート生成ロジックにフォールバックする。これにより可用性を維持。

## Bedrock モデル設定

- Model ID: `jp.anthropic.claude-haiku-4-5-20251001-v1:0`（東京リージョン inference profile）
- Max tokens: 1024
- Temperature: 0.7（表現のゆらぎを持たせるため）

## IAM 権限

既存の AgentCore Runtime ロール（`AmazonBedrockAgentCoreSDKRuntime-ap-northeast-1-c31c3fd2fb`）に Bedrock InvokeModel 権限が含まれているため、追加の権限変更は不要。
