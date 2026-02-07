"""IPAT投票実行モジュール.

ipatgo.exe を利用してIPAT投票と残高照会を行う。
"""
import configparser
import subprocess
import tempfile
from pathlib import Path


class IpatExecutor:
    """IPAT投票を実行するクラス."""

    IPATGO_PATH = r"C:\umagen\ipatgo\ipatgo.exe"
    STAT_INI_PATH = r"C:\umagen\ipatgo\stat.ini"

    def vote(self, card: str, birthday: str, pin: str, dummy: str, bet_lines: list[dict]) -> dict:
        """投票を実行する."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = f.name
            self._write_csv(bet_lines, csv_path)

        try:
            result = subprocess.run(
                [self.IPATGO_PATH, "file", csv_path, card, birthday, pin, dummy],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return {"status": "ok"}
            else:
                return {"status": "error", "message": result.stdout}
        finally:
            Path(csv_path).unlink(missing_ok=True)

    def stat(self, card: str, birthday: str, pin: str, dummy: str) -> dict:
        """残高照会を実行する."""
        result = subprocess.run(
            [self.IPATGO_PATH, "stat", card, birthday, pin, dummy],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return {"status": "error", "message": result.stdout}

        data = self._parse_stat_ini()
        return {"status": "ok", "data": data}

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
        with open(self.STAT_INI_PATH) as f:
            config.read_file(f)

        return {
            "bet_dedicated_balance": int(config["stat"]["bet_dedicated_balance"]),
            "settle_possible_balance": int(config["stat"]["settle_possible_balance"]),
            "bet_balance": int(config["stat"]["bet_balance"]),
            "limit_vote_amount": int(config["stat"]["limit_vote_amount"]),
        }
