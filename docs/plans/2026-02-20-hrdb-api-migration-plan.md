# HRDB-API移行 Phase 1 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** HRDB-APIクライアントとバッチLambdaを実装し、レース・出走馬データをDynamoDBに蓄積する基盤を構築する

**Architecture:** HRDB-APIは非同期SQLクエリAPI（送信→ポーリング→CSV取得）。バッチLambdaがEventBridgeスケジュールでHRDB-APIからデータを取得し、DynamoDBに書き込む。既存のAI予測スクレイパーと同じパターンを踏襲。

**Tech Stack:** Python 3.12, boto3, requests, AWS CDK (TypeScript→Python), DynamoDB, EventBridge, Secrets Manager

**Design Doc:** `docs/plans/2026-02-13-hrdb-api-migration-design.md`

---

## Task 1: HrdbClient — HRDB-APIクライアント

**Files:**
- Create: `backend/batch/hrdb_client.py`
- Test: `backend/tests/batch/test_hrdb_client.py`

### Step 1: テスト作成 — 正常系クエリフロー

`test_hrdb_client.py` にクエリ送信→状態確認→CSV取得の一連フローをテスト。

```python
"""HRDB-APIクライアントのテスト."""
import csv
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from batch.hrdb_client import HrdbClient


class TestQuery:
    """query() メソッドのテスト."""

    def _make_client(self):
        return HrdbClient(
            club_id="test@example.com",
            club_password="testpass",
        )

    @patch("batch.hrdb_client.requests.post")
    @patch("batch.hrdb_client.requests.get")
    @patch("batch.hrdb_client.time.sleep")
    def test_正常なクエリフロー(self, mock_sleep, mock_get, mock_post):
        # 1. クエリ送信 → qid取得
        submit_resp = MagicMock()
        submit_resp.json.return_value = {
            "ret": 0, "msg": "ok.",
            "ret1": "20260220120000001", "msg1": "ok.",
        }
        submit_resp.raise_for_status = MagicMock()

        # 2. 状態確認 → 処理中(1) → 完了(2)
        state_resp_processing = MagicMock()
        state_resp_processing.json.return_value = {
            "ret": 0, "msg": "ok.", "ret1": "1", "msg1": "ok.",
        }
        state_resp_processing.raise_for_status = MagicMock()

        state_resp_done = MagicMock()
        state_resp_done.json.return_value = {
            "ret": 0, "msg": "ok.", "ret1": "2", "msg1": "ok.",
        }
        state_resp_done.raise_for_status = MagicMock()

        # 3. URL取得
        url_resp = MagicMock()
        url_resp.json.return_value = {
            "ret": 0, "msg": "ok.",
            "ret1": "https://api.gamble-os.net/systems/csv?url=test.csv",
            "msg1": "ok.",
        }
        url_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [submit_resp, state_resp_processing, state_resp_done, url_resp]

        # 4. CSV取得 (Shift-JISエンコード)
        csv_content = "COL1,COL2\nval1,val2\nval3,val4".encode("shift_jis")
        csv_resp = MagicMock()
        csv_resp.content = csv_content
        csv_resp.raise_for_status = MagicMock()
        mock_get.return_value = csv_resp

        client = self._make_client()
        result = client.query("SELECT COL1, COL2 FROM TEST;")

        assert result == [
            {"COL1": "val1", "COL2": "val2"},
            {"COL1": "val3", "COL2": "val4"},
        ]
        assert mock_post.call_count == 4  # submit + 2 state + geturl
        assert mock_get.call_count == 1   # csv download

    @patch("batch.hrdb_client.requests.post")
    def test_認証エラーで例外(self, mock_post):
        resp = MagicMock()
        resp.json.return_value = {"ret": -200, "msg": "Authentication failure."}
        resp.raise_for_status = MagicMock()
        mock_post.return_value = resp

        client = self._make_client()
        with pytest.raises(RuntimeError, match="Authentication failure"):
            client.query("SELECT 1;")

    @patch("batch.hrdb_client.requests.post")
    def test_ライセンスエラーで例外(self, mock_post):
        resp = MagicMock()
        resp.json.return_value = {"ret": -203, "msg": "Authentication no license error."}
        resp.raise_for_status = MagicMock()
        mock_post.return_value = resp

        client = self._make_client()
        with pytest.raises(RuntimeError, match="no license"):
            client.query("SELECT 1;")

    @patch("batch.hrdb_client.requests.post")
    @patch("batch.hrdb_client.requests.get")
    @patch("batch.hrdb_client.time.sleep")
    def test_SQLエラーで例外(self, mock_sleep, mock_get, mock_post):
        submit_resp = MagicMock()
        submit_resp.json.return_value = {
            "ret": 0, "msg": "ok.",
            "ret1": "qid001", "msg1": "ok.",
        }
        submit_resp.raise_for_status = MagicMock()

        state_resp = MagicMock()
        state_resp.json.return_value = {
            "ret": 0, "msg": "ok.", "ret1": "6", "msg1": "ok.",
        }
        state_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [submit_resp, state_resp]

        client = self._make_client()
        with pytest.raises(RuntimeError, match="SQL error"):
            client.query("SELECT * FROM NONEXISTENT;")

    @patch("batch.hrdb_client.requests.post")
    @patch("batch.hrdb_client.requests.get")
    @patch("batch.hrdb_client.time.sleep")
    def test_CSVの空白がトリムされる(self, mock_sleep, mock_get, mock_post):
        submit_resp = MagicMock()
        submit_resp.json.return_value = {
            "ret": 0, "msg": "ok.", "ret1": "qid001", "msg1": "ok.",
        }
        submit_resp.raise_for_status = MagicMock()

        state_resp = MagicMock()
        state_resp.json.return_value = {
            "ret": 0, "msg": "ok.", "ret1": "2", "msg1": "ok.",
        }
        state_resp.raise_for_status = MagicMock()

        url_resp = MagicMock()
        url_resp.json.return_value = {
            "ret": 0, "msg": "ok.",
            "ret1": "https://example.com/test.csv", "msg1": "ok.",
        }
        url_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [submit_resp, state_resp, url_resp]

        # HRDB-APIのCSVはカラム値が大量の空白でパディングされる
        csv_content = '"NAME"\n"テスト                    "\n'.encode("shift_jis")
        csv_resp = MagicMock()
        csv_resp.content = csv_content
        csv_resp.raise_for_status = MagicMock()
        mock_get.return_value = csv_resp

        client = self._make_client()
        result = client.query("SELECT NAME FROM TEST;")

        assert result == [{"NAME": "テスト"}]

    @patch("batch.hrdb_client.requests.post")
    @patch("batch.hrdb_client.time.sleep")
    def test_ポーリングタイムアウトで例外(self, mock_sleep, mock_post):
        submit_resp = MagicMock()
        submit_resp.json.return_value = {
            "ret": 0, "msg": "ok.", "ret1": "qid001", "msg1": "ok.",
        }
        submit_resp.raise_for_status = MagicMock()

        # ずっと処理中(1)を返す
        state_resp = MagicMock()
        state_resp.json.return_value = {
            "ret": 0, "msg": "ok.", "ret1": "1", "msg1": "ok.",
        }
        state_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [submit_resp] + [state_resp] * 100

        client = self._make_client()
        with pytest.raises(TimeoutError, match="poll"):
            client.query("SELECT 1;")


class TestQueryDual:
    """query_dual() — 2クエリ同時送信のテスト."""

    def _make_client(self):
        return HrdbClient(club_id="test@example.com", club_password="testpass")

    @patch("batch.hrdb_client.requests.post")
    @patch("batch.hrdb_client.requests.get")
    @patch("batch.hrdb_client.time.sleep")
    def test_2クエリ同時送信と結果取得(self, mock_sleep, mock_get, mock_post):
        submit_resp = MagicMock()
        submit_resp.json.return_value = {
            "ret": 0, "msg": "ok.",
            "ret1": "qid001", "msg1": "ok.",
            "ret2": "qid002", "msg2": "ok.",
        }
        submit_resp.raise_for_status = MagicMock()

        state_resp = MagicMock()
        state_resp.json.return_value = {
            "ret": 0, "msg": "ok.", "ret1": "2", "msg1": "ok.",
        }
        state_resp.raise_for_status = MagicMock()

        url_resp = MagicMock()
        url_resp.json.return_value = {
            "ret": 0, "msg": "ok.",
            "ret1": "https://example.com/r1.csv", "msg1": "ok.",
            "ret2": "https://example.com/r2.csv", "msg2": "ok.",
        }
        url_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [submit_resp, state_resp, url_resp]

        csv1 = "A\n1\n".encode("shift_jis")
        csv2 = "B\n2\n".encode("shift_jis")
        csv_resp1 = MagicMock(content=csv1)
        csv_resp1.raise_for_status = MagicMock()
        csv_resp2 = MagicMock(content=csv2)
        csv_resp2.raise_for_status = MagicMock()
        mock_get.side_effect = [csv_resp1, csv_resp2]

        client = self._make_client()
        r1, r2 = client.query_dual("SELECT A FROM T1;", "SELECT B FROM T2;")

        assert r1 == [{"A": "1"}]
        assert r2 == [{"B": "2"}]
```

