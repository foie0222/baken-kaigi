"""HRDB-APIクライアントのテスト."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.hrdb_client import HrdbClient, API_URL, POLL_INTERVAL_SECONDS, MAX_POLL_ATTEMPTS


class TestHrdbClientQuery:
    """HrdbClient.query() のテスト."""

    def _make_client(self):
        return HrdbClient(club_id="TEST_ID", club_password="TEST_PW")

    @patch("batch.hrdb_client.time.sleep")
    @patch("batch.hrdb_client.requests.get")
    @patch("batch.hrdb_client.requests.post")
    def test_正常なクエリフロー(self, mock_post, mock_get, mock_sleep):
        """submit → poll(processing) → poll(done) → geturl → download CSV."""
        # submit: クエリ送信
        submit_resp = MagicMock()
        submit_resp.json.return_value = {"ret1": "QID_001"}

        # state: 1回目は処理中、2回目は完了
        state_processing = MagicMock()
        state_processing.json.return_value = {"ret1": "1"}
        state_done = MagicMock()
        state_done.json.return_value = {"ret1": "2"}

        # geturl: CSV URL取得
        geturl_resp = MagicMock()
        geturl_resp.json.return_value = {"ret1": "https://example.com/result.csv"}

        mock_post.side_effect = [submit_resp, state_processing, state_done, geturl_resp]

        # CSV download
        csv_content = "馬番,馬名,タイム\r\n1,ディープインパクト,1:58.5\r\n2,キタサンブラック,1:59.0\r\n"
        csv_resp = MagicMock()
        csv_resp.content = csv_content.encode("shift_jis")
        mock_get.return_value = csv_resp

        client = self._make_client()
        result = client.query("SELECT * FROM uma")

        assert len(result) == 2
        assert result[0] == {"馬番": "1", "馬名": "ディープインパクト", "タイム": "1:58.5"}
        assert result[1] == {"馬番": "2", "馬名": "キタサンブラック", "タイム": "1:59.0"}

        # submit呼び出しの検証
        submit_call = mock_post.call_args_list[0]
        assert submit_call[1]["data"]["prccd"] == "select"
        assert submit_call[1]["data"]["tncid"] == "TEST_ID"
        assert submit_call[1]["data"]["tncpw"] == "TEST_PW"
        assert submit_call[1]["data"]["cmd1"] == "SELECT * FROM uma"
        assert submit_call[1]["data"]["format"] == "json"

        # sleepはポーリング中に1回呼ばれる
        mock_sleep.assert_called_once_with(POLL_INTERVAL_SECONDS)

    @patch("batch.hrdb_client.requests.post")
    def test_認証エラー(self, mock_post):
        """ret=-200 → RuntimeError."""
        submit_resp = MagicMock()
        submit_resp.json.return_value = {"ret1": "-200", "msg": "認証に失敗しました"}
        mock_post.return_value = submit_resp

        client = self._make_client()
        try:
            client.query("SELECT 1")
            assert False, "RuntimeError が発生するべき"
        except RuntimeError as e:
            assert "-200" in str(e)

    @patch("batch.hrdb_client.requests.post")
    def test_ライセンスエラー(self, mock_post):
        """ret=-203 → RuntimeError."""
        submit_resp = MagicMock()
        submit_resp.json.return_value = {"ret1": "-203", "msg": "ライセンスが無効です"}
        mock_post.return_value = submit_resp

        client = self._make_client()
        try:
            client.query("SELECT 1")
            assert False, "RuntimeError が発生するべき"
        except RuntimeError as e:
            assert "-203" in str(e)

    @patch("batch.hrdb_client.time.sleep")
    @patch("batch.hrdb_client.requests.post")
    def test_SQLエラー(self, mock_post, mock_sleep):
        """state=6 → RuntimeError."""
        submit_resp = MagicMock()
        submit_resp.json.return_value = {"ret1": "QID_001"}

        state_error = MagicMock()
        state_error.json.return_value = {"ret1": "6"}

        mock_post.side_effect = [submit_resp, state_error]

        client = self._make_client()
        try:
            client.query("SELECT * FROM nonexistent")
            assert False, "RuntimeError が発生するべき"
        except RuntimeError as e:
            assert "SQL" in str(e)

    @patch("batch.hrdb_client.time.sleep")
    @patch("batch.hrdb_client.requests.get")
    @patch("batch.hrdb_client.requests.post")
    def test_CSVの空白がトリムされる(self, mock_post, mock_get, mock_sleep):
        """HRDBはCSV値をスペースでパディングするためトリムが必要."""
        submit_resp = MagicMock()
        submit_resp.json.return_value = {"ret1": "QID_001"}

        state_done = MagicMock()
        state_done.json.return_value = {"ret1": "2"}

        geturl_resp = MagicMock()
        geturl_resp.json.return_value = {"ret1": "https://example.com/result.csv"}

        mock_post.side_effect = [submit_resp, state_done, geturl_resp]

        # 空白パディングされたCSV
        csv_content = "Code ,Name      ,Value \r\n 01  ,テスト    , 100  \r\n"
        csv_resp = MagicMock()
        csv_resp.content = csv_content.encode("shift_jis")
        mock_get.return_value = csv_resp

        client = self._make_client()
        result = client.query("SELECT * FROM test")

        assert len(result) == 1
        assert result[0] == {"Code": "01", "Name": "テスト", "Value": "100"}

    @patch("batch.hrdb_client.time.sleep")
    @patch("batch.hrdb_client.requests.post")
    def test_ポーリングタイムアウト(self, mock_post, mock_sleep):
        """MAX_POLL_ATTEMPTS 回ポーリングしても完了しない → TimeoutError."""
        submit_resp = MagicMock()
        submit_resp.json.return_value = {"ret1": "QID_001"}

        state_processing = MagicMock()
        state_processing.json.return_value = {"ret1": "1"}

        mock_post.side_effect = [submit_resp] + [state_processing] * MAX_POLL_ATTEMPTS

        client = self._make_client()
        try:
            client.query("SELECT * FROM huge_table")
            assert False, "TimeoutError が発生するべき"
        except TimeoutError:
            pass

        assert mock_sleep.call_count == MAX_POLL_ATTEMPTS


class TestHrdbClientQueryDual:
    """HrdbClient.query_dual() のテスト."""

    def _make_client(self):
        return HrdbClient(club_id="TEST_ID", club_password="TEST_PW")

    @patch("batch.hrdb_client.time.sleep")
    @patch("batch.hrdb_client.requests.get")
    @patch("batch.hrdb_client.requests.post")
    def test_2クエリ同時送信(self, mock_post, mock_get, mock_sleep):
        """query_dual で2つのSQLを同時に送信し、2つの結果を取得."""
        # submit: 2クエリ送信
        submit_resp = MagicMock()
        submit_resp.json.return_value = {"ret1": "QID_A", "ret2": "QID_B"}

        # state: 両方完了
        state_done = MagicMock()
        state_done.json.return_value = {"ret1": "2", "ret2": "2"}

        # geturl: 2つのURL
        geturl_resp = MagicMock()
        geturl_resp.json.return_value = {
            "ret1": "https://example.com/result1.csv",
            "ret2": "https://example.com/result2.csv",
        }

        mock_post.side_effect = [submit_resp, state_done, geturl_resp]

        # CSV downloads
        csv1 = "id,name\r\n1,Alpha\r\n"
        csv2 = "id,name\r\n2,Beta\r\n3,Gamma\r\n"
        csv_resp1 = MagicMock()
        csv_resp1.content = csv1.encode("shift_jis")
        csv_resp2 = MagicMock()
        csv_resp2.content = csv2.encode("shift_jis")
        mock_get.side_effect = [csv_resp1, csv_resp2]

        client = self._make_client()
        result1, result2 = client.query_dual(
            "SELECT * FROM table1",
            "SELECT * FROM table2",
        )

        assert len(result1) == 1
        assert result1[0] == {"id": "1", "name": "Alpha"}
        assert len(result2) == 2
        assert result2[0] == {"id": "2", "name": "Beta"}
        assert result2[1] == {"id": "3", "name": "Gamma"}

        # submit呼び出しの検証
        submit_call = mock_post.call_args_list[0]
        assert submit_call[1]["data"]["cmd1"] == "SELECT * FROM table1"
        assert submit_call[1]["data"]["cmd2"] == "SELECT * FROM table2"

        # state呼び出しの検証
        state_call = mock_post.call_args_list[1]
        assert state_call[1]["data"]["qid1"] == "QID_A"
        assert state_call[1]["data"]["qid2"] == "QID_B"
