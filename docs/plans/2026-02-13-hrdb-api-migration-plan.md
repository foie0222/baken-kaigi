# HRDB-API移行 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** JRA-VAN API（EC2）をGAMBLE-OS HRDB-APIに移行し、EC2/VPC/JRA-VAN契約を全廃する。

**Architecture:** EventBridge → Lambda → HRDB-API → DynamoDB のバッチ取得パターンでレースデータを事前格納。ハンドラー層は既存の `RaceDataProvider` / `IpatGateway` インターフェースを維持して `DynamoDbRaceDataProvider` / `GambleOsIpatGateway` に差し替え。AgentCoreツール17個は `cached_get()` → DynamoDB直接読み出しに改修。

**Tech Stack:** Python 3.12, boto3, moto, requests, AWS CDK, DynamoDB, EventBridge, Secrets Manager, Strands Agents SDK

**設計書:** `docs/plans/2026-02-13-hrdb-api-migration-design.md`

---

## Phase 1: 基盤構築

### Task 1: HrdbClient — テスト作成

HRDB-APIの非同期バッチ型フローをテストする。SQL送信→ポーリング→CSV取得の3ステップ。

**Files:**
- Create: `backend/src/infrastructure/clients/hrdb_client.py`
- Create: `backend/tests/infrastructure/clients/test_hrdb_client.py`

**Step 1: Write the failing test**

```python
# backend/tests/infrastructure/clients/test_hrdb_client.py
"""HRDB-APIクライアントのテスト."""
import csv
import io
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.clients.hrdb_client import HrdbClient, HrdbApiError


class TestHrdbClientQuery:
    """HrdbClient.query() のテスト."""

    def _make_client(self) -> HrdbClient:
        return HrdbClient(
            club_id="TEST_CLUB",
            club_password="TEST_PASS",
            api_domain="https://api.example.com",
        )

    def test_正常系_SQL実行でCSV結果をdictリストで返す(self):
        """SQL送信→ポーリング→CSV取得の正常フロー."""
        client = self._make_client()

        # Phase 1: SQL送信 → req_id 取得
        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {"ret": "0", "req_id": "REQ001"}

        # Phase 2: ポーリング → 完了
        poll_response = MagicMock()
        poll_response.status_code = 200
        poll_response.json.return_value = {"ret": "0", "status": "done", "count": "2"}

        # Phase 3: CSV取得
        csv_data = "OPDT,RCOURSECD,RNO\n20260215,06,01\n20260215,06,02\n"
        csv_response = MagicMock()
        csv_response.status_code = 200
        csv_response.text = csv_data

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [submit_response, poll_response, csv_response]
            result = client.query("SELECT OPDT, RCOURSECD, RNO FROM RACEMST")

        assert len(result) == 2
        assert result[0]["OPDT"] == "20260215"
        assert result[0]["RCOURSECD"] == "06"
        assert result[1]["RNO"] == "02"

    def test_SQL送信エラーで例外を送出する(self):
        """SQL送信が失敗した場合."""
        client = self._make_client()

        error_response = MagicMock()
        error_response.status_code = 200
        error_response.json.return_value = {"ret": "1", "msg": "SQL error"}

        with patch("requests.post", return_value=error_response):
            with pytest.raises(HrdbApiError, match="SQL error"):
                client.query("INVALID SQL")

    def test_ポーリングでタイムアウトすると例外を送出する(self):
        """ポーリングが最大回数に達した場合."""
        client = self._make_client()
        client._max_poll_attempts = 2
        client._poll_interval = 0  # テスト用に即時

        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {"ret": "0", "req_id": "REQ001"}

        poll_response = MagicMock()
        poll_response.status_code = 200
        poll_response.json.return_value = {"ret": "0", "status": "running"}

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [submit_response, poll_response, poll_response]
            with pytest.raises(HrdbApiError, match="タイムアウト"):
                client.query("SELECT * FROM RACEMST")

    def test_CSV結果が0件の場合は空リストを返す(self):
        """結果が0件の場合."""
        client = self._make_client()

        submit_response = MagicMock()
        submit_response.status_code = 200
        submit_response.json.return_value = {"ret": "0", "req_id": "REQ001"}

        poll_response = MagicMock()
        poll_response.status_code = 200
        poll_response.json.return_value = {"ret": "0", "status": "done", "count": "0"}

        csv_response = MagicMock()
        csv_response.status_code = 200
        csv_response.text = ""

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [submit_response, poll_response, csv_response]
            result = client.query("SELECT * FROM RACEMST WHERE OPDT = '99991231'")

        assert result == []
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/infrastructure/clients/test_hrdb_client.py -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

**Step 3: Write minimal implementation**

```python
# backend/src/infrastructure/clients/__init__.py
# (空ファイル)
```

```python
# backend/src/infrastructure/clients/hrdb_client.py
"""GAMBLE-OS HRDB-API クライアント."""
import csv
import io
import logging
import time

import requests

logger = logging.getLogger(__name__)


class HrdbApiError(Exception):
    """HRDB-API エラー."""

    pass


