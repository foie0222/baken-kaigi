# 券種選択の直接指定化

## 概要

「券種の好み」（抽象的な5択: 三連系重視/馬単系重視/...）を廃止し、
実際に購入する券種を直接選択するUIに変更する。

## 変更内容

### UI変更

- ラベル: 「券種の好み」→「購入する券種」
- 選択方式: 単一選択ボタン → 複数選択トグルボタン
- 選択肢: 単勝 / 複勝 / ワイド / 馬連 / 馬単 / 三連複 / 三連単
- 未選択時は全券種対象（現在の `auto` と同等）

### データモデル変更

**フロントエンド:**
- `BetTypePreference` 型を廃止
- `BettingPreference.bet_type_preference` → `BettingPreference.selected_bet_types: BetType[]`
- `bettingPreferences.ts` の `BET_TYPE_PREFERENCE_OPTIONS` を削除

**バックエンド:**
- `BetTypePreference` enum (`bet_type_preference.py`) を削除
- `BettingPreference` の `bet_type_preference: BetTypePreference` → `selected_bet_types: list[str]`
- DynamoDB保存形式: `"bet_type_preference": "trio_focused"` → `"selected_bet_types": ["trio", "trifecta"]`

### バックエンドロジック変更

- `ev_proposer.py`:
  - `_BET_TYPE_PREFERENCE_MAP` を削除
  - `_resolve_bet_types()` を簡略化: `selected_bet_types` が空なら `DEFAULT_BET_TYPES`、そうでなければそのまま使用

### 旧データの扱い

- 後方互換性なし。既存データは再保存で対応。