**Run:** `cd backend && uv run pytest tests/batch/test_hrdb_client.py -v`
**Expected:** FAIL — `ModuleNotFoundError: No module named 'batch.hrdb_client'`

### Step 2: HrdbClient実装

```python
"""GAMBLE-OS HRDB-API (HorseRacing DataBase API) クライアント."""
import csv
import io
import logging
import time

import requests

logger = logging.getLogger(__name__)

API_URL = "https://api.gamble-os.net/systems/hrdb"
POLL_INTERVAL_SECONDS = 3
MAX_POLL_ATTEMPTS = 60


class HrdbClient:
    """HRDB-API非同期クエリクライアント.

    ワークフロー: SQL送信 → ポーリング → CSV取得 → パース
    """

    def __init__(self, club_id: str, club_password: str):
        self._club_id = club_id
        self._club_password = club_password

    def _auth_params(self) -> dict:
        return {"tncid": self._club_id, "tncpw": self._club_password}

    def _submit(self, params: dict) -> dict:
        resp = requests.post(API_URL, data=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data["ret"] < 0:
            raise RuntimeError(f"HRDB-API error: {data['msg']} (ret={data['ret']})")
        return data

    def _poll_until_done(self, qid: str) -> None:
        for _ in range(MAX_POLL_ATTEMPTS):
            time.sleep(POLL_INTERVAL_SECONDS)
            data = self._submit({
                **self._auth_params(),
                "prccd": "state",
                "qid1": qid,
            })
            state = data["ret1"]
            if state == "2":  # 完了
                return
            if state == "6":  # SQLエラー
                raise RuntimeError(f"HRDB-API SQL error for qid={qid}")
            if state not in ("0", "1"):  # 0=待機, 1=処理中
                raise RuntimeError(f"HRDB-API unexpected state={state} for qid={qid}")
        raise TimeoutError(f"HRDB-API poll timeout for qid={qid}")

    def _get_result_url(self, qid: str) -> str:
        data = self._submit({
            **self._auth_params(),
            "prccd": "geturl",
            "qid1": qid,
        })
        return data["ret1"]

    def _download_csv(self, url: str) -> list[dict]:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        text = resp.content.decode("shift_jis")
        reader = csv.DictReader(io.StringIO(text))
        return [{k: v.strip() for k, v in row.items()} for row in reader]

    def query(self, sql: str) -> list[dict]:
        """SQLクエリを実行し結果をlist[dict]で返す."""
        logger.info("HRDB query: %s", sql[:100])
        data = self._submit({
            **self._auth_params(),
            "prccd": "select",
            "cmd1": sql,
            "format": "json",
        })
        qid = data["ret1"]
        self._poll_until_done(qid)
        url = self._get_result_url(qid)
        return self._download_csv(url)

    def query_dual(self, sql1: str, sql2: str) -> tuple[list[dict], list[dict]]:
        """2つのSQLクエリを同時送信し結果を返す."""
        logger.info("HRDB dual query: %s / %s", sql1[:80], sql2[:80])
        data = self._submit({
            **self._auth_params(),
            "prccd": "select",
            "cmd1": sql1,
            "cmd2": sql2,
            "format": "json",
        })
        qid1, qid2 = data["ret1"], data["ret2"]
        self._poll_until_done(qid1)
        url_data = self._submit({
            **self._auth_params(),
            "prccd": "geturl",
            "qid1": qid1,
            "qid2": qid2,
        })
        result1 = self._download_csv(url_data["ret1"])
        result2 = self._download_csv(url_data["ret2"])
        return result1, result2
```

