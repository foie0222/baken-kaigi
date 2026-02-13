# HRDB-API移行設計書

## 概要

JRA-VAN API（EC2 + PostgreSQL）からteam-naveのGAMBLE-OSプラットフォームへ移行し、EC2/VPC/JRA-VAN契約を全廃する。

## 移行対象サービス

| GAMBLE-OS API | 用途 | 置換対象 |
|--------------|------|---------|
| HRDB-API | レース・馬・騎手・血統・成績データ | EC2 JRA-VAN API |
| リアルタイムオッズAPI | オッズ履歴 | EC2 odds-history |
| JRA-IPAT投票API | 馬券購入・残高照会 | EC2 IPAT機能 |

料金: 月額3,300円（税込）GAMBLE-OS GIIIプラン

## アーキテクチャ

### Before

```
フロントエンド → API Gateway → Lambda → EC2 FastAPI → PC-KEIBA DB (PostgreSQL)
                                                     → JV-Link (IPAT)
```

### After

```
フロントエンド → API Gateway → Lambda → DynamoDB (レースデータ)
                                      → GAMBLE-OS API (IPAT投票)
                                      → GAMBLE-OS API (リアルタイムオッズ)

EventBridge → Lambda (バッチ) → HRDB-API → DynamoDB (レースデータ)
```

## DynamoDB新テーブル

| テーブル | PK | SK | GSI | 内容 |
|---------|----|----|-----|------|
| `baken-kaigi-races` | `race_date` | `race_id` | - | レース概要（RACEMST相当） |
| `baken-kaigi-runners` | `race_id` | `horse_number` | `horse_id-index` (PK: horse_id, SK: race_date) | 出走馬詳細（RACEDTL相当） |
| `baken-kaigi-horses` | `horse_id` | `info` | - | 競走馬マスタ（HORSE相当） |
| `baken-kaigi-jockeys` | `jockey_id` | `info` | - | 騎手マスタ（JKY相当） |
| `baken-kaigi-trainers` | `trainer_id` | `info` | - | 調教師マスタ（TRNR相当） |

`runners` テーブルの `horse_id-index` GSIにより、特定馬の過去成績をクエリ可能。

## HRDB-APIクライアント

HRDB-APIは非同期バッチ型API:

1. データベース検索要求（SQL送信）
2. データベース処理状況（ポーリング、完了まで待機）
3. データベースデータ（CSV）要求（結果取得）
4. CSVパース → list[dict]

```python
class HrdbClient:
    """GAMBLE-OS HRDB-API クライアント."""

    def __init__(self, club_id: str, club_password: str, api_domain: str): ...
    def query(self, sql: str) -> list[dict]: ...
```

認証情報: Secrets Manager（`baken-kaigi/gamble-os-credentials`）

### HRDB-API利用制限

- 同時3リクエストまで
- 1回最大55,555件
- 毎日AM6:00〜8:00メンテナンス
- FIRST句使用不可（アプリ側でフィルタリング）

## バッチ取得Lambda

| Lambda | スケジュール | 取得SQL | 格納先 |
|--------|-----------|--------|-------|
| `hrdb-races-scraper` | 毎晩21:00 + 当日朝8:00 JST | `SELECT * FROM RACEMST WHERE OPDT = '{date}'` | `races` |
| `hrdb-runners-scraper` | 同上 | `SELECT * FROM RACEDTL WHERE OPDT = '{date}'` | `runners` |
| `hrdb-horses-sync` | 毎晩22:00 JST | `SELECT * FROM HORSE WHERE BLDNO IN (...)` | `horses` |
| `hrdb-jockeys-sync` | 毎晩22:10 JST | `SELECT * FROM JKY WHERE JKYCD IN (...)` | `jockeys` |
| `hrdb-trainers-sync` | 毎晩22:20 JST | `SELECT * FROM TRNR WHERE TRNRCD IN (...)` | `trainers` |
| `hrdb-results-sync` | 毎週月曜 6:00 JST | `SELECT * FROM RACEDTL WHERE OPDT BETWEEN ...` | `runners` 更新 |