class HrdbClient:
    """GAMBLE-OS HRDB-API クライアント.

    非同期バッチ型API:
    1. データベース検索要求（SQL送信）
    2. データベース処理状況（ポーリング、完了まで待機）
    3. データベースデータ（CSV）要求（結果取得）
    """

    def __init__(
        self,
        club_id: str,
        club_password: str,
        api_domain: str,
    ) -> None:
        self._club_id = club_id
        self._club_password = club_password
        self._api_domain = api_domain.rstrip("/")
        self._max_poll_attempts = 60
        self._poll_interval = 2  # seconds
        self._timeout = 30

    def query(self, sql: str) -> list[dict]:
        """SQLを実行して結果をdictリストで返す."""
        req_id = self._submit_query(sql)
        self._wait_for_completion(req_id)
        return self._fetch_csv(req_id)

    def _submit_query(self, sql: str) -> str:
        """SQL送信してリクエストIDを取得する."""
        response = requests.post(
            f"{self._api_domain}/systems/kbdb-search",
            data={
                "tncid": self._club_id,
                "tncpw": self._club_password,
                "sql": sql,
            },
            timeout=self._timeout,
        )
        data = response.json()
        if data.get("ret") != "0":
            raise HrdbApiError(data.get("msg", "SQL送信に失敗しました"))
        req_id = data.get("req_id")
        if not req_id:
            raise HrdbApiError("リクエストIDが取得できませんでした")
        return req_id

    def _wait_for_completion(self, req_id: str) -> None:
        """ポーリングして処理完了を待つ."""
        for _ in range(self._max_poll_attempts):
            response = requests.post(
                f"{self._api_domain}/systems/kbdb-status",
                data={
                    "tncid": self._club_id,
                    "tncpw": self._club_password,
                    "req_id": req_id,
                },
                timeout=self._timeout,
            )
            data = response.json()
            if data.get("ret") != "0":
                raise HrdbApiError(data.get("msg", "ステータス確認に失敗しました"))
            if data.get("status") == "done":
                return
            time.sleep(self._poll_interval)
        raise HrdbApiError("ポーリングがタイムアウトしました")

    def _fetch_csv(self, req_id: str) -> list[dict]:
        """CSV結果を取得してdictリストに変換する."""
        response = requests.post(
            f"{self._api_domain}/systems/kbdb-data",
            data={
                "tncid": self._club_id,
                "tncpw": self._club_password,
                "req_id": req_id,
            },
            timeout=self._timeout,
        )
        text = response.text.strip()
        if not text:
            return []
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/infrastructure/clients/test_hrdb_client.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add backend/src/infrastructure/clients/__init__.py backend/src/infrastructure/clients/hrdb_client.py backend/tests/infrastructure/clients/test_hrdb_client.py
git commit -m "feat: HRDB-APIクライアント実装（SQL送信→ポーリング→CSV取得）"
```

---

### Task 2: CDK — DynamoDB新テーブル5個作成

**Files:**
- Create: `cdk/stacks/hrdb_tables_stack.py`

**Step 1: Write the CDK stack**

```python
# cdk/stacks/hrdb_tables_stack.py
"""HRDB移行用 DynamoDB テーブルスタック."""
from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class HrdbTablesStack(Stack):
    """HRDB移行用 DynamoDB テーブル."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # races テーブル（PK: race_date, SK: race_id）
        self.races_table = dynamodb.Table(
            self,
            "RacesTable",
            table_name="baken-kaigi-races",
            partition_key=dynamodb.Attribute(
                name="race_date", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="race_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # runners テーブル（PK: race_id, SK: horse_number）
        self.runners_table = dynamodb.Table(
            self,
            "RunnersTable",
            table_name="baken-kaigi-runners",
            partition_key=dynamodb.Attribute(
                name="race_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="horse_number", type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )
        # GSI: horse_id-index（馬の過去成績検索用）
        self.runners_table.add_global_secondary_index(
            index_name="horse_id-index",
            partition_key=dynamodb.Attribute(
                name="horse_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="race_date", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # horses テーブル（PK: horse_id, SK: sk）
        self.horses_table = dynamodb.Table(
            self,
            "HorsesTable",
            table_name="baken-kaigi-horses",
            partition_key=dynamodb.Attribute(
                name="horse_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # jockeys テーブル（PK: jockey_id, SK: sk）
        self.jockeys_table = dynamodb.Table(
            self,
            "JockeysTable",
            table_name="baken-kaigi-jockeys",
            partition_key=dynamodb.Attribute(
                name="jockey_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # trainers テーブル（PK: trainer_id, SK: sk）
        self.trainers_table = dynamodb.Table(
            self,
            "TrainersTable",
            table_name="baken-kaigi-trainers",
            partition_key=dynamodb.Attribute(
                name="trainer_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )
```

**Step 2: app.py にスタック追加**

Modify: `cdk/app.py` — `HrdbTablesStack` をインポートしてインスタンス化。

**Step 3: CDK synth で確認**

Run: `cd cdk && npx cdk synth baken-kaigi-hrdb-tables --context jravan=true 2>&1 | head -50`
Expected: CloudFormation テンプレートが出力される（DynamoDB テーブル5個 + GSI 1個）

**Step 4: Commit**

```bash
git add cdk/stacks/hrdb_tables_stack.py cdk/app.py
git commit -m "feat: HRDB移行用DynamoDBテーブル5個のCDKスタック追加"
```

---

### Task 3: HRDB→DynamoDB変換ユーティリティ + テスト

HRDB-APIのCSVカラム名をDynamoDBアイテムに変換するマッピング関数。
RACEMST/RACEDTLのカラム名は HRDB のFirebird DBスキーマに従う。

**Files:**
- Create: `backend/src/infrastructure/clients/hrdb_mapper.py`
- Create: `backend/tests/infrastructure/clients/test_hrdb_mapper.py`

**Step 1: Write the failing test**

```python
# backend/tests/infrastructure/clients/test_hrdb_mapper.py
"""HRDB→DynamoDBマッピングのテスト."""
import pytest

from src.infrastructure.clients.hrdb_mapper import (
    map_racemst_to_race_item,
    map_racedtl_to_runner_item,
    map_horse_to_horse_item,
    map_jky_to_jockey_item,
    map_trnr_to_trainer_item,
)


class TestMapRacemstToRaceItem:
    def test_正常系_RACEMSTレコードをracesテーブルアイテムに変換する(self):
        row = {
            "OPDT": "20260215",
            "RCOURSECD": "06",
            "RNO": "11",
            "RNAME": "フェブラリーS",
            "TRACKCD": "23",
            "KYORI": "1600",
            "TENKO": "1",
            "SHIBA_DART_CD": "2",
            "BABA": "1",
            "TOSU": "16",
            "GRADECD": "1",
            "JYOKENCD": "A3",
            "HTIME": "1540",
        }
        item = map_racemst_to_race_item(row)
        assert item["race_date"] == "20260215"
        assert item["race_id"] == "20260215_06_11"
        assert item["race_name"] == "フェブラリーS"
        assert item["distance"] == 1600
        assert item["horse_count"] == 16


class TestMapRacedtlToRunnerItem:
    def test_正常系_RACEDTLレコードをrunnersテーブルアイテムに変換する(self):
        row = {
            "OPDT": "20260215",
            "RCOURSECD": "06",
            "RNO": "11",
            "UMABAN": "3",
            "BAMEI": "テスト馬",
            "BLDNO": "2020100001",
            "JKYCD": "01234",
            "JKYNAME": "テスト騎手",
            "TRNRCD": "05678",
            "ODDS": "5.6",
            "NINKI": "2",
            "WAKUBAN": "2",
            "FUTAN": "57.0",
            "KAKUTEI": "1",
            "TIME": "1335",
            "AGARI3F": "345",
        }
        item = map_racedtl_to_runner_item(row)
        assert item["race_id"] == "20260215_06_11"
        assert item["horse_number"] == 3
        assert item["horse_name"] == "テスト馬"
        assert item["horse_id"] == "2020100001"
        assert item["jockey_id"] == "01234"
        assert item["odds"] == "5.6"
        assert item["finish_position"] == 1
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/infrastructure/clients/test_hrdb_mapper.py -v`
Expected: FAIL with "ImportError"

**Step 3: Write minimal implementation**

```python
# backend/src/infrastructure/clients/hrdb_mapper.py
"""HRDB CSVカラム→DynamoDBアイテム変換."""


def _make_race_id(opdt: str, rcoursecd: str, rno: str) -> str:
    """レースIDを生成する."""
    return f"{opdt}_{rcoursecd}_{int(rno):02d}"


def map_racemst_to_race_item(row: dict) -> dict:
    """RACEMSTレコードをracesテーブルアイテムに変換する."""
    opdt = row["OPDT"]
    race_id = _make_race_id(opdt, row["RCOURSECD"], row["RNO"])
    return {
        "race_date": opdt,
        "race_id": race_id,
        "race_number": int(row.get("RNO", "0")),
        "race_name": row.get("RNAME", ""),
        "venue_code": row.get("RCOURSECD", ""),
        "track_code": row.get("TRACKCD", ""),
        "distance": int(row.get("KYORI", "0")),
        "track_condition": row.get("BABA", ""),
        "horse_count": int(row.get("TOSU", "0")),
        "grade_code": row.get("GRADECD", ""),
        "condition_code": row.get("JYOKENCD", ""),
        "start_time": row.get("HTIME", ""),
    }


def map_racedtl_to_runner_item(row: dict) -> dict:
    """RACEDTLレコードをrunnersテーブルアイテムに変換する."""
    opdt = row["OPDT"]
    race_id = _make_race_id(opdt, row["RCOURSECD"], row["RNO"])
    return {
        "race_id": race_id,
        "race_date": opdt,
        "horse_number": int(row.get("UMABAN", "0")),
        "horse_name": row.get("BAMEI", ""),
        "horse_id": row.get("BLDNO", ""),
        "jockey_id": row.get("JKYCD", ""),
        "jockey_name": row.get("JKYNAME", ""),
        "trainer_id": row.get("TRNRCD", ""),
        "odds": row.get("ODDS", ""),
        "popularity": int(row.get("NINKI", "0")),
        "waku_ban": int(row.get("WAKUBAN", "0")),
        "weight_carried": row.get("FUTAN", ""),
        "finish_position": int(row.get("KAKUTEI", "0")),
        "time": row.get("TIME", ""),
        "last_3f": row.get("AGARI3F", ""),
    }


def map_horse_to_horse_item(row: dict) -> dict:
    """HORSEレコードをhorsesテーブルアイテムに変換する."""
    return {
        "horse_id": row.get("BLDNO", ""),
        "sk": "info",
        "horse_name": row.get("BAMEI", ""),
        "sire_name": row.get("FTNAME", ""),
        "dam_name": row.get("MTNAME", ""),
        "broodmare_sire": row.get("BMSTNAME", ""),
        "birth_year": row.get("BNEN", ""),
        "sex": row.get("SEX", ""),
        "coat_color": row.get("KEIRO", ""),
    }


def map_jky_to_jockey_item(row: dict) -> dict:
    """JKYレコードをjockeysテーブルアイテムに変換する."""
    return {
        "jockey_id": row.get("JKYCD", ""),
        "sk": "info",
        "jockey_name": row.get("JKYNAME", ""),
        "jockey_name_kana": row.get("JKYKANA", ""),
        "affiliation": row.get("SHOZOKU", ""),
    }


def map_trnr_to_trainer_item(row: dict) -> dict:
    """TRNRレコードをtrainersテーブルアイテムに変換する."""
    return {
        "trainer_id": row.get("TRNRCD", ""),
        "sk": "info",
        "trainer_name": row.get("TRNRNAME", ""),
        "trainer_name_kana": row.get("TRNRKANA", ""),
        "affiliation": row.get("SHOZOKU", ""),
    }
```

**Step 4: Run tests**

Run: `cd backend && uv run pytest tests/infrastructure/clients/test_hrdb_mapper.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/infrastructure/clients/hrdb_mapper.py backend/tests/infrastructure/clients/test_hrdb_mapper.py
git commit -m "feat: HRDB CSVカラム→DynamoDBアイテム変換マッパー"
```

---

### Task 4: バッチLambda — レース取得（hrdb-races-scraper）

**Files:**
- Create: `backend/batch/hrdb_races_scraper.py`
- Create: `backend/tests/batch/test_hrdb_races_scraper.py`

**Step 1: Write the failing test**

```python
# backend/tests/batch/test_hrdb_races_scraper.py
"""HRDB レース取得バッチのテスト."""
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from batch.hrdb_races_scraper import handler


@mock_aws
class TestHrdbRacesScraper:
    def _setup_table(self):
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = dynamodb.create_table(
            TableName="baken-kaigi-races",
            KeySchema=[
                {"AttributeName": "race_date", "KeyType": "HASH"},
                {"AttributeName": "race_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "race_date", "AttributeType": "S"},
                {"AttributeName": "race_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        return table

    @patch.dict("os.environ", {
        "RACES_TABLE_NAME": "baken-kaigi-races",
        "GAMBLE_OS_SECRET_ID": "test-secret",
    })
    @patch("batch.hrdb_races_scraper._get_hrdb_client")
    def test_正常系_HRDB結果をDynamoDBに書き込む(self, mock_get_client):
        table = self._setup_table()

        mock_client = MagicMock()
        mock_client.query.return_value = [
            {
                "OPDT": "20260215",
                "RCOURSECD": "06",
                "RNO": "11",
                "RNAME": "フェブラリーS",
                "TRACKCD": "23",
                "KYORI": "1600",
                "BABA": "1",
                "TOSU": "16",
                "GRADECD": "1",
                "JYOKENCD": "A3",
                "HTIME": "1540",
            },
        ]
        mock_get_client.return_value = mock_client

        handler({"offset_days": 0}, None)

        items = table.scan()["Items"]
        assert len(items) == 1
        assert items[0]["race_id"] == "20260215_06_11"
        assert items[0]["race_name"] == "フェブラリーS"
```

**Step 2:** Run test → FAIL

**Step 3: Write minimal implementation**

```python
# backend/batch/hrdb_races_scraper.py
"""HRDB レース取得バッチ."""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3

from src.infrastructure.clients.hrdb_client import HrdbClient
from src.infrastructure.clients.hrdb_mapper import map_racemst_to_race_item

logger = logging.getLogger(__name__)
JST = timezone(timedelta(hours=9))


def _get_hrdb_client() -> HrdbClient:
    secret_id = os.environ["GAMBLE_OS_SECRET_ID"]
    client = boto3.client("secretsmanager", region_name="ap-northeast-1")
    secret = json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])
    return HrdbClient(
        club_id=secret["club_id"],
        club_password=secret["club_password"],
        api_domain=secret["api_domain"],
    )


def handler(event: dict, context) -> dict:
    offset_days = event.get("offset_days", 1)
    target_date = datetime.now(JST) + timedelta(days=offset_days)
    date_str = target_date.strftime("%Y%m%d")

    logger.info("Fetching races for date: %s", date_str)

    hrdb_client = _get_hrdb_client()
    rows = hrdb_client.query(f"SELECT * FROM RACEMST WHERE OPDT = '{date_str}'")

    table_name = os.environ["RACES_TABLE_NAME"]
    table = boto3.resource("dynamodb", region_name="ap-northeast-1").Table(table_name)

    with table.batch_writer() as batch:
        for row in rows:
            item = map_racemst_to_race_item(row)
            batch.put_item(Item=item)

    logger.info("Wrote %d races to %s", len(rows), table_name)
    return {"status": "ok", "count": len(rows)}
```

**Step 4:** Run tests → PASS
**Step 5:** Commit: `feat: HRDBレース取得バッチLambda`

---

### Task 5: バッチLambda — 出走馬取得（hrdb-runners-scraper）

Task 4と同じパターン。`RACEDTL` → `runners` テーブル。

**Files:**
- Create: `backend/batch/hrdb_runners_scraper.py`
- Create: `backend/tests/batch/test_hrdb_runners_scraper.py`

SQL: `SELECT * FROM RACEDTL WHERE OPDT = '{date}'`
マッパー: `map_racedtl_to_runner_item`
テーブル: `baken-kaigi-runners`

Task 4と同じTDDフロー（テスト→実装→確認→コミット）。

**Commit:** `feat: HRDB出走馬取得バッチLambda`

---

### Task 6: バッチLambda — 馬・騎手・調教師マスタ同期

3つのマスタ同期Lambda。runnersテーブルから未取得のIDを抽出し、HRDBに問い合わせる。

**Files:**
- Create: `backend/batch/hrdb_horses_sync.py`
- Create: `backend/batch/hrdb_jockeys_sync.py`
- Create: `backend/batch/hrdb_trainers_sync.py`
- Create: `backend/tests/batch/test_hrdb_horses_sync.py`
- Create: `backend/tests/batch/test_hrdb_jockeys_sync.py`
- Create: `backend/tests/batch/test_hrdb_trainers_sync.py`

パターン:
1. `runners` テーブルをスキャンして `horse_id` / `jockey_id` / `trainer_id` を収集
2. 対応するマスタテーブルに存在しないIDをフィルタ
3. HRDB-API で `SELECT * FROM HORSE WHERE BLDNO IN (...)` 等を実行
4. 結果をマスタテーブルに書き込み

各Lambda: テスト→実装→確認→コミット。

**Commits:**
- `feat: HRDB馬マスタ同期バッチLambda`
- `feat: HRDB騎手マスタ同期バッチLambda`
- `feat: HRDB調教師マスタ同期バッチLambda`

---

### Task 7: バッチLambda — レース結果更新（hrdb-results-sync）

週次バッチで前週のレース結果（着順・タイム・上がり3F等）を更新。

**Files:**
- Create: `backend/batch/hrdb_results_sync.py`
- Create: `backend/tests/batch/test_hrdb_results_sync.py`

SQL: `SELECT * FROM RACEDTL WHERE OPDT BETWEEN '{from_date}' AND '{to_date}' AND KAKUTEI > 0`

**Commit:** `feat: HRDBレース結果更新バッチLambda`

---

### Task 8: CDK — バッチLambda + EventBridgeルール追加

**Files:**
- Modify: `cdk/stacks/batch_stack.py` — HRDB系Lambda 6個 + EventBridgeルール追加

追加するLambda:

| Lambda名 | ハンドラー | スケジュール |
|----------|----------|------------|
| `hrdb-races-scraper` | `batch.hrdb_races_scraper.handler` | 毎晩21:00 JST + 当日朝8:00 JST |
| `hrdb-runners-scraper` | `batch.hrdb_runners_scraper.handler` | 同上 |
| `hrdb-horses-sync` | `batch.hrdb_horses_sync.handler` | 毎晩22:00 JST |
| `hrdb-jockeys-sync` | `batch.hrdb_jockeys_sync.handler` | 毎晩22:10 JST |
| `hrdb-trainers-sync` | `batch.hrdb_trainers_sync.handler` | 毎晩22:20 JST |
| `hrdb-results-sync` | `batch.hrdb_results_sync.handler` | 毎週月曜 6:00 JST |

CDKパターンは既存のスクレイパーLambdaと同じ（`batch_deps_layer`, `backend_code`, `Duration.seconds(300)`, `memory_size=512`）。

IAM権限: 各Lambda に対応するDynamoDBテーブルの `grant_write_data` + runnersテーブルの `grant_read_data`（マスタ同期用）。
Secrets Manager: `gamble-os-credentials` シークレットの読み取り権限。

**Step 1:** CDK スタック修正
**Step 2:** `cd cdk && npx cdk synth --context jravan=true 2>&1 | head -50` で確認
**Step 3:** Commit: `feat: HRDBバッチLambda 6個のCDKリソース追加`

---

## Phase 2: データ層切り替え

### Task 9: DynamoDbRaceDataProvider — 基本メソッド群

`RaceDataProvider` の27メソッドをDynamoDB読み出しで実装する。motoでテスト。
まず基本的なレース・出走馬系6メソッドから。

**Files:**
- Create: `backend/src/infrastructure/providers/dynamodb_race_data_provider.py`
- Create: `backend/tests/infrastructure/providers/test_dynamodb_race_data_provider.py`

**対象メソッド（基本6メソッド）:**
1. `get_race(race_id)` → `races` テーブル query
2. `get_races_by_date(target_date, venue)` → `races` テーブル query
3. `get_runners(race_id)` → `runners` テーブル query
4. `get_race_weights(race_id)` → `runners` テーブル query
5. `get_race_dates(from_date, to_date)` → `races` テーブル scan
6. `get_race_results(race_id)` → `runners` テーブル query

**Step 1: Write the failing test（get_raceの例）**

```python
# backend/tests/infrastructure/providers/test_dynamodb_race_data_provider.py
"""DynamoDbRaceDataProvider のテスト."""
import boto3
import pytest
from moto import mock_aws

from src.domain.identifiers import RaceId
from src.infrastructure.providers.dynamodb_race_data_provider import (
    DynamoDbRaceDataProvider,
)


def _create_tables():
    """テスト用DynamoDBテーブルを作成する."""
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    dynamodb.create_table(
        TableName="baken-kaigi-races",
        KeySchema=[
            {"AttributeName": "race_date", "KeyType": "HASH"},
            {"AttributeName": "race_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "race_date", "AttributeType": "S"},
            {"AttributeName": "race_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamodb.create_table(
        TableName="baken-kaigi-runners",
        KeySchema=[
            {"AttributeName": "race_id", "KeyType": "HASH"},
            {"AttributeName": "horse_number", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "race_id", "AttributeType": "S"},
            {"AttributeName": "horse_number", "AttributeType": "N"},
            {"AttributeName": "horse_id", "AttributeType": "S"},
            {"AttributeName": "race_date", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[{
            "IndexName": "horse_id-index",
            "KeySchema": [
                {"AttributeName": "horse_id", "KeyType": "HASH"},
                {"AttributeName": "race_date", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )
    for table_name, pk_name in [
        ("baken-kaigi-horses", "horse_id"),
        ("baken-kaigi-jockeys", "jockey_id"),
        ("baken-kaigi-trainers", "trainer_id"),
    ]:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": pk_name, "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": pk_name, "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )


@mock_aws
class TestGetRace:
    def test_正常系_レースIDで検索して結果を返す(self):
        _create_tables()
        table = boto3.resource("dynamodb", region_name="ap-northeast-1").Table("baken-kaigi-races")
        table.put_item(Item={
            "race_date": "20260215",
            "race_id": "20260215_06_11",
            "race_number": 11,
            "race_name": "フェブラリーS",
            "venue_code": "06",
            "distance": 1600,
            "track_condition": "1",
            "horse_count": 16,
            "grade_code": "1",
            "start_time": "1540",
        })
        provider = DynamoDbRaceDataProvider(region_name="ap-northeast-1")
        result = provider.get_race(RaceId("20260215_06_11"))
        assert result is not None
        assert result.race_name == "フェブラリーS"
        assert result.distance == 1600

    def test_存在しないレースIDの場合Noneを返す(self):
        _create_tables()
        provider = DynamoDbRaceDataProvider(region_name="ap-northeast-1")
        result = provider.get_race(RaceId("99991231_99_99"))
        assert result is None
```

**Step 2-5:** TDDフロー
**Commit:** `feat: DynamoDbRaceDataProvider 基本6メソッド実装`

---

### Task 10: DynamoDbRaceDataProvider — 馬系メソッド群

**対象メソッド（馬関連8メソッド）:**
1. `get_past_performance(horse_id)` → `runners` テーブル horse_id-index
2. `get_horse_performances(horse_id, limit, track_type)` → `runners` テーブル horse_id-index
3. `get_pedigree(horse_id)` → `horses` テーブル get_item
4. `get_extended_pedigree(horse_id)` → `horses` テーブル get_item
5. `get_weight_history(horse_id, limit)` → `runners` テーブル horse_id-index
6. `get_course_aptitude(horse_id)` → `runners` テーブル horse_id-index で集計
7. `get_horse_training(horse_id, limit, days)` → HRDB未サポート、空データ返却
8. `get_jra_checksum(...)` → HRDB未サポート、None返却

TDDフロー。
**Commit:** `feat: DynamoDbRaceDataProvider 馬系8メソッド実装`

---

### Task 11: DynamoDbRaceDataProvider — 人物・統計系メソッド群

**対象メソッド（13メソッド）:**
1. `get_jockey_stats` → `runners` テーブル集計
2. `get_jockey_info` → `jockeys` テーブル get_item
3. `get_jockey_stats_detail` → `runners` テーブル集計
4. `get_trainer_info` → `trainers` テーブル get_item
5. `get_trainer_stats_detail` → `runners` テーブル集計
6. `get_stallion_offspring_stats` → `horses` + `runners` テーブル結合集計
7. `get_owner_info` → `horses` テーブル検索
8. `get_owner_stats` → `horses` + `runners` テーブル結合
9. `get_breeder_info` → `horses` テーブル検索
10. `get_breeder_stats` → `horses` + `runners` テーブル結合
11. `get_odds_history` → Phase 3 で RealtimeOddsClient に委譲（暫定空データ）
12. `get_past_race_stats` → `runners` テーブル集計
13. `get_gate_position_stats` → `runners` テーブル集計

TDDフロー。
**Commit:** `feat: DynamoDbRaceDataProvider 人物・統計系13メソッド実装`

---

### Task 12: Provider切り替えファクトリ

環境変数 `RACE_DATA_PROVIDER` で `jravan` / `dynamodb` を切り替えるファクトリ。

**Files:**
- Create: `backend/src/infrastructure/providers/race_data_provider_factory.py`
- Create: `backend/tests/infrastructure/providers/test_race_data_provider_factory.py`
- Modify: ハンドラー層のProvider生成箇所

```python
# backend/src/infrastructure/providers/race_data_provider_factory.py
"""RaceDataProvider ファクトリ."""
import os

from src.domain.ports.race_data_provider import RaceDataProvider


def create_race_data_provider() -> RaceDataProvider:
    """環境変数に基づいてRaceDataProviderを生成する."""
    provider_type = os.environ.get("RACE_DATA_PROVIDER", "jravan")
    if provider_type == "dynamodb":
        from src.infrastructure.providers.dynamodb_race_data_provider import (
            DynamoDbRaceDataProvider,
        )
        return DynamoDbRaceDataProvider()
    else:
        from src.infrastructure.providers.jravan_race_data_provider import (
            JraVanRaceDataProvider,
        )
        return JraVanRaceDataProvider()
```

TDDフロー。
**Commit:** `feat: RaceDataProvider切り替えファクトリ`

---

### Task 13: AgentCoreツール — DynamoDB読み出し共通モジュール

`jravan_client.py` の `cached_get()` を置き換える DynamoDB 読み出しモジュール。

**Files:**
- Create: `backend/agentcore/tools/dynamodb_client.py`
- Create: `backend/tests/agentcore/test_dynamodb_client.py`

```python
# backend/agentcore/tools/dynamodb_client.py
"""DynamoDB読み出しクライアント（AgentCoreツール用）."""
import os
import boto3
from boto3.dynamodb.conditions import Key

_dynamodb = None

def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    return _dynamodb

def get_race(race_id: str) -> dict | None:
    race_date = race_id.split("_")[0]
    table = _get_dynamodb().Table(os.environ.get("RACES_TABLE_NAME", "baken-kaigi-races"))
    response = table.get_item(Key={"race_date": race_date, "race_id": race_id})
    return response.get("Item")

def get_runners(race_id: str) -> list[dict]:
    table = _get_dynamodb().Table(os.environ.get("RUNNERS_TABLE_NAME", "baken-kaigi-runners"))
    response = table.query(KeyConditionExpression=Key("race_id").eq(race_id))
    return response.get("Items", [])

def get_horse_performances(horse_id: str, limit: int = 20) -> list[dict]:
    table = _get_dynamodb().Table(os.environ.get("RUNNERS_TABLE_NAME", "baken-kaigi-runners"))
    response = table.query(
        IndexName="horse_id-index",
        KeyConditionExpression=Key("horse_id").eq(horse_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return response.get("Items", [])

def get_horse(horse_id: str) -> dict | None:
    table = _get_dynamodb().Table(os.environ.get("HORSES_TABLE_NAME", "baken-kaigi-horses"))
    response = table.get_item(Key={"horse_id": horse_id, "sk": "info"})
    return response.get("Item")

def get_jockey(jockey_id: str) -> dict | None:
    table = _get_dynamodb().Table(os.environ.get("JOCKEYS_TABLE_NAME", "baken-kaigi-jockeys"))
    response = table.get_item(Key={"jockey_id": jockey_id, "sk": "info"})
    return response.get("Item")

def get_trainer(trainer_id: str) -> dict | None:
    table = _get_dynamodb().Table(os.environ.get("TRAINERS_TABLE_NAME", "baken-kaigi-trainers"))
    response = table.get_item(Key={"trainer_id": trainer_id, "sk": "info"})
    return response.get("Item")
```

TDDフロー（moto使用）。
**Commit:** `feat: AgentCoreツール用DynamoDB読み出しクライアント`

---

### Task 14: AgentCoreツール — race_data.py をDynamoDB化

**Files:**
- Modify: `backend/agentcore/tools/race_data.py`
- Modify: `backend/tests/agentcore/test_race_data.py`

**Before:**
```python
from .jravan_client import cached_get, get_api_url
def _fetch_race_detail(race_id: str) -> dict:
    response = cached_get(f"{get_api_url()}/races/{race_id}")
    response.raise_for_status()
    return response.json()
```

**After:**
```python
from . import dynamodb_client
def _fetch_race_detail(race_id: str) -> dict:
    race = dynamodb_client.get_race(race_id)
    runners = dynamodb_client.get_runners(race_id)
    return {"race": race or {}, "runners": runners}
```

TDDフロー。
**Commit:** `refactor: race_data.py をDynamoDB読み出しに移行`

---

### Task 15: AgentCoreツール — 残り16ツールをDynamoDB化

17ツールのうち `race_data.py` はTask 14で完了。残り16ツールを同じパターンで移行。

**移行パターン:** 各ツールの `_get_race_info()`, `_get_performances()` 等のプライベート関数で `requests.get(f"{get_api_url()}/...")` → `dynamodb_client` の関数に置き換え。

| ツール | 置き換えるAPI呼び出し |
|-------|---------------------|
| `odds_analysis.py` | `/races/{id}/odds-history` → Phase 3で対応、暫定空データ |
| `course_aptitude_analysis.py` | `/horses/{id}/course-aptitude` → `get_horse_performances()` で集計 |
| `race_comprehensive_analysis.py` | 複数エンドポイント → `dynamodb_client` 各関数 |
| `bet_combinations.py` | `/races/{id}/runners`, `/horses/{id}/performances` → `dynamodb_client` |
| `track_change_analysis.py` | `/races/{id}`, `/races?date=...` → `dynamodb_client` |
| `track_condition_analysis.py` | `/races/{id}`, `/horses/{id}/performances` → `dynamodb_client` |
| `last_race_analysis.py` | `/races/{id}`, `/horses/{id}/performances` → `dynamodb_client` |
| `momentum_analysis.py` | `/horses/{id}/performances` → `dynamodb_client` |
| `scratch_impact_analysis.py` | `/races/{id}`, `/races/{id}/runners` → `dynamodb_client` |
| `time_analysis.py` | `/races/{id}`, `/horses/{id}/performances` → `dynamodb_client` |
| `bet_probability_analysis.py` | `/races/{id}`, `/statistics/past-races` → `dynamodb_client` |
| `class_analysis.py` | `/races/{id}`, `/horses/{id}/performances` → `dynamodb_client` |
| `distance_change_analysis.py` | `/races/{id}`, `/horses/{id}/performances` → `dynamodb_client` |
| `rotation_analysis.py` | `/races/{id}`, `/horses/{id}/performances` → `dynamodb_client` |
| `weight_analysis.py` | `/horses/{id}/performances` → `dynamodb_client` |
| `past_performance.py` | `/horses/{id}/performances` → `dynamodb_client` |

3-5ツールごとにコミット。

**Commits:**
- `refactor: AgentCoreツール(bet系)をDynamoDB読み出しに移行`
- `refactor: AgentCoreツール(分析系)をDynamoDB読み出しに移行`
- `refactor: AgentCoreツール(成績・統計系)をDynamoDB読み出しに移行`

---

### Task 16: keibagrantスクレイパー廃止

**Files:**
- Delete: `backend/batch/keibagrant_scraper.py`
- Modify: `cdk/stacks/batch_stack.py` — keibagrant関連のLambda + EventBridgeルール削除

**Commit:** `chore: keibagrantスクレイパー廃止（HRDBで代替）`

---

## Phase 3: IPAT・オッズ移行

### Task 17: GambleOsIpatGateway — 実装 + テスト

`IpatGateway` インターフェースの新実装。GAMBLE-OS JRA-IPAT投票APIを呼び出す。

**Files:**
- Create: `backend/src/infrastructure/providers/gambleos_ipat_gateway.py`
- Create: `backend/tests/infrastructure/providers/test_gambleos_ipat_gateway.py`

**API仕様:**
- ベースURL: `https://api.gamble-os.net`
- 投票: `POST /systems/ip-bet-kb` (tncid, tncpw, opdt, rcoursecd, rno, denomination, method, multi, number, bet_price)
- 残高: `POST /systems/ip-balance` (tncid, tncpw, inet_id, subscriber_no, pin, pars_no)
- レスポンス: `{"ret": "0", "msg": "", "results": [...]}`

TDDフロー。
**Commit:** `feat: GambleOsIpatGateway実装`

---

### Task 18: IpatGateway切り替えファクトリ

**Files:**
- Create: `backend/src/infrastructure/providers/ipat_gateway_factory.py`
- Create: `backend/tests/infrastructure/providers/test_ipat_gateway_factory.py`

TDDフロー。
**Commit:** `feat: IpatGateway切り替えファクトリ`

---

### Task 19: RealtimeOddsClient — 実装 + テスト

**Files:**
- Create: `backend/src/infrastructure/clients/realtime_odds_client.py`
- Create: `backend/tests/infrastructure/clients/test_realtime_odds_client.py`

TDDフロー。
**Commit:** `feat: RealtimeOddsClient実装`

---

### Task 20: オッズ系統合

Task 15で暫定空データにした `odds_analysis.py` と Task 11の `get_odds_history` を `RealtimeOddsClient` に接続。

**Files:**
- Modify: `backend/agentcore/tools/odds_analysis.py`
- Modify: `backend/src/infrastructure/providers/dynamodb_race_data_provider.py`

TDDフロー。
**Commit:** `feat: odds_analysis.py と get_odds_history をリアルタイムオッズAPIに接続`

---

## Phase 4: EC2廃止・クリーンアップ

### Task 21: 旧コード削除

**Files:**
- Delete: `backend/agentcore/tools/jravan_client.py`
- Delete: `backend/agentcore/tools/api_cache.py`
- Delete: `backend/src/infrastructure/providers/jravan_race_data_provider.py`
- Delete: `backend/src/infrastructure/providers/jravan_ipat_gateway.py`
- Delete: 対応テストファイル

**Step 1:** grep で参照箇所がないことを確認
**Step 2:** ファイル削除
**Step 3:** 全テスト実行→PASS確認

**Commit:** `chore: JRA-VAN API旧コード削除`

---

### Task 22: CDK — EC2/VPC関連リソース削除

**Files:**
- Delete: `cdk/stacks/jravan_server_stack.py`
- Modify: `cdk/app.py`
- Modify: `cdk/stacks/batch_stack.py` — VPC関連パラメータ削除

**重要:** 実際のCDKデプロイは十分なテスト後に手動実行。

**Commit:** `chore: EC2/VPC/JRA-VAN CDKリソース削除`

---

### Task 23: jravan-api ディレクトリ削除 + ファクトリデフォルト切り替え

**Files:**
- Delete: `jravan-api/` ディレクトリ全体
- Modify: `race_data_provider_factory.py` — デフォルト `dynamodb`
- Modify: `ipat_gateway_factory.py` — デフォルト `gambleos`

**Step 1:** 全テスト実行→PASS確認
**Step 2:** Commit

**Commits:**
- `chore: jravan-apiディレクトリ削除（HRDB移行完了）`
- `feat: Provider/Gatewayのデフォルトを新実装に切り替え`

---

## 補足: テスト実行コマンド

```bash
# 全テスト
cd backend && uv run pytest

# 特定ファイル
cd backend && uv run pytest tests/infrastructure/clients/test_hrdb_client.py -v

# 特定テストクラス
cd backend && uv run pytest tests/infrastructure/providers/test_dynamodb_race_data_provider.py::TestGetRace -v

# カバレッジ付き
cd backend && uv run pytest --cov=src --cov=batch --cov-report=term-missing
```

## 補足: HRDB-APIカラム名対応表

| HRDB カラム | DynamoDB フィールド | テーブル |
|------------|-------------------|---------|
| OPDT | race_date | races, runners |
| RCOURSECD | venue_code | races |
| RNO | race_number | races |
| RNAME | race_name | races |
| KYORI | distance | races |
| TOSU | horse_count | races |
| GRADECD | grade_code | races |
| UMABAN | horse_number | runners |
| BAMEI | horse_name | runners, horses |
| BLDNO | horse_id | runners, horses |
| JKYCD | jockey_id | runners, jockeys |
| JKYNAME | jockey_name | runners, jockeys |
| TRNRCD | trainer_id | runners, trainers |
| ODDS | odds | runners |
| NINKI | popularity | runners |
| KAKUTEI | finish_position | runners |
| TIME | time | runners |
| AGARI3F | last_3f | runners |
| FTNAME | sire_name | horses |
| MTNAME | dam_name | horses |
| BMSTNAME | broodmare_sire | horses |
