"""IpatExecutorのテスト."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# テスト対象モジュールへのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from ipat_executor import IpatExecutor


class TestIpatExecutor:
    """IpatExecutorの単体テスト."""

    def setup_method(self) -> None:
        """テスト前の準備."""
        self.executor = IpatExecutor()

    def test_CSVファイルを正しく書き出す(self, tmp_path: Path) -> None:
        """CSVファイルが正しいフォーマットで書き出されることを確認."""
        csv_path = tmp_path / "test.csv"
        bet_lines = [
            {
                "opdt": "20260201",
                "rcoursecd": "05",
                "rno": "11",
                "denomination": "tansyo",
                "method": "NORMAL",
                "multi": "",
                "number": "03",
                "bet_price": "100",
            },
        ]

        self.executor._write_csv(bet_lines, str(csv_path))

        content = csv_path.read_text()
        assert content.strip() == "20260201,05,11,tansyo,NORMAL,,03,100"

    def test_CSVファイル複数行を書き出す(self, tmp_path: Path) -> None:
        """複数行のCSVファイルが正しく書き出されることを確認."""
        csv_path = tmp_path / "test.csv"
        bet_lines = [
            {
                "opdt": "20260201",
                "rcoursecd": "05",
                "rno": "11",
                "denomination": "tansyo",
                "method": "NORMAL",
                "multi": "",
                "number": "03",
                "bet_price": "100",
            },
            {
                "opdt": "20260201",
                "rcoursecd": "05",
                "rno": "11",
                "denomination": "umaren",
                "method": "NORMAL",
                "multi": "",
                "number": "01-03",
                "bet_price": "500",
            },
        ]

        self.executor._write_csv(bet_lines, str(csv_path))

        lines = csv_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "20260201,05,11,tansyo,NORMAL,,03,100"
        assert lines[1] == "20260201,05,11,umaren,NORMAL,,01-03,500"

    def test_ipatgoが存在しない場合voteがエラーを返す(self, tmp_path: Path) -> None:
        """ipatgo.exeが存在しない場合、voteがエラーを返すことを確認."""
        self.executor.ipatgo_path = str(tmp_path / "nonexistent" / "ipatgo.exe")

        bet_lines = [
            {
                "opdt": "20260201",
                "rcoursecd": "05",
                "rno": "11",
                "denomination": "tansyo",
                "method": "NORMAL",
                "multi": "",
                "number": "03",
                "bet_price": "100",
            },
        ]

        result = self.executor.vote("ABcd1234", "12345678", "1234", "5678", bet_lines)

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_ipatgoが存在しない場合statがエラーを返す(self, tmp_path: Path) -> None:
        """ipatgo.exeが存在しない場合、statがエラーを返すことを確認."""
        self.executor.ipatgo_path = str(tmp_path / "nonexistent" / "ipatgo.exe")

        result = self.executor.stat("ABcd1234", "12345678", "1234", "5678")

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_ipatgoパスが空文字の場合エラーを返す(self) -> None:
        """IPATGO_PATHが空文字の場合、エラーを返すことを確認."""
        self.executor.ipatgo_path = ""

        result = self.executor.stat("ABcd1234", "12345678", "1234", "5678")

        assert result["success"] is False
        assert "empty" in result["message"].lower()

    @patch("ipat_executor.IpatExecutor._check_ipatgo", return_value=None)
    @patch("subprocess.run")
    def test_voteでsubprocessが呼ばれる(self, mock_run: MagicMock, _mock_check: MagicMock) -> None:
        """voteメソッドでsubprocess.runが正しく呼ばれることを確認."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK")

        bet_lines = [
            {
                "opdt": "20260201",
                "rcoursecd": "05",
                "rno": "11",
                "denomination": "tansyo",
                "method": "NORMAL",
                "multi": "",
                "number": "03",
                "bet_price": "100",
            },
        ]

        result = self.executor.vote("ABcd1234", "12345678", "1234", "5678", bet_lines)

        assert mock_run.called
        assert result["success"] is True

    @patch("ipat_executor.IpatExecutor._check_ipatgo", return_value=None)
    @patch("subprocess.run")
    def test_vote失敗時にエラーを返す(self, mock_run: MagicMock, _mock_check: MagicMock) -> None:
        """voteメソッドでsubprocess失敗時にerrorステータスを返すことを確認."""
        mock_run.return_value = MagicMock(returncode=1, stdout="ERROR")

        bet_lines = [
            {
                "opdt": "20260201",
                "rcoursecd": "05",
                "rno": "11",
                "denomination": "tansyo",
                "method": "NORMAL",
                "multi": "",
                "number": "03",
                "bet_price": "100",
            },
        ]

        result = self.executor.vote("ABcd1234", "12345678", "1234", "5678", bet_lines)

        assert result["success"] is False

    @patch("ipat_executor.IpatExecutor._check_ipatgo", return_value=None)
    @patch("subprocess.run")
    def test_statでsubprocessが呼ばれる(self, mock_run: MagicMock, _mock_check: MagicMock) -> None:
        """statメソッドでsubprocess.runが正しく呼ばれることを確認."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK")

        # stat.iniのモック（ipatgo.exeの実際の出力キー名）
        ini_content = """[stat]