**Run:** `cd backend && uv run pytest tests/batch/test_hrdb_client.py -v`
**Expected:** ALL PASS

### Step 3: コミット

```bash
git add backend/batch/hrdb_client.py backend/tests/batch/test_hrdb_client.py
git commit -m "feat: HrdbClient — GAMBLE-OS HRDB-API クライアント実装"
```

---

## Task 2: DynamoDBテーブル定義（CDK）

**Files:**
- Modify: `cdk/stacks/api_stack.py`
- Test: `cdk/tests/unit/test_api_stack.py`

### Step 1: CDKテスト追加

`test_api_stack.py` に新テーブルの存在を検証するテストを追加。

```python
def test_racesテーブルが作成される(self):
    template = self._get_template()
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "TableName": "baken-kaigi-races",
        "KeySchema": Match.array_with([
            Match.object_like({"AttributeName": "race_date", "KeyType": "HASH"}),
            Match.object_like({"AttributeName": "race_id", "KeyType": "RANGE"}),
        ]),
        "BillingMode": "PAY_PER_REQUEST",
    })

def test_runnersテーブルが作成される(self):
    template = self._get_template()
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "TableName": "baken-kaigi-runners",
        "KeySchema": Match.array_with([
            Match.object_like({"AttributeName": "race_id", "KeyType": "HASH"}),
            Match.object_like({"AttributeName": "horse_number", "KeyType": "RANGE"}),
        ]),
        "BillingMode": "PAY_PER_REQUEST",
    })
```

**Run:** `cd cdk && npx jest --testPathPattern test_api_stack`
**Expected:** FAIL — テーブルが存在しない

### Step 2: DynamoDBテーブル追加

`api_stack.py` に2テーブル追加:

