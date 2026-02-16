# オッズAPI統合設計

## 背景

#507 で EV ベース買い目提案が実オッズ参照に切り替わった。
EC2 FastAPI に `GET /races/{race_id}/odds`（全券種一括取得）を追加したが、
API Gateway にルートが未登録のため AgentCore から 403 Forbidden が発生。

同時に `GET /races/{race_id}/bet-odds` Lambda は EC2 の存在しないエンドポイントを呼んでおり機能していない。

## 方針

オッズ取得ロジックを **1 エンドポイントに統合** する。

- `GET /races/{race_id}/odds` を唯一のオッズ取得 API とする
- フロントエンドは全券種を一括取得し、クライアント側で必要な券種を抽出
- AgentCore は既存の `_fetch_all_odds()` がそのまま動く（URL 変更不要）
- `GET /races/{race_id}/bet-odds` は削除

## アーキテクチャ

```
AgentCore / フロントエンド
  → API Gateway GET /races/{race_id}/odds (x-api-key)
  → Lambda get_all_odds()
  → JraVanRaceDataProvider.get_all_odds()
  → EC2 FastAPI GET /races/{race_id}/odds
  → PostgreSQL jvd_o1~o6
```

リアルタイムオッズ（レース前）と確定オッズ（レース後）は同一テーブルに格納されるため、
エンドポイントは同じ。データ未提供時は 404。

## レスポンス形式

```json
{
  "race_id": "202602150511",
  "win": {"1": 3.5, "2": 12.0},
  "place": {"1": {"min": 1.2, "max": 1.5}},
  "quinella": {"1-2": 64.8},
  "quinella_place": {"1-2": 10.5},
  "exacta": {"1-2": 128.5},
  "trio": {"1-2-3": 341.9},
  "trifecta": {"1-2-3": 2048.3}
}
```

18 頭フルゲートで約 6,360 エントリ、JSON 約 100KB。API Gateway 上限 10MB に対して余裕あり。

## 追加するもの

| ファイル | 内容 |
|---|---|
| `backend/src/domain/ports/race_data_provider.py` | `AllOddsData` モデル + `get_all_odds()` ポート |
| `backend/src/infrastructure/providers/jravan_race_data_provider.py` | `get_all_odds()` 実装 |
| `backend/src/api/handlers/races.py` | `get_all_odds()` Lambda ハンドラ |
| `cdk/stacks/api_stack.py` | Lambda 定義 + API Gateway `/odds` ルート |
| `frontend/src/api/client.ts` | `getAllOdds()` メソッド |
| フロントエンド各所 | `getBetOdds()` → `getAllOdds()` + クライアント抽出に置換 |

## 削除するもの

| ファイル | 内容 |
|---|---|
| `backend/src/api/handlers/races.py` | `get_bet_odds()` ハンドラ |
| `backend/src/domain/ports/race_data_provider.py` | `BetOddsData` + `get_bet_odds()` ポート |
| `backend/src/infrastructure/providers/jravan_race_data_provider.py` | `get_bet_odds()` 実装 |
| `cdk/stacks/api_stack.py` | `get_bet_odds` Lambda + API Gateway `/bet-odds` ルート |
| `frontend/src/api/client.ts` | `getBetOdds()` メソッド |
| 関連テスト | 上記に対応するテスト |

## エラーハンドリング

- EC2 から 404（オッズ未提供）→ Lambda も 404 → フロントエンドで「オッズ未取得」表示
- AgentCore `_fetch_all_odds()` の 404 → `{}` で継続（EV=0 で買い目なし）
- エラーは握りつぶさず早期失敗（CLAUDE.md コーディング原則）

## AgentCore 側

変更なし。`ev_proposer.py` の `_fetch_all_odds()` は同じ URL を呼ぶ。
API Gateway にルートが追加されるため 403 が解消する。
