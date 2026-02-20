# HRDB-API移行設計書

## 概要

JRA-VAN API（EC2 + PostgreSQL）からteam-naveのGAMBLE-OSプラットフォームへ移行し、EC2/VPC/JRA-VAN契約を全廃する。

## 移行対象サービス

| GAMBLE-OS API | 用途 | 置換対象 | 状態 |
|--------------|------|---------|------|
| HRDB-API | レース・馬・騎手・血統・成績データ | EC2 JRA-VAN API | **利用可能** |
| リアルタイムオッズAPI | オッズ履歴 | EC2 odds-history | **ライセンスなし** (ret=-203) |
| JRA-IPAT投票API | 馬券購入・残高照会 | EC2 IPAT機能 | 未検証 |

料金: 月額3,300円（税込）GAMBLE-OS GIIIプラン

> **2026-02-20 実装結果:** リアルタイムオッズAPIは `-203 "Authentication no license error"` を返す。GIIIプランではHRDB-APIのみ利用可能。オッズデータ取得は別手段が必要。

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

| テーブル | PK | SK | GSI | 内容 | 状態 |
|---------|----|----|-----|------|------|
| `baken-kaigi-races` | `race_date` | `race_id` | - | レース概要（RACEMST相当） | **Phase 1 作成済み** |
| `baken-kaigi-runners` | `race_id` | `horse_number` | `horse_id-index` (PK: horse_id, SK: race_date) | 出走馬詳細（RACEDTL相当） | **Phase 1 作成済み** |
| `baken-kaigi-horses` | `horse_id` | `info` | - | 競走馬マスタ（HORSE相当） | 未作成 |
| `baken-kaigi-jockeys` | `jockey_id` | `info` | - | 騎手マスタ（JKY相当） | 未作成 |
| `baken-kaigi-trainers` | `trainer_id` | `info` | - | 調教師マスタ（TRNR相当） | 未作成 |

`runners` テーブルの `horse_id-index` GSIにより、特定馬の過去成績をクエリ可能。

全テーブル共通: `BillingMode=PAY_PER_REQUEST`, `RemovalPolicy=DESTROY`, `TTL=ttl`属性

## HRDB-APIクライアント

HRDB-APIは非同期バッチ型API:

1. データベース検索要求（SQL送信） — `prccd=select`
2. データベース処理状況（ポーリング、完了まで待機） — `prccd=state`
3. データベースデータ（CSV）要求（結果取得） — `prccd=geturl`
4. CSVパース → list[dict]

### 認証

- **方式:** POST form data (`tncid` + `tncpw`)
- **tncid:** team-nave CLUBメールアドレス（`daikinoue0222@gmail.com`）
- **tncpw:** team-nave CLUBパスワード
- **エンドポイント:** `https://api.gamble-os.net/systems/hrdb`
- **認証情報格納先:** Secrets Manager（`baken-kaigi/gamble-os-credentials`）

> **注意:** メールアドレスは `daikinoue0222@gmail.com`（daikの後に"i"あり）。

```python
class HrdbClient:
    """GAMBLE-OS HRDB-API クライアント."""

    def __init__(self, club_id: str, club_password: str): ...
    def query(self, sql: str) -> list[dict]: ...
    def query_dual(self, sql1: str, sql2: str) -> tuple[list[dict], list[dict]]: ...
```

### CSVレスポンス

- **エンコーディング:** Shift-JIS（`shift_jis`でデコードが必要、UTF-8ではない）
- **カラム値:** 大量の空白でパディングされている → `.strip()` 必須
- **引用符:** ダブルクォートで囲まれている場合あり

### HRDB-API利用制限

- 同時3リクエストまで（`cmd1`, `cmd2`, `cmd3` で同時送信可能）
- 1回最大55,555件
- 毎日AM6:00〜8:00メンテナンス
- ~~FIRST句使用不可（アプリ側でフィルタリング）~~ → **FIRST N 句は使用可能**（Firebird SQL の `LIMIT` 相当）

### Firebird SQLテーブル（確認済み）

| テーブル | 内容 |
|---------|------|
| RACEMST | レースマスタ |
| RACEDTL | レース出走馬詳細 |
| HORSE | 競走馬マスタ |
| JKY | 騎手マスタ |
| TRNR | 調教師マスタ |

### RACEMSTカラム（確認済み）

