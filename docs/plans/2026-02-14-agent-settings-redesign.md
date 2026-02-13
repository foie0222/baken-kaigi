# エージェント設定の改善

## 概要

エージェントの名前/スタイルの変更可否を見直し、能力値を削除し、UIテキストを改善する。

## 変更内容

### 1. テキスト修正（OnboardingPage）

- ヘッダー説明文: 「あなた好みの分析ができるようになります」→「あなたの好みで分析できるようになります」
- フッター注釈: 「スタイルは後から変更できませんが、名前は変更できます」→「名前は後から変更できませんが、スタイルは変更できます」

### 2. 名前変更の無効化 / スタイル変更の有効化

**バックエンド:**
- `Agent` エンティティ: `update_name()` を削除、`update_style(style: AgentStyle)` を追加
- `UpdateAgentUseCase`: `name` パラメータを `base_style` に変更
- `PUT /agents/me` ハンドラー: リクエストボディを `{ base_style }` に変更

**フロントエンド:**
- `apiClient.updateAgent(name)` → `apiClient.updateAgent(baseStyle)` に変更
- `agentStore.updateAgent(name)` → `agentStore.updateAgent(baseStyle)` に変更

### 3. 能力値（AgentStats）の削除

- AgentProfilePageから能力値セクション削除
- 振り返り時の `stats_change` 計算・保存を削除
- 振り返りカードの `stats_change` バッジ表示を削除
- `Agent` エンティティから `stats` フィールドを削除
- APIレスポンスから `stats` を除去
- フロントエンド `Agent` 型から `stats` を除去

### 4. AgentProfilePage スタイル変更UI

- スタイルバッジの横に「変更」テキストリンクを追加
- タップするとOnboardingPageと同じ2x2グリッドがインラインで展開
- 選択するとAPIを呼んでスタイルを更新、グリッドを閉じる

## 設計判断

- **名前は固定**: エージェントのアイデンティティ。「相棒」感を重視
- **スタイルは可変**: 使いながら好みが変わることがある。柔軟性を確保
- **能力値は削除**: 成長の仕組みがユーザーに伝わっておらず、価値が不明瞭
- **作り直しは不可**: エージェントは1体のみ。愛着を持って育てる設計

## 影響範囲

### フロントエンド
- `OnboardingPage.tsx` — テキスト修正
- `AgentProfilePage.tsx` — 能力値削除、スタイル変更UI追加
- `api/client.ts` — updateAgent のパラメータ変更
- `stores/agentStore.ts` — updateAgent のパラメータ変更
- `types/index.ts` — Agent型からstats除去

### バックエンド
- `domain/entities/agent.py` — stats削除、update_name→update_style
- `domain/value_objects/agent_stats.py` — 未使用になるが互換性のため残す
- `application/use_cases/update_agent.py` — name→base_style
- `application/use_cases/create_agent_review.py` — stats_change計算削除
- `api/handlers/agent.py` — PUT仕様変更、レスポンスからstats除去
- テスト各種