```python
# --- レースデータ（HRDB-API移行） ---

races_table = dynamodb.Table(
    self, "RacesTable",
    table_name="baken-kaigi-races",
    partition_key=dynamodb.Attribute(
        name="race_date", type=dynamodb.AttributeType.STRING
    ),
    sort_key=dynamodb.Attribute(
        name="race_id", type=dynamodb.AttributeType.STRING
    ),
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
    removal_policy=RemovalPolicy.DESTROY,
    time_to_live_attribute="ttl",
)

runners_table = dynamodb.Table(
    self, "RunnersTable",
    table_name="baken-kaigi-runners",
    partition_key=dynamodb.Attribute(
        name="race_id", type=dynamodb.AttributeType.STRING
    ),
    sort_key=dynamodb.Attribute(
        name="horse_number", type=dynamodb.AttributeType.STRING
    ),
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
    removal_policy=RemovalPolicy.DESTROY,
    time_to_live_attribute="ttl",
)
runners_table.add_global_secondary_index(
    index_name="horse_id-index",
    partition_key=dynamodb.Attribute(
        name="horse_id", type=dynamodb.AttributeType.STRING
    ),
    sort_key=dynamodb.Attribute(
        name="race_date", type=dynamodb.AttributeType.STRING
    ),
    projection_type=dynamodb.ProjectionType.ALL,
)
```

**Run:** `cd cdk && npx jest --testPathPattern test_api_stack`
**Expected:** PASS

### Step 3: AgentCoreランタイムロールにread権限追加

`api_stack.py` のAgentCoreランタイムロール定義部で、新テーブルにも `grant_read_data()` を追加:

```python
races_table.grant_read_data(agentcore_runtime_role)
runners_table.grant_read_data(agentcore_runtime_role)
```

### Step 4: コミット

```bash
git add cdk/stacks/api_stack.py cdk/tests/unit/test_api_stack.py
git commit -m "feat: races/runnersテーブル定義追加（HRDB-API移行）"
```

---

## Task 3: レース場コード・HRDB定数マッピング

**Files:**
- Create: `backend/batch/hrdb_constants.py`
- Test: `backend/tests/batch/test_hrdb_constants.py`

### Step 1: テスト作成

HRDBのコースコード（RCOURSECD）とrace_idの相互変換をテスト。

```python
"""HRDB定数・コード変換のテスト."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from batch.hrdb_constants import (
    VENUE_CODE_MAP,
    hrdb_to_race_id,
    parse_race_id,
)


class TestHrdbToRaceId:
    def test_東京5R(self):
        assert hrdb_to_race_id("20260214", "05", "05") == "202602140505"

    def test_阪神11R(self):
        assert hrdb_to_race_id("20260215", "08", "11") == "202602150811"

    def test_小倉1R(self):
        assert hrdb_to_race_id("20260214", "10", "01") == "202602141001"


class TestParseRaceId:
    def test_race_idをパース(self):
        date, venue, rno = parse_race_id("202602140511")
        assert date == "20260214"
        assert venue == "05"
        assert rno == "11"


class TestVenueCodeMap:
    def test_全10場のマッピング(self):
        assert VENUE_CODE_MAP["01"] == "札幌"
        assert VENUE_CODE_MAP["05"] == "東京"
        assert VENUE_CODE_MAP["08"] == "阪神"
        assert VENUE_CODE_MAP["10"] == "小倉"
        assert len(VENUE_CODE_MAP) == 10
```

**Run:** `cd backend && uv run pytest tests/batch/test_hrdb_constants.py -v`
**Expected:** FAIL

### Step 2: 定数モジュール実装

```python
"""HRDB-API定数・コード変換."""

VENUE_CODE_MAP: dict[str, str] = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "阪神",
    "09": "京都",
    "10": "小倉",
}


def hrdb_to_race_id(opdt: str, rcoursecd: str, rno: str) -> str:
    """HRDB各カラム値からrace_id (12桁) を生成."""
    return f"{opdt}{rcoursecd.zfill(2)}{rno.zfill(2)}"


def parse_race_id(race_id: str) -> tuple[str, str, str]:
    """race_id (12桁) を (date, venue_code, race_number) に分解."""
    return race_id[:8], race_id[8:10], race_id[10:12]
```

**Run:** `cd backend && uv run pytest tests/batch/test_hrdb_constants.py -v`
**Expected:** PASS

### Step 3: コミット

```bash
git add backend/batch/hrdb_constants.py backend/tests/batch/test_hrdb_constants.py
git commit -m "feat: HRDB定数・コード変換モジュール"
```

---

## Task 4: レースデータバッチスクレイパー

**Files:**
- Create: `backend/batch/hrdb_race_scraper.py`
- Test: `backend/tests/batch/test_hrdb_race_scraper.py`

### Step 1: テスト作成 — データ変換

HRDBのCSV行をDynamoDB用dictに変換するロジックをテスト。

