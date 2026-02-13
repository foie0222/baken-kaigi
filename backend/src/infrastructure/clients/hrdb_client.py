"""GAMBLE-OS HRDB-API クライアント.

非同期バッチ型API:
1. データベース検索要求（prccd=select でSQL送信）→ キューID取得
2. データベース処理状況（prccd=state でポーリング）→ 完了待ち
3. データベースデータ（prccd=getcsv）→ CSV取得 → list[dict]

全操作は同一エンドポイント /systems/hrdb に POST。
prccd パラメータで操作を切り替える。
"""
import csv
import io
import logging
import time

import requests

logger = logging.getLogger(__name__)

# ポーリング時のステータスコード
_STATUS_WAITING = "0"
_STATUS_PROCESSING = "1"
_STATUS_DONE = "2"
_STATUS_FAILED = "4"
_STATUS_SQL_ERROR = "6"
_STATUS_CANCELLED = "8"


class HrdbApiError(Exception):
    """HRDB-API エラー."""

    pass


class HrdbClient:
    """GAMBLE-OS HRDB-API クライアント."""

    def __init__(
        self,
        club_id: str,
        club_password: str,
        api_domain: str,
    ) -> None:
        self._club_id = club_id
        self._club_password = club_password
        self._endpoint = f"{api_domain.rstrip('/')}/systems/hrdb"
        self._max_poll_attempts = 60
        self._poll_interval = 3
        self._timeout = 30

    def query(self, sql: str) -> list[dict]:
        """SQLを実行して結果をdictリストで返す."""
        queue_id = self._submit(sql)
        self._wait_for_completion(queue_id)
        return self._fetch_csv(queue_id)

    def _auth_params(self) -> dict:
        return {"tncid": self._club_id, "tncpw": self._club_password}

    def _submit(self, sql: str) -> str:
        """prccd=select でSQL送信し、キューIDを取得する."""
        params = {**self._auth_params(), "prccd": "select", "cmd1": sql}
        response = requests.post(self._endpoint, data=params, timeout=self._timeout)
        data = response.json()

        ret = data.get("ret", "")
        if ret != "0":
            raise HrdbApiError(data.get("msg", f"SQL送信エラー (ret={ret})"))

        queue_id = data.get("ret1", "")
        if not queue_id or queue_id.startswith("-"):
            raise HrdbApiError(
                data.get("msg1", f"キューID取得エラー (ret1={queue_id})")
            )
        return queue_id

    def _wait_for_completion(self, queue_id: str) -> None:
        """prccd=state でポーリングし、処理完了を待つ."""
        for _ in range(self._max_poll_attempts):
            params = {**self._auth_params(), "prccd": "state", "qid1": queue_id}
            response = requests.post(
                self._endpoint, data=params, timeout=self._timeout
            )
            data = response.json()

            status = data.get("ret1", "")
            if status == _STATUS_DONE:
                return
            if status in (_STATUS_FAILED, _STATUS_SQL_ERROR, _STATUS_CANCELLED):
                raise HrdbApiError(
                    f"処理失敗 (status={status}): {data.get('msg1', '')}"
                )
            time.sleep(self._poll_interval)

        raise HrdbApiError("ポーリングがタイムアウトしました")

    def _fetch_csv(self, queue_id: str) -> list[dict]:
        """prccd=getcsv でCSV結果を取得しdictリストに変換する."""
        params = {**self._auth_params(), "prccd": "getcsv", "qid": queue_id}
        response = requests.post(self._endpoint, data=params, timeout=self._timeout)
        text = response.text.strip()
        if not text:
            return []
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