`OPDT`, `RCOURSECD`, `RNO`, `RNMHON`(レース名), `GCD`(グレード), `DIST`(距離), `TRACKCD`(トラックコード), `ENTNUM`(登録頭数), `RUNNUM`(出走頭数), `POSTTM`(発走時刻), `WEATHERCD`, `TSTATCD`(芝状態), `DSTATCD`(ダート状態), `RKINDCD`, `KAI`(開催回), `NITIME`(日次)

### RACEDTLカラム（確認済み）

`OPDT`, `RCOURSECD`, `RNO`, `UMANO`(馬番), `BLDNO`(血統登録番号=horse_id), `WAKNO`(枠番), `HSNM`(馬名), `SEXCD`, `AGE`, `JKYCD`(騎手コード), `JKYNM4`(騎手名), `TRNRCD`(調教師コード), `TRNRNM4`(調教師名), `FTNWGHT`(斤量x10), `FIXPLC`(着順), `RUNTM`(走破タイム), `TANODDS`(単勝オッズx10), `TANNINKI`(単勝人気), `CONRPLC1`〜`CONRPLC4`(コーナー通過順)

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

> **2026-02-20 実装結果:** GAMBLE-OS リアルタイムオッズAPIは現在のGIIIプランでは利用不可（`-203 "Authentication no license error"`）。オッズデータの取得は別手段（上位プランへのアップグレード、または別のデータソース）を検討する必要がある。

当初の設計（無効）:
- ~~`RealtimeOddsClient` でオッズ履歴を取得~~
- ~~AgentCoreの `odds_analysis.py` から呼び出し~~

## CDKインフラ変更

### 追加（Phase 1 完了分）

- DynamoDBテーブル2個（`baken-kaigi-races`, `baken-kaigi-runners`）— `api_stack.py`
- バッチ取得Lambda 1個（`baken-kaigi-hrdb-race-scraper`）— `batch_stack.py`
- EventBridgeルール2個（毎晩21:00 JST offset_days=1 + 当日8:30 JST offset_days=0）
- Secrets Manager読み取り権限（`baken-kaigi/gamble-os-credentials`）
- AgentCoreランタイムロールにraces/runnersテーブルのread権限追加

### 追加（今後）

- DynamoDBテーブル3個（horses, jockeys, trainers）
- バッチ取得Lambda 4個（horses-sync, jockeys-sync, trainers-sync, results-sync）

### 削除（Phase 4）

- `jravan_server_stack.py`（EC2 + VPC Link + ALB）
- VPC関連リソース
- JRA-VAN API関連Secrets Manager
- keibagrantスクレイパーLambda + EventBridgeルール

## 段階的移行フェーズ

### Phase 1: 基盤構築 -- **完了 (2026-02-20)**

6コミットで実装完了:

1. `feat: HrdbClient — GAMBLE-OS HRDB-API クライアント実装`
2. `feat: HRDB定数・コード変換モジュール`
3. `feat: HRDBレースデータバッチスクレイパー`
4. `feat: races/runnersテーブル定義追加（HRDB-API移行）`
5. `feat: HRDBスクレイパーLambda + EventBridge定義（CDK）`
6. `chore: HRDB-APIローカル確認スクリプト追加`

実装ファイル:
- `backend/batch/hrdb_client.py` — HRDB-APIクライアント（query + query_dual）
- `backend/batch/hrdb_constants.py` — レース場コード・race_id変換
- `backend/batch/hrdb_race_scraper.py` — バッチスクレイパーLambda handler
- `cdk/stacks/api_stack.py` — DynamoDBテーブル定義（races, runners）
- `cdk/stacks/batch_stack.py` — Lambda + EventBridgeルール定義

Secrets Manager:
- シークレット名: `baken-kaigi/gamble-os-credentials`
- 内容: `{"tncid": "...", "tncpw": "..."}`（HRDB-APIパラメータ名に準拠）

### Phase 2: データ層切り替え

- `DynamoDbRaceDataProvider` 実装
- AgentCoreツール26個をDynamoDB読み出しに改修
- keibagrantスクレイパー廃止
- 検証: 環境変数切り替えで新旧比較テスト

### Phase 3: IPAT・オッズ移行

- `GambleOsIpatGateway` 実装
- ~~`RealtimeOddsClient` 実装~~ → オッズAPIはライセンスなし、別手段を検討
- 検証: 本番環境で投票の動作確認

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
