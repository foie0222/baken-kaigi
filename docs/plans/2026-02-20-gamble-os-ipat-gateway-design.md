# GAMBLE-OS IPAT ゲートウェイ移行設計書

## 概要

JRA-VAN EC2経由のIPAT投票・残高照会を、GAMBLE-OS IPAT APIへの直接呼び出しに置き換える。

## 動機

- EC2 + VPC Link + ALB は廃止予定（HRDB-API移行 Phase 4）
- GAMBLE-OS GIIIプラン（月額3,300円）にIPAT APIが含まれている
- EC2への依存を1つずつ削減し、最終的なEC2廃止に近づける

## GAMBLE-OS IPAT API仕様

### 投票API

- **エンドポイント**: `https://api.gamble-os.net/systems/ip-bet-kb`
- **メソッド**: POST

**パラメータ:**

| パラメータ | 説明 | 値 |
|-----------|------|-----|
| tncid | team-nave CLUB メンバーID | Secrets Manager |
| tncpw | team-nave CLUB パスワード | Secrets Manager |
| gov | 中央/地方 | `C` (JRA固定) |
| uno | 加入者番号 | ユーザーIPAT認証情報 |
| pin | 暗証番号 | ユーザーIPAT認証情報 |
| pno | 認証番号 | ユーザーIPAT認証情報 |
| betcd | 投票/チェック | `bet` or `betchk` |
| money | 投票合計金額 | 算出 |
| buyeye | 買い目データ | フォーマット変換 |

**buyeyeフォーマット:**
```
日付,レース場コード,レース番号,式別,方式,金額,買い目,マルチ:...
```

**券種コードマッピング:**

| 既存 IpatBetType | GAMBLE-OS 式別 |
|-----------------|---------------|
| TANSYO | TAN |
| FUKUSYO | FUKU |
| UMAREN | UMAFUKU |
| WIDE | WIDE |
| UMATAN | UMATAN |
| SANRENPUKU | SANFUKU |
| SANRENTAN | SANTAN |

**レスポンス (JSON):**
- `ret`: リターンコード (0: OK, -1以下: Error)
- `msg`: エラーメッセージ
- `results`: 結果データ

### 残高照会API

- **エンドポイント**: `https://api.gamble-os.net/systems/ip-balance`
- **メソッド**: POST
- **パラメータ**: tncid, tncpw, gov, uno, pin, pno

**レスポンス results:**

| フィールド | 説明 |
|-----------|------|
| day_buy_money | 当日購入金額 |
| day_refund_money | 当日払い戻し金額 |
| total_buy_money | 累計購入金額 |
| total_refund_money | 累計払い戻し金額 |
| buy_limit_money | 購入限度額 |
| buy_possible_count | 購入可能回数 |

### ドライランモード

`betcd="betchk"` を送信すると、実際には投票せず投票直前で処理を停止し、パラメータチェックのみ実行する。テスト・動作確認に使用。

## アーキテクチャ

### Before

```
Lambda → EC2 FastAPI (jravan-api) → JRA IPAT
```

### After

```
Lambda → GambleOsIpatGateway → GAMBLE-OS API → JRA IPAT
```

### 認証情報の流れ

```
ユーザー → SecretsManagerCredentialsProvider
             → baken-kaigi/ipat/{user_id}
             → IpatCredentials (subscriber_number, pin, pars_number)

GambleOsIpatGateway
  → Secrets Manager: baken-kaigi/gamble-os-credentials (tncid, tncpw)
  → IpatCredentials から: uno=subscriber_number, pin=pin, pno=pars_number
  → POST GAMBLE-OS API
```

## コンポーネント

### 1. GambleOsIpatGateway（新規作成）

`IpatGateway` インターフェースを実装。

```python
class GambleOsIpatGateway(IpatGateway):
    BETTING_URL = "https://api.gamble-os.net/systems/ip-bet-kb"
    BALANCE_URL = "https://api.gamble-os.net/systems/ip-balance"

    def __init__(self, secret_name: str, *, dry_run: bool = False): ...
    def submit_bets(self, credentials: IpatCredentials, bet_lines: list[IpatBetLine]) -> bool: ...
    def get_balance(self, credentials: IpatCredentials) -> IpatBalance: ...
```