```python
"""HRDBレースデータスクレイパーのテスト."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from batch.hrdb_race_scraper import (
    convert_race_row,
    convert_runner_row,
    handler,
)

JST = timezone(timedelta(hours=9))


class TestConvertRaceRow:
    """RACEMST行 → DynamoDBアイテム変換."""

    def _make_row(self, **overrides):
        base = {
            "OPDT": "20260214",
            "RCOURSECD": "05",
            "RNO": "11",
            "RNMHON": "デイリー杯クイーンカップ",
            "GCD": "C",
            "DIST": "1600",
            "TRACKCD": "11",
            "ENTNUM": "16",
            "RUNNUM": "16",
            "POSTTM": "1530",
            "WEATHERCD": "1",
            "TSTATCD": "1",
            "DSTATCD": "",
            "RKINDCD": "",
            "KAI": "01",
            "NITIME": "03",
        }
        base.update(overrides)
        return base

    def test_基本変換(self):
        row = self._make_row()
        item = convert_race_row(row, scraped_at=datetime(2026, 2, 13, 21, 0, tzinfo=JST))

        assert item["race_date"] == "20260214"
        assert item["race_id"] == "202602140511"
        assert item["race_name"] == "デイリー杯クイーンカップ"
        assert item["venue"] == "東京"
        assert item["venue_code"] == "05"
        assert item["race_number"] == 11
        assert item["distance"] == 1600
        assert item["track_type"] == "芝"
        assert item["grade"] == "C"
        assert item["horse_count"] == 16
        assert "ttl" in item

    def test_ダートトラック(self):
        row = self._make_row(TRACKCD="23")
        item = convert_race_row(row, scraped_at=datetime(2026, 2, 13, 21, 0, tzinfo=JST))
        assert item["track_type"] == "ダート"

    def test_障害トラック(self):
        row = self._make_row(TRACKCD="54")
        item = convert_race_row(row, scraped_at=datetime(2026, 2, 13, 21, 0, tzinfo=JST))
        assert item["track_type"] == "障害"


class TestConvertRunnerRow:
    """RACEDTL行 → DynamoDBアイテム変換."""

    def _make_row(self, **overrides):
        base = {
            "OPDT": "20260214",
            "RCOURSECD": "05",
            "RNO": "11",
            "UMANO": "01",
            "BLDNO": "1234567890",
            "WAKNO": "1",
            "HSNM": "ドリームコア",
            "SEXCD": "2",
            "AGE": "03",
            "JKYCD": "01234",
            "JKYNM4": "ルメール",
            "TRNRCD": "05678",
            "TRNRNM4": "藤沢和雄",
            "FTNWGHT": "550",
            "FIXPLC": "01",
            "RUNTM": "1326",
            "TANODDS": "0034",
            "TANNINKI": "02",
            "CONRPLC1": "05",
            "CONRPLC2": "03",
            "CONRPLC3": "02",
            "CONRPLC4": "01",
        }
        base.update(overrides)
        return base

    def test_基本変換(self):
        row = self._make_row()
        item = convert_runner_row(row, scraped_at=datetime(2026, 2, 13, 21, 0, tzinfo=JST))

        assert item["race_id"] == "202602140511"
        assert item["race_date"] == "20260214"
        assert item["horse_number"] == "01"
        assert item["horse_id"] == "1234567890"
        assert item["horse_name"] == "ドリームコア"
        assert item["waku_ban"] == 1
        assert item["jockey_name"] == "ルメール"
        assert item["jockey_id"] == "01234"
        assert item["weight_carried"] == 55.0
        assert item["finish_position"] == 1
        assert item["time"] == "1:32.6"
        assert item["odds"] == 3.4
        assert item["popularity"] == 2

    def test_未確定の着順(self):
        row = self._make_row(FIXPLC="00", RUNTM="0000")
        item = convert_runner_row(row, scraped_at=datetime(2026, 2, 13, 21, 0, tzinfo=JST))
        assert item["finish_position"] is None
        assert item["time"] is None

    def test_走破タイム変換(self):
        row = self._make_row(RUNTM="1455")
        item = convert_runner_row(row, scraped_at=datetime(2026, 2, 13, 21, 0, tzinfo=JST))
        assert item["time"] == "1:45.5"


class TestHandler:
    """Lambda handler のテスト."""

    @patch("batch.hrdb_race_scraper.get_hrdb_client")
    @patch("batch.hrdb_race_scraper.get_races_table")
    @patch("batch.hrdb_race_scraper.get_runners_table")
    def test_翌日データ取得の正常系(self, mock_runners_tbl, mock_races_tbl, mock_client):
        client = MagicMock()
        mock_client.return_value = client

        races_table = MagicMock()
        mock_races_tbl.return_value = races_table

        runners_table = MagicMock()
        mock_runners_tbl.return_value = runners_table

        # query_dual: (RACEMST, RACEDTL)
        client.query_dual.return_value = (
            [{"OPDT": "20260215", "RCOURSECD": "05", "RNO": "01",
              "RNMHON": "", "GCD": "", "DIST": "1400", "TRACKCD": "23",
              "ENTNUM": "16", "RUNNUM": "16", "POSTTM": "1000",
              "WEATHERCD": "", "TSTATCD": "", "DSTATCD": "",
              "RKINDCD": "", "KAI": "01", "NITIME": "01"}],
            [{"OPDT": "20260215", "RCOURSECD": "05", "RNO": "01",
              "UMANO": "01", "BLDNO": "123", "WAKNO": "1",
              "HSNM": "テスト馬", "SEXCD": "1", "AGE": "03",
              "JKYCD": "001", "JKYNM4": "テスト", "TRNRCD": "001",
              "TRNRNM4": "テスト", "FTNWGHT": "570", "FIXPLC": "00",
              "RUNTM": "0000", "TANODDS": "0000", "TANNINKI": "00",
              "CONRPLC1": "", "CONRPLC2": "", "CONRPLC3": "", "CONRPLC4": ""}],
        )

        result = handler({"offset_days": 1}, None)

        assert result["statusCode"] == 200
        assert result["body"]["races_saved"] == 1
        assert result["body"]["runners_saved"] == 1
        client.query_dual.assert_called_once()
        races_table.put_item.assert_called_once()
        runners_table.put_item.assert_called_once()
```

