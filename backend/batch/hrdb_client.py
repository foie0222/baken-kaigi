"""HRDB-APIクライアント.

競馬データベース(HRDB)にSQLクエリを送信し、CSV結果を取得する。

APIワークフロー:
1. select: SQLクエリ送信 → クエリID取得
2. state: ポーリングで完了待ち
3. geturl: CSV ダウンロードURL取得
4. GET: CSV ダウンロード（Shift-JIS）
"""

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
    """HRDB-APIクライアント."""

    def __init__(self, club_id: str, club_password: str) -> None:
        self._club_id = club_id
        self._club_password = club_password

    def query(self, sql: str) -> list[dict]:
        """単一SQLクエリを実行し、結果をlist[dict]で返す."""
        logger.info("HRDB query: %s", sql[:100])
        qid = self._submit(cmd1=sql)
        self._poll(qid1=qid)
        url = self._get_url(qid1=qid)
        return self._download_csv(url)

    def query_dual(self, sql1: str, sql2: str) -> tuple[list[dict], list[dict]]:
        """2つのSQLクエリを同時実行し、結果のタプルを返す."""
        logger.info("HRDB query_dual: sql1=%s, sql2=%s", sql1[:100], sql2[:100])
        qid1, qid2 = self._submit(cmd1=sql1, cmd2=sql2)
        self._poll(qid1=qid1, qid2=qid2)
        url1, url2 = self._get_url(qid1=qid1, qid2=qid2)
        return self._download_csv(url1), self._download_csv(url2)

    def _base_data(self) -> dict:
        return {
            "tncid": self._club_id,
            "tncpw": self._club_password,
        }

    def _submit(
        self, cmd1: str, cmd2: str | None = None
    ) -> str | tuple[str, str]:
        """SQLクエリを送信し、クエリIDを返す.

        cmd2を指定した場合は2つのクエリIDのタプルを返す。
        """
        data = self._base_data()
        data["prccd"] = "select"
        data["cmd1"] = cmd1
        if cmd2 is not None:
            data["cmd2"] = cmd2
        data["format"] = "json"

        resp = requests.post(API_URL, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        ret1 = result["ret1"]
        self._check_error(ret1, result)

        if cmd2 is not None:
            ret2 = result["ret2"]
            self._check_error(ret2, result)
            return ret1, ret2

        return ret1

    def _check_error(self, ret: str, result: dict) -> None:
        """retが負の値ならRuntimeErrorを送出."""
        if ret.lstrip("-").isdigit() and int(ret) < 0:
            msg = result.get("msg", "不明なエラー")
            raise RuntimeError(f"HRDB API error: ret={ret}, msg={msg}")

    def _poll(self, qid1: str, qid2: str | None = None) -> None:
        """クエリ完了までポーリング."""
        for _ in range(MAX_POLL_ATTEMPTS):
            data = self._base_data()
            data["prccd"] = "state"
            data["qid1"] = qid1
            if qid2 is not None:
                data["qid2"] = qid2

            resp = requests.post(API_URL, data=data, timeout=30)
            resp.raise_for_status()
            result = resp.json()

            state1 = result["ret1"]
            if state1 == "6":
                raise RuntimeError(
                    f"HRDB-API SQL error for qid={qid1}"
                )

            state2 = result.get("ret2")
            if state2 == "6":
                raise RuntimeError(
                    f"HRDB-API SQL error for qid={qid2}"
                )

            # 両方完了しているか確認
            done1 = state1 == "2"
            done2 = state2 == "2" if qid2 is not None else True

            if done1 and done2:
                return

            time.sleep(POLL_INTERVAL_SECONDS)

        raise TimeoutError(
            f"HRDB polling timed out after {MAX_POLL_ATTEMPTS} attempts"
        )

    def _get_url(
        self, qid1: str, qid2: str | None = None
    ) -> str | tuple[str, str]:
        """CSV ダウンロードURLを取得.

        qid2を指定した場合は2つのURLのタプルを返す。
        """
        data = self._base_data()
        data["prccd"] = "geturl"
        data["qid1"] = qid1
        if qid2 is not None:
            data["qid2"] = qid2

        resp = requests.post(API_URL, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        if qid2 is not None:
            return result["ret1"], result["ret2"]
        return result["ret1"]

    def _download_csv(self, url: str) -> list[dict]:
        """CSVをダウンロードしてlist[dict]にパース.

        HRDBのCSVはShift-JISでエンコードされており、
        値がスペースでパディングされているためトリムする。
        """
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        text = resp.content.decode("shift_jis")
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            trimmed = {k.strip(): v.strip() for k, v in row.items()}
            rows.append(trimmed)
        return rows
