"""IPAT投票実行モジュール.

ipatgo.exe を利用してIPAT投票と残高照会を行う。
"""
import configparser
import os
import subprocess
import tempfile
from pathlib import Path

SUBPROCESS_TIMEOUT = 120


class IpatExecutor:
    """IPAT投票を実行するクラス."""

    def __init__(self) -> None:
        """初期化."""
        self.ipatgo_path = os.environ.get(
            "IPATGO_PATH", r"C:\umagen\ipatgo\ipatgo.exe"
        )
        self.stat_ini_path = os.environ.get(
            "STAT_INI_PATH", r"C:\umagen\ipatgo\stat.ini"
        )

    def _check_ipatgo(self) -> str | None:
        """ipatgo.exe の存在を確認する.

        Returns:
            エラーメッセージ。問題なければ None。
        """
        if not Path(self.ipatgo_path).exists():
            return f"ipatgo.exe not found at {self.ipatgo_path}"
        return None

    def vote(self, inet_id: str, subscriber_number: str, pin: str, pars_number: str, bet_lines: list[dict]) -> dict:
        """投票を実行する."""
        if err := self._check_ipatgo():
            return {"success": False, "message": err}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = f.name
            self._write_csv(bet_lines, csv_path)

        try:
            result = subprocess.run(
                [self.ipatgo_path, "file", inet_id, subscriber_number, pin, pars_number, csv_path],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
            )

            if result.returncode == 0:
                return {"success": True}
            else:
                return {"success": False, "message": result.stdout}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "ipatgo.exe timed out"}
        finally:
            Path(csv_path).unlink(missing_ok=True)

    def stat(self, inet_id: str, subscriber_number: str, pin: str, pars_number: str) -> dict:
        """残高照会を実行する."""
        if err := self._check_ipatgo():
            return {"success": False, "message": err}

        try:
            result = subprocess.run(
                [self.ipatgo_path, "stat", inet_id, subscriber_number, pin, pars_number],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "ipatgo.exe timed out"}

        if result.returncode != 0:
            return {"success": False, "message": result.stdout}

        data = self._parse_stat_ini()
        return {"success": True, **data}

    def _write_csv(self, bet_lines: list[dict], path: str) -> None:
        """CSVファイルを書き出す."""
        with open(path, "w") as f:
            for line in bet_lines:
                csv_line = ",".join([
                    line["opdt"],
                    line["rcoursecd"],
                    line["rno"],
                    line["denomination"],
                    line["method"],
                    line["multi"],
                    line["number"],
                    line["bet_price"],
                ])
                f.write(csv_line + "\n")

    def _parse_stat_ini(self) -> dict:
        """stat.iniをパースする."""
        config = configparser.ConfigParser()
        with open(self.stat_ini_path) as f:
            config.read_file(f)

        return {
            "bet_dedicated_balance": int(config["stat"]["bet_dedicated_balance"]),
            "settle_possible_balance": int(config["stat"]["settle_possible_balance"]),
            "bet_balance": int(config["stat"]["bet_balance"]),
            "limit_vote_amount": int(config["stat"]["limit_vote_amount"]),
        }