**Run:** `cd backend && uv run pytest tests/batch/test_hrdb_race_scraper.py -v`
**Expected:** FAIL

### Step 2: スクレイパー実装

```python
"""HRDBレースデータスクレイパー.

HRDB-APIからRACEMST/RACEDTLを取得しDynamoDBに書き込む。
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import boto3

from batch.hrdb_client import HrdbClient
from batch.hrdb_constants import VENUE_CODE_MAP, hrdb_to_race_id

logger = logging.getLogger(__name__)
JST = timezone(timedelta(hours=9))
TTL_DAYS = 14

# TRACKCDの先頭桁: 1=芝, 2=ダート, 5=障害
TRACK_TYPE_MAP = {"1": "芝", "2": "ダート", "5": "障害"}


def get_hrdb_client() -> HrdbClient:
    secret = _get_secret()
    return HrdbClient(club_id=secret["club_id"], club_password=secret["club_password"])


def _get_secret() -> dict:
    secret_name = os.environ.get(
        "HRDB_SECRET_NAME", "baken-kaigi/gamble-os-credentials"
    )
    client = boto3.client("secretsmanager")
    import json
    resp = client.get_secret_value(SecretId=secret_name)
    return json.loads(resp["SecretString"])


def get_races_table():
    table_name = os.environ.get("RACES_TABLE_NAME", "baken-kaigi-races")
    return boto3.resource("dynamodb").Table(table_name)


def get_runners_table():
    table_name = os.environ.get("RUNNERS_TABLE_NAME", "baken-kaigi-runners")
    return boto3.resource("dynamodb").Table(table_name)


def convert_race_row(row: dict, scraped_at: datetime) -> dict:
    """RACEMST行をDynamoDBアイテムに変換."""
    opdt = row["OPDT"].strip()
    rcoursecd = row["RCOURSECD"].strip()
    rno = row["RNO"].strip()
    race_id = hrdb_to_race_id(opdt, rcoursecd, rno)
    track_code = row.get("TRACKCD", "").strip()
    track_type = TRACK_TYPE_MAP.get(track_code[:1], "") if track_code else ""

    ttl = int((scraped_at + timedelta(days=TTL_DAYS)).timestamp())

    return {
        "race_date": opdt,
        "race_id": race_id,
        "venue_code": rcoursecd,
        "venue": VENUE_CODE_MAP.get(rcoursecd, rcoursecd),
        "race_number": int(rno),
        "race_name": row.get("RNMHON", "").strip(),
        "grade": row.get("GCD", "").strip(),
        "distance": int(row.get("DIST", "0").strip() or "0"),
        "track_type": track_type,
        "track_code": track_code,
        "horse_count": int(row.get("ENTNUM", "0").strip() or "0"),
        "run_count": int(row.get("RUNNUM", "0").strip() or "0"),
        "post_time": row.get("POSTTM", "").strip(),
        "weather_code": row.get("WEATHERCD", "").strip(),
        "turf_condition_code": row.get("TSTATCD", "").strip(),
        "dirt_condition_code": row.get("DSTATCD", "").strip(),
        "kaisai_kai": row.get("KAI", "").strip(),
        "kaisai_nichime": row.get("NITIME", "").strip(),
        "scraped_at": scraped_at.isoformat(),
        "ttl": ttl,
    }


def _parse_run_time(runtm: str) -> str | None:
    """走破タイム (例: '1326') を '1:32.6' 形式に変換."""
    runtm = runtm.strip()
    if not runtm or runtm == "0000" or not runtm.isdigit():
        return None
    minutes = int(runtm[0])
    seconds = int(runtm[1:3])
    tenths = int(runtm[3])
    return f"{minutes}:{seconds:02d}.{tenths}"


def convert_runner_row(row: dict, scraped_at: datetime) -> dict:
    """RACEDTL行をDynamoDBアイテムに変換."""
    opdt = row["OPDT"].strip()
    rcoursecd = row["RCOURSECD"].strip()
    rno = row["RNO"].strip()
    race_id = hrdb_to_race_id(opdt, rcoursecd, rno)

    fixplc_raw = row.get("FIXPLC", "").strip()
    fixplc = int(fixplc_raw) if fixplc_raw and fixplc_raw.isdigit() and fixplc_raw != "00" else None

    tanodds_raw = row.get("TANODDS", "").strip()
    odds = round(int(tanodds_raw) / 10, 1) if tanodds_raw and tanodds_raw.isdigit() and tanodds_raw != "0000" else None

    tanninki_raw = row.get("TANNINKI", "").strip()
    popularity = int(tanninki_raw) if tanninki_raw and tanninki_raw.isdigit() and tanninki_raw != "00" else None

    ftnwght_raw = row.get("FTNWGHT", "").strip()
    weight_carried = int(ftnwght_raw) / 10 if ftnwght_raw and ftnwght_raw.isdigit() else None

    umano = row["UMANO"].strip().zfill(2)

    ttl = int((scraped_at + timedelta(days=TTL_DAYS)).timestamp())

    item: dict[str, Any] = {
        "race_id": race_id,
        "horse_number": umano,
        "race_date": opdt,
        "horse_id": row.get("BLDNO", "").strip(),
        "horse_name": row.get("HSNM", "").strip(),
        "waku_ban": int(row.get("WAKNO", "0").strip() or "0"),
        "sex_code": row.get("SEXCD", "").strip(),
        "age": int(row.get("AGE", "0").strip() or "0"),
        "jockey_id": row.get("JKYCD", "").strip(),
        "jockey_name": row.get("JKYNM4", "").strip(),
        "trainer_id": row.get("TRNRCD", "").strip(),
        "trainer_name": row.get("TRNRNM4", "").strip(),
        "weight_carried": Decimal(str(weight_carried)) if weight_carried else None,
        "finish_position": fixplc,
        "time": _parse_run_time(row.get("RUNTM", "")),
        "odds": Decimal(str(odds)) if odds else None,
        "popularity": popularity,
        "scraped_at": scraped_at.isoformat(),
        "ttl": ttl,
    }
    # DynamoDBはNone値を保存しないのでフィルタ
    return {k: v for k, v in item.items() if v is not None}


def _scrape_date(target_date: str, hrdb: HrdbClient, races_table, runners_table) -> dict:
    """指定日のレース・出走馬データを取得してDynamoDBに保存."""
    now = datetime.now(tz=JST)

    races_sql = f"SELECT * FROM RACEMST WHERE OPDT = '{target_date}';"
    runners_sql = f"SELECT * FROM RACEDTL WHERE OPDT = '{target_date}';"

    race_rows, runner_rows = hrdb.query_dual(races_sql, runners_sql)
    logger.info("Fetched %d races, %d runners for %s", len(race_rows), len(runner_rows), target_date)

    races_saved = 0
    for row in race_rows:
        item = convert_race_row(row, scraped_at=now)
        races_table.put_item(Item=item)
        races_saved += 1

    runners_saved = 0
    for row in runner_rows:
        item = convert_runner_row(row, scraped_at=now)
        runners_table.put_item(Item=item)
        runners_saved += 1

    return {"races_saved": races_saved, "runners_saved": runners_saved}


def handler(event: dict, context: Any) -> dict:
    """Lambda handler."""
    try:
        offset_days = int(event.get("offset_days", 1))
    except (TypeError, ValueError):
        offset_days = 1

    target_date = (datetime.now(tz=JST) + timedelta(days=offset_days)).strftime("%Y%m%d")
    logger.info("Scraping HRDB data for %s (offset_days=%d)", target_date, offset_days)

    try:
        hrdb = get_hrdb_client()
        races_table = get_races_table()
        runners_table = get_runners_table()
        result = _scrape_date(target_date, hrdb, races_table, runners_table)
        return {
            "statusCode": 200,
            "body": {"success": True, "target_date": target_date, **result},
        }
    except Exception as e:
        logger.exception("HRDB scraper failed")
        return {
            "statusCode": 500,
            "body": {"success": False, "error": str(e)},
        }
```