- GAMBLE-OS認証情報は `baken-kaigi/gamble-os-credentials` から取得（起動時1回）
- `dry_run=True` → `betcd="betchk"` でパラメータチェックのみ
- リトライなし（投票の重複実行リスク）
- `ret < 0` → `IpatGatewayError` を raise

### 2. IpatCredentials → GAMBLE-OS パラメータマッピング

| IpatCredentials | GAMBLE-OS |
|----------------|-----------|
| subscriber_number | uno |
| pin | pin |
| pars_number | pno |
| inet_id | (不要) |

### 3. IpatBetLine → buyeye変換

`IpatBetLine` の `to_buyeye_field()` メソッドを追加（または `GambleOsIpatGateway` 内で変換）。

**券種コード変換テーブル:**

```python
GAMBLE_OS_BET_TYPE_MAP = {
    IpatBetType.TANSYO: "TAN",
    IpatBetType.FUKUSYO: "FUKU",
    IpatBetType.UMAREN: "UMAFUKU",
    IpatBetType.WIDE: "WIDE",
    IpatBetType.UMATAN: "UMATAN",
    IpatBetType.SANRENPUKU: "SANFUKU",
    IpatBetType.SANRENTAN: "SANTAN",
}
```

### 4. 残高レスポンスマッピング

| GAMBLE-OS results | IpatBalance |
|-------------------|-------------|
| buy_limit_money | limit_vote_amount |
| day_buy_money | bet_dedicated_balance |
| buy_limit_money - day_buy_money | bet_balance |
| total_buy_money | settle_possible_balance |

## 変更対象ファイル

### 新規作成

- `backend/src/infrastructure/providers/gamble_os_ipat_gateway.py`
- `backend/tests/infrastructure/providers/test_gamble_os_ipat_gateway.py`

### 変更

- `backend/src/api/dependencies.py` — `get_ipat_gateway()` の判定ロジック変更
- `backend/batch/auto_bet_executor.py` — `JraVanIpatGateway` → `GambleOsIpatGateway`
- `cdk/stacks/batch_stack.py` — Lambda環境変数から `JRAVAN_API_URL` を削除、`GAMBLE_OS_SECRET_NAME` を追加（auto_bet_executor用）

### 削除

- `backend/src/infrastructure/providers/jravan_ipat_gateway.py`
- `backend/tests/infrastructure/providers/test_jravan_ipat_gateway.py`

### 削除しない（EC2依存が残る）

- `jravan-api/` — レースデータ・オッズ取得でまだ使用中（Phase 2/4で対応）
- `backend/agentcore/tools/jravan_client.py` — AgentCoreツールが依存
- `backend/src/infrastructure/providers/jravan_race_data_provider.py` — レースデータ取得
- `backend/batch/auto_bet_executor.py` の `_fetch_odds()` — オッズ取得はEC2依存のまま（GAMBLE-OSオッズAPIはライセンスなし）
- `backend/batch/auto_bet_orchestrator.py` — レース一覧取得はEC2依存のまま

## エラーハンドリング

- `ret < 0` → `IpatGatewayError(msg)` を raise
- HTTPエラー → `IpatGatewayError` を raise
- Secrets Manager取得失敗 → そのまま例外伝播（握りつぶさない）
- リトライなし（既存方針を踏襲、投票重複リスク回避）

## テスト戦略

- `GambleOsIpatGateway`: HTTPモック（`requests_mock` or `unittest.mock.patch`）でGAMBLE-OS APIレスポンスをテスト
- buyeyeフォーマット変換: 各券種のユニットテスト
- 残高マッピング: レスポンスJSONからのIpatBalance変換テスト
- エラーケース: `ret=-1`, HTTP 500, タイムアウト
- ドライランモード: `betcd="betchk"` が送信されることを検証