## データ層切り替え

### RaceDataProvider

`JraVanRaceDataProvider`（EC2呼び出し）→ `DynamoDbRaceDataProvider`（DynamoDB読み出し）に差し替え。

既存の `RaceDataProvider` インターフェースを維持するため、ハンドラー層は変更不要。

環境変数: `RACE_DATA_PROVIDER=dynamodb`

### AgentCoreツール（26個）

`cached_get()`（EC2 HTTP）→ `boto3` DynamoDB読み出しに改修。

| 現在のエンドポイント | 置換先 | 影響ツール数 |
|------------------|-------|------------|
| `/races/{race_id}` | `races` テーブル query | 8 |
| `/horses/{horse_id}/performances` | `runners` テーブル horse_id-index | 10 |
| `/horses/{horse_id}/pedigree` | `horses` テーブル get_item | 2 |
| `/jockeys/{jockey_id}/*` | `jockeys` テーブル get_item | 2 |
| `/trainers/{trainer_id}/*` | `trainers` テーブル get_item | 1 |
| `/statistics/*` | DynamoDB集計クエリ | 2 |
| `/races/{race_id}/odds-history` | リアルタイムオッズAPI | 1 |

### 廃止対象

- `jravan_client.py`（cached_get等）
- `JraVanRaceDataProvider`
- `JraVanIpatGateway`
- keibagrantスクレイパー

## IPAT投票移行

`JraVanIpatGateway` → `GambleOsIpatGateway`（GAMBLE-OS JRA-IPAT投票API直接呼び出し）。

既存の `IpatGateway` インターフェースを維持。

## リアルタイムオッズ

```python
class RealtimeOddsClient:
    """GAMBLE-OS リアルタイムオッズAPIクライアント."""
    def get_odds_history(self, race_id: str) -> OddsHistoryResponse: ...
```

AgentCoreの `odds_analysis.py` から呼び出し。

## CDKインフラ変更

### 追加

- DynamoDBテーブル5個
- バッチ取得Lambda 5個 + EventBridgeルール
- Secrets Managerシークレット（GAMBLE-OS認証情報）

### 削除

- `jravan_server_stack.py`（EC2 + VPC Link + ALB）
- VPC関連リソース
- JRA-VAN API関連Secrets Manager
- keibagrantスクレイパーLambda + EventBridgeルール

## 段階的移行フェーズ

### Phase 1: 基盤構築

- HRDB-APIクライアント実装 + テスト
- DynamoDBテーブル作成（CDK）
- バッチ取得Lambda実装（レース・出走馬・馬・騎手・調教師）
- 検証: バッチ取得→DynamoDB投入の正常動作

### Phase 2: データ層切り替え

- `DynamoDbRaceDataProvider` 実装
- AgentCoreツール26個をDynamoDB読み出しに改修
- keibagrantスクレイパー廃止
- 検証: 環境変数切り替えで新旧比較テスト

### Phase 3: IPAT・オッズ移行

- `GambleOsIpatGateway` 実装
- `RealtimeOddsClient` 実装
- 検証: 本番環境で投票・オッズの動作確認

### Phase 4: EC2廃止

- `jravan_server_stack.py` 削除
- VPC関連リソース整理
- JRA-VAN Data Lab.契約解除
- 旧コード削除

## テスト戦略

- HrdbClient: モックHTTPでSQL→ポーリング→CSV取得フローをテスト
- DynamoDbRaceDataProvider: moto（DynamoDBモック）で既存テスト互換性確認
- バッチLambda: HrdbClientモック + DynamoDB書き込み検証
- AgentCoreツール: モック先をEC2 API → DynamoDBに差し替え
- IPAT/オッズ: モックHTTPでGAMBLE-OS APIレスポンステスト