**Run:** `cd backend && uv run pytest tests/batch/test_hrdb_race_scraper.py -v`
**Expected:** PASS

### Step 3: コミット

```bash
git add backend/batch/hrdb_race_scraper.py backend/tests/batch/test_hrdb_race_scraper.py
git commit -m "feat: HRDBレースデータバッチスクレイパー"
```

---

## Task 5: CDKバッチLambda + EventBridge + SecretsManager

**Files:**
- Modify: `cdk/stacks/batch_stack.py`
- Test: `cdk/tests/unit/test_batch_stack.py`

### Step 1: CDKテスト追加

```python
def test_hrdb_race_scraperが作成される(self):
    template = self._get_template()
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "baken-kaigi-hrdb-race-scraper",
        "Handler": "batch.hrdb_race_scraper.handler",
        "Timeout": 600,
    })

def test_hrdb_scraperのEventBridgeルールが作成される(self):
    template = self._get_template()
    template.has_resource_properties("AWS::Events::Rule", {
        "Name": "baken-kaigi-hrdb-race-scraper-evening-rule",
    })
```

**Run:** `cd cdk && npx jest --testPathPattern test_batch_stack`
**Expected:** FAIL

### Step 2: batch_stack.py にHRDBスクレイパーLambda追加

`batch_stack.py` に以下を追加:
- Secrets Manager参照（GAMBLE-OS認証情報）
- `hrdb_race_scraper` Lambda（timeout=600s, memory=512MB）
- `races_table` + `runners_table` への書き込み権限
- Secrets Manager読み取り権限
- EventBridgeルール: 毎晩21:00 JST (offset_days=1) + 当日8:30 JST (offset_days=0)