total_vote_amount=10000
total_repayment=5000
daily_vote_amount=15000
limit_vote_amount=100000
"""
        with patch("builtins.open", mock_open(read_data=ini_content)):
            result = self.executor.stat("ABcd1234", "12345678", "1234", "5678")

        assert result["success"] is True
        assert result["bet_dedicated_balance"] == 10000
        assert result["settle_possible_balance"] == 5000
        assert result["bet_balance"] == 15000
        assert result["limit_vote_amount"] == 100000

    @patch("ipat_executor.IpatExecutor._check_ipatgo", return_value=None)
    @patch("subprocess.run")
    def test_stat失敗時にエラーを返す(self, mock_run: MagicMock, _mock_check: MagicMock) -> None:
        """statメソッドでsubprocess失敗時にerrorステータスを返すことを確認."""
        mock_run.return_value = MagicMock(returncode=1, stdout="ERROR")

        result = self.executor.stat("ABcd1234", "12345678", "1234", "5678")

        assert result["success"] is False

    def test_parse_stat_iniで正しくパースされる(self) -> None:
        """_parse_stat_iniでstat.iniが正しくパースされることを確認."""
        ini_content = """[stat]
total_vote_amount=10000
total_repayment=5000
daily_vote_amount=15000
limit_vote_amount=100000
"""
        with patch("builtins.open", mock_open(read_data=ini_content)):
            result = self.executor._parse_stat_ini()

        assert result["bet_dedicated_balance"] == 10000
        assert result["settle_possible_balance"] == 5000
        assert result["bet_balance"] == 15000
        assert result["limit_vote_amount"] == 100000

    def test_parse_stat_iniでstatセクションがない場合全て0を返す(self) -> None:
        """stat.iniに[stat]セクションがない場合、全て0を返すことを確認."""
        ini_content = """[other]
key=value
"""
        with patch("builtins.open", mock_open(read_data=ini_content)):
            result = self.executor._parse_stat_ini()

        assert result["bet_dedicated_balance"] == 0
        assert result["settle_possible_balance"] == 0
        assert result["bet_balance"] == 0
        assert result["limit_vote_amount"] == 0

    def test_parse_stat_iniでキーが欠落している場合デフォルト0を返す(self) -> None:
        """stat.iniの一部キーが欠落している場合、デフォルト0を返すことを確認."""
        ini_content = """[stat]
total_vote_amount=5000
limit_vote_amount=200000
"""
        with patch("builtins.open", mock_open(read_data=ini_content)):
            result = self.executor._parse_stat_ini()

        assert result["bet_dedicated_balance"] == 5000
        assert result["settle_possible_balance"] == 0
        assert result["bet_balance"] == 0
        assert result["limit_vote_amount"] == 200000