### Step 3: テスト実行 → PASS → コミット

```bash
git add cdk/stacks/batch_stack.py cdk/tests/unit/test_batch_stack.py
git commit -m "feat: HRDBスクレイパーLambda + EventBridge定義（CDK）"
```

---

## Task 6: Secrets Manager に認証情報を登録

### Step 1: AWS CLIでシークレット作成

```bash
aws secretsmanager create-secret \
  --name baken-kaigi/gamble-os-credentials \
  --secret-string '{"club_id":"daikinoue0222@gmail.com","club_password":"bf46135d"}' \
  --region ap-northeast-1
```

### Step 2: コミット不要（インフラ手動操作）

---

## Task 7: 結合テスト — ローカルでHRDB-APIアクセス確認

### Step 1: ローカル実行スクリプト作成

```python
# backend/scripts/test_hrdb_fetch.py
"""HRDB-APIへのアクセス確認スクリプト."""
import json
import sys
sys.path.insert(0, ".")
from batch.hrdb_client import HrdbClient

client = HrdbClient(
    club_id="daikinoue0222@gmail.com",
    club_password="bf46135d",
)

# 直近のレースデータ取得テスト
races, runners = client.query_dual(
    "SELECT OPDT,RCOURSECD,RNO,RNMHON,GCD,DIST,TRACKCD,ENTNUM,RUNNUM FROM RACEMST WHERE OPDT = '20260222';",
    "SELECT OPDT,RCOURSECD,RNO,UMANO,HSNM,JKYNM4,TANODDS,TANNINKI,FIXPLC,RUNTM FROM RACEDTL WHERE OPDT = '20260222' AND RCOURSECD = '05' AND RNO = '11';",
)

print(f"Races: {len(races)}")
for r in races[:5]:
    print(f"  {r['OPDT']} 場{r['RCOURSECD']} {r['RNO']}R {r['RNMHON']}")

print(f"\nRunners: {len(runners)}")
for r in runners:
    print(f"  {r['UMANO']}番 {r['HSNM']} ({r['JKYNM4']}) 単{r['TANODDS']} {r['TANNINKI']}人気")
```

**Run:** `cd backend && uv run python scripts/test_hrdb_fetch.py`
**Expected:** レースデータと出走馬データが表示される

### Step 2: データ変換の確認

```python
# 変換テスト追加
from batch.hrdb_race_scraper import convert_race_row, convert_runner_row
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
now = datetime.now(tz=JST)

for race in races[:3]:
    item = convert_race_row(race, scraped_at=now)
    print(json.dumps(item, ensure_ascii=False, indent=2, default=str))
```

### Step 3: コミット

```bash
git add backend/scripts/test_hrdb_fetch.py
git commit -m "chore: HRDB-APIローカル確認スクリプト追加"
```

---

## 完了条件

Phase 1完了時点で:
- [x] `HrdbClient` がHRDB-APIにSQL送信→CSV取得→dict変換できる
- [x] DynamoDBに `baken-kaigi-races` / `baken-kaigi-runners` テーブルが定義済み
- [x] バッチLambdaがEventBridgeスケジュールで翌日/当日のレースデータを取得→DynamoDB保存
- [x] Secrets ManagerにGAMBLE-OS認証情報が登録済み
- [x] 全テスト PASS

## 次のフェーズ（別計画）

- **Phase 2**: `DynamoDbRaceDataProvider` 実装 + AgentCoreツール移行
- **Phase 3**: オッズデータ移行（ODDSTFWK等）
- **Phase 4**: EC2/JRA-VAN廃止
