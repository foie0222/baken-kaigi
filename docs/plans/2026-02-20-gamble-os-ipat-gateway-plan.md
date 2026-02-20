# GAMBLE-OS IPAT ゲートウェイ移行 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** EC2経由のIPAT投票・残高照会を GAMBLE-OS API 直接呼び出しに置き換え、旧実装を削除する。

**Architecture:** 既存の `IpatGateway` インターフェースを維持したまま、`JraVanIpatGateway`（EC2 → jravan-api）を `GambleOsIpatGateway`（GAMBLE-OS API直接）に差し替える。GAMBLE-OS認証はSecrets Managerから取得し、ユーザーIPAT認証情報は既存の `IpatCredentials` をマッピングして使用する。

**Tech Stack:** Python 3.12, requests, boto3, pytest, unittest.mock

**Design doc:** `docs/plans/2026-02-20-gamble-os-ipat-gateway-design.md`

---

### Task 1: GambleOsIpatGateway — 投票機能

`IpatGateway.submit_bets()` をGAMBLE-OS API向けに実装する。

**Files:**
- Create: `backend/src/infrastructure/providers/gamble_os_ipat_gateway.py`
- Create: `backend/tests/infrastructure/providers/test_gamble_os_ipat_gateway.py`

**Step 1: テストファイル作成 — 投票正常系**

```python
"""GambleOsIpatGateway のテスト."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.domain.enums import IpatBetType, IpatVenueCode
from src.domain.ports import IpatGatewayError
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials


def _make_credentials() -> IpatCredentials:
    return IpatCredentials(
        inet_id="ABcd1234",
        subscriber_number="12345678",
        pin="1234",
        pars_number="5678",
    )


def _make_bet_line(**overrides) -> IpatBetLine:
    defaults = {
        "opdt": "20260222",
        "venue_code": IpatVenueCode.TOKYO,
        "race_number": 11,
        "bet_type": IpatBetType.TANSYO,
        "number": "03",
        "amount": 100,
    }
    defaults.update(overrides)
    return IpatBetLine(**defaults)


class TestSubmitBets:
    """submit_bets のテスト."""

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_投票正常系(self, mock_post, mock_boto_client):
        """ret=0 で True を返す."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "test@example.com", "tncpw": "pass123"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": 0, "msg": "", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        result = gateway.submit_bets(_make_credentials(), [_make_bet_line()])

        assert result is True

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_投票エラー_ret負数でIpatGatewayError(self, mock_post, mock_boto_client):
        """ret=-1 で IpatGatewayError を raise."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "test@example.com", "tncpw": "pass123"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": -1, "msg": "投票エラー", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        with pytest.raises(IpatGatewayError, match="投票エラー"):
            gateway.submit_bets(_make_credentials(), [_make_bet_line()])

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_buyeyeフォーマット_単勝(self, mock_post, mock_boto_client):
        """単勝の buyeye が正しいフォーマットで送信される."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": 0, "msg": "", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        bet_line = _make_bet_line(
            opdt="20260222",
            venue_code=IpatVenueCode.TOKYO,
            race_number=11,
            bet_type=IpatBetType.TANSYO,
            number="03",
            amount=100,
        )
        gateway.submit_bets(_make_credentials(), [bet_line])

        call_kwargs = mock_post.call_args[1]
        data = call_kwargs["data"]
        assert data["buyeye"] == "20260222,05,11,TAN,NORMAL,100,03,:"
        assert data["money"] == "100"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_buyeyeフォーマット_三連単(self, mock_post, mock_boto_client):
        """三連単の buyeye が正しいフォーマットで送信される."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": 0, "msg": "", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        bet_line = _make_bet_line(
            bet_type=IpatBetType.SANRENTAN,
            number="03-01-05",
            amount=200,
        )
        gateway.submit_bets(_make_credentials(), [bet_line])

        call_kwargs = mock_post.call_args[1]
        data = call_kwargs["data"]
        assert data["buyeye"] == "20260222,05,11,SANTAN,NORMAL,200,03-01-05,:"
        assert data["money"] == "200"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_複数買い目のbuyeye結合(self, mock_post, mock_boto_client):
        """複数行がコロン区切りで連結される."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": 0, "msg": "", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        lines = [
            _make_bet_line(bet_type=IpatBetType.TANSYO, number="03", amount=100),
            _make_bet_line(bet_type=IpatBetType.FUKUSYO, number="05", amount=200),
        ]
        gateway.submit_bets(_make_credentials(), lines)

        call_kwargs = mock_post.call_args[1]
        data = call_kwargs["data"]
        assert ":" in data["buyeye"]
        assert data["money"] == "300"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_IPAT認証情報のマッピング(self, mock_post, mock_boto_client):
        """IpatCredentials → GAMBLE-OS パラメータの変換."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": 0, "msg": "", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        creds = _make_credentials()
        gateway.submit_bets(creds, [_make_bet_line()])

        call_kwargs = mock_post.call_args[1]
        data = call_kwargs["data"]
        assert data["uno"] == "12345678"  # subscriber_number
        assert data["pin"] == "1234"  # pin
        assert data["pno"] == "5678"  # pars_number
        assert data["gov"] == "C"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_ドライランモード(self, mock_post, mock_boto_client):
        """dry_run=True で betcd=betchk が送信される."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": 0, "msg": "", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret", dry_run=True)
        gateway.submit_bets(_make_credentials(), [_make_bet_line()])

        call_kwargs = mock_post.call_args[1]
        data = call_kwargs["data"]
        assert data["betcd"] == "betchk"

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_HTTPエラーでIpatGatewayError(self, mock_post, mock_boto_client):
        """HTTPエラーで IpatGatewayError を raise."""
        import requests as req

        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_post.side_effect = req.RequestException("Connection error")

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        with pytest.raises(IpatGatewayError, match="Connection error"):
            gateway.submit_bets(_make_credentials(), [_make_bet_line()])

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_全券種のコード変換(self, mock_post, mock_boto_client):
        """全IpatBetTypeが正しいGAMBLE-OS式別コードに変換される."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": 0, "msg": "", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        expected = {
            IpatBetType.TANSYO: "TAN",
            IpatBetType.FUKUSYO: "FUKU",
            IpatBetType.UMAREN: "UMAFUKU",
            IpatBetType.WIDE: "WIDE",
            IpatBetType.UMATAN: "UMATAN",
            IpatBetType.SANRENPUKU: "SANFUKU",
            IpatBetType.SANRENTAN: "SANTAN",
        }
        gateway = GambleOsIpatGateway(secret_name="test-secret")

        for bet_type, gamble_os_code in expected.items():
            bet_line = _make_bet_line(bet_type=bet_type)
            gateway.submit_bets(_make_credentials(), [bet_line])
            call_kwargs = mock_post.call_args[1]
            buyeye = call_kwargs["data"]["buyeye"]
            assert f",{gamble_os_code}," in buyeye, f"{bet_type.name} → {gamble_os_code}"
```

**Step 2: テスト実行して全件FAILを確認**

Run: `cd backend && uv run pytest tests/infrastructure/providers/test_gamble_os_ipat_gateway.py -v`
Expected: FAIL (ModuleNotFoundError — `gamble_os_ipat_gateway` が存在しない)

**Step 3: 実装**

```python
"""GAMBLE-OS IPAT ゲートウェイ実装.

GAMBLE-OS API経由でIPAT投票・残高照会を行う。
"""
import json
import logging

import boto3
import requests

from src.domain.enums import IpatBetType
from src.domain.ports import IpatGateway, IpatGatewayError
from src.domain.value_objects import IpatBalance, IpatBetLine, IpatCredentials

logger = logging.getLogger(__name__)

BETTING_URL = "https://api.gamble-os.net/systems/ip-bet-kb"
BALANCE_URL = "https://api.gamble-os.net/systems/ip-balance"
TIMEOUT = 30

# IpatBetType → GAMBLE-OS 式別コード
_BET_TYPE_MAP: dict[IpatBetType, str] = {
    IpatBetType.TANSYO: "TAN",
    IpatBetType.FUKUSYO: "FUKU",
    IpatBetType.UMAREN: "UMAFUKU",
    IpatBetType.WIDE: "WIDE",
    IpatBetType.UMATAN: "UMATAN",
    IpatBetType.SANRENPUKU: "SANFUKU",
    IpatBetType.SANRENTAN: "SANTAN",
}


def _build_buyeye_field(line: IpatBetLine) -> str:
    """IpatBetLine を GAMBLE-OS buyeye 1レコードに変換."""
    bet_code = _BET_TYPE_MAP[line.bet_type]
    rno = str(line.race_number).zfill(2)
    return f"{line.opdt},{line.venue_code.value},{rno},{bet_code},NORMAL,{line.amount},{line.number},:"


class GambleOsIpatGateway(IpatGateway):
    """GAMBLE-OS API経由のIPATゲートウェイ."""

    def __init__(self, secret_name: str, *, dry_run: bool = False) -> None:
        self._secret_name = secret_name
        self._dry_run = dry_run
        self._gamble_os_creds: dict | None = None

    def _get_gamble_os_creds(self) -> dict:
        """GAMBLE-OS認証情報をSecrets Managerから取得（キャッシュ）."""
        if self._gamble_os_creds is None:
            sm = boto3.client("secretsmanager")
            secret = sm.get_secret_value(SecretId=self._secret_name)
            self._gamble_os_creds = json.loads(secret["SecretString"])
        return self._gamble_os_creds

    def _base_params(self, credentials: IpatCredentials) -> dict:
        """共通POSTパラメータを生成."""
        go_creds = self._get_gamble_os_creds()
        return {
            "tncid": go_creds["tncid"],
            "tncpw": go_creds["tncpw"],
            "gov": "C",
            "uno": credentials.subscriber_number,
            "pin": credentials.pin,
            "pno": credentials.pars_number,
        }

    def submit_bets(self, credentials: IpatCredentials, bet_lines: list[IpatBetLine]) -> bool:
        """投票を送信する."""
        try:
            buyeye = "".join(_build_buyeye_field(line) for line in bet_lines)
            total_money = sum(line.amount for line in bet_lines)

            data = self._base_params(credentials)
            data["betcd"] = "betchk" if self._dry_run else "bet"
            data["money"] = str(total_money)
            data["buyeye"] = buyeye

            response = requests.post(BETTING_URL, data=data, timeout=TIMEOUT)
            response.raise_for_status()

            result = response.json()
            if result.get("ret", -1) < 0:
                raise IpatGatewayError(result.get("msg", "Unknown betting error"))
            return True
        except requests.RequestException as e:
            raise IpatGatewayError(f"Failed to submit bets: {e}") from e

    def get_balance(self, credentials: IpatCredentials) -> IpatBalance:
        """残高を取得する."""
        try:
            data = self._base_params(credentials)

            response = requests.post(BALANCE_URL, data=data, timeout=TIMEOUT)
            response.raise_for_status()

            result = response.json()
            if result.get("ret", -1) < 0:
                raise IpatGatewayError(result.get("msg", "Unknown balance error"))

            r = result.get("results", {})
            buy_limit = int(r["buy_limit_money"])
            day_buy = int(r["day_buy_money"])
            total_buy = int(r["total_buy_money"])

            return IpatBalance(
                bet_dedicated_balance=day_buy,
                settle_possible_balance=total_buy,
                bet_balance=buy_limit - day_buy,
                limit_vote_amount=buy_limit,
            )
        except requests.RequestException as e:
            raise IpatGatewayError(f"Failed to get balance: {e}") from e
        except (KeyError, TypeError) as e:
            raise IpatGatewayError(
                f"Failed to get balance: missing field {e} in response"
            ) from e
```

**Step 4: テスト実行して全件PASSを確認**

Run: `cd backend && uv run pytest tests/infrastructure/providers/test_gamble_os_ipat_gateway.py -v`
Expected: 全件 PASS

**Step 5: コミット**

```bash
git add backend/src/infrastructure/providers/gamble_os_ipat_gateway.py backend/tests/infrastructure/providers/test_gamble_os_ipat_gateway.py
git commit -m "feat: GambleOsIpatGateway — 投票機能実装"
```

---

### Task 2: GambleOsIpatGateway — 残高照会テスト追加

投票テストと同じファイルに残高照会テストを追加する。

**Files:**
- Modify: `backend/tests/infrastructure/providers/test_gamble_os_ipat_gateway.py`

**Step 1: 残高照会テストを追加**

テストファイル末尾に以下を追加:

```python
class TestGetBalance:
    """get_balance のテスト."""

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_残高取得正常系(self, mock_post, mock_boto_client):
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ret": 0,
            "msg": "",
            "results": {
                "day_buy_money": "5000",
                "day_refund_money": "0",
                "total_buy_money": "30000",
                "total_refund_money": "8000",
                "buy_limit_money": "100000",
                "buy_possible_count": "10",
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        balance = gateway.get_balance(_make_credentials())

        assert isinstance(balance, IpatBalance)
        assert balance.limit_vote_amount == 100000
        assert balance.bet_dedicated_balance == 5000
        assert balance.bet_balance == 95000  # 100000 - 5000
        assert balance.settle_possible_balance == 30000

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_残高取得エラー_ret負数(self, mock_post, mock_boto_client):
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": -1, "msg": "認証エラー", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        with pytest.raises(IpatGatewayError, match="認証エラー"):
            gateway.get_balance(_make_credentials())

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_残高取得エラー_フィールド欠損(self, mock_post, mock_boto_client):
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {"ret": 0, "msg": "", "results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        with pytest.raises(IpatGatewayError, match="missing field"):
            gateway.get_balance(_make_credentials())

    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.boto3.client")
    @patch("src.infrastructure.providers.gamble_os_ipat_gateway.requests.post")
    def test_残高照会のエンドポイント(self, mock_post, mock_boto_client):
        """残高照会は ip-balance エンドポイントを使用."""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            "SecretString": json.dumps({"tncid": "t@e.com", "tncpw": "pw"})
        }
        mock_boto_client.return_value = mock_sm

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ret": 0, "msg": "",
            "results": {
                "day_buy_money": "0", "day_refund_money": "0",
                "total_buy_money": "0", "total_refund_money": "0",
                "buy_limit_money": "100000", "buy_possible_count": "10",
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

        gateway = GambleOsIpatGateway(secret_name="test-secret")
        gateway.get_balance(_make_credentials())

        url = mock_post.call_args[0][0]
        assert url == "https://api.gamble-os.net/systems/ip-balance"
```

**Step 2: テスト実行**

Run: `cd backend && uv run pytest tests/infrastructure/providers/test_gamble_os_ipat_gateway.py -v`
Expected: 全件 PASS

**Step 3: コミット**

```bash
git add backend/tests/infrastructure/providers/test_gamble_os_ipat_gateway.py
git commit -m "test: GambleOsIpatGateway — 残高照会テスト追加"
```

---

### Task 3: 依存注入の差し替え

`Dependencies.get_ipat_gateway()` を `GambleOsIpatGateway` に差し替える。

**Files:**
- Modify: `backend/src/api/dependencies.py:130-143`

**Step 1: 変更内容**

`get_ipat_gateway()` メソッドを変更:

```python
# Before (L130-143):
    @classmethod
    def get_ipat_gateway(cls) -> IpatGateway:
        """IPATゲートウェイを取得する."""
        if cls._ipat_gateway is None:
            if os.environ.get("JRAVAN_API_URL") is not None:
                from src.infrastructure.providers.jravan_ipat_gateway import (
                    JraVanIpatGateway,
                )

                cls._ipat_gateway = JraVanIpatGateway()
            else:
                from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway

                cls._ipat_gateway = MockIpatGateway()
        return cls._ipat_gateway

# After:
    @classmethod
    def get_ipat_gateway(cls) -> IpatGateway:
        """IPATゲートウェイを取得する."""
        if cls._ipat_gateway is None:
            secret_name = os.environ.get("GAMBLE_OS_SECRET_NAME")
            if secret_name is not None:
                from src.infrastructure.providers.gamble_os_ipat_gateway import (
                    GambleOsIpatGateway,
                )

                cls._ipat_gateway = GambleOsIpatGateway(secret_name=secret_name)
            else:
                from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway

                cls._ipat_gateway = MockIpatGateway()
        return cls._ipat_gateway
```

**Step 2: 既存テストが壊れていないことを確認**

Run: `cd backend && uv run pytest tests/api/ -v -k ipat`
Expected: 全件 PASS

**Step 3: コミット**

```bash
git add backend/src/api/dependencies.py
git commit -m "refactor: 依存注入をGambleOsIpatGatewayに差し替え"
```

---

### Task 4: auto_bet_executor の差し替え

`auto_bet_executor.py` から `JraVanIpatGateway` 依存を `GambleOsIpatGateway` に変更する。

**Files:**
- Modify: `backend/batch/auto_bet_executor.py:33,44,181`

**Step 1: 変更内容**

```python
# Before (L33):
from src.infrastructure.providers.jravan_ipat_gateway import JraVanIpatGateway

# After:
from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway

# Before (L44):
JRAVAN_API_URL = os.environ.get("JRAVAN_API_URL", "http://10.0.1.100:8000")

# After:
JRAVAN_API_URL = os.environ.get("JRAVAN_API_URL", "http://10.0.1.100:8000")  # オッズ取得用（EC2依存）
GAMBLE_OS_SECRET_NAME = os.environ["GAMBLE_OS_SECRET_NAME"]

# Before (L181):
    gateway = JraVanIpatGateway(base_url=JRAVAN_API_URL)

# After:
    gateway = GambleOsIpatGateway(secret_name=GAMBLE_OS_SECRET_NAME)
```

**Step 2: テスト実行**

Run: `cd backend && uv run pytest tests/batch/ -v -k auto_bet`
Expected: PASS（テストはモックを使っているため影響なし）

**Step 3: コミット**

```bash
git add backend/batch/auto_bet_executor.py
git commit -m "refactor: auto_bet_executorをGambleOsIpatGatewayに差し替え"
```

---

### Task 5: CDK — auto_bet_executor の環境変数更新

`batch_stack.py` で auto_bet_executor Lambda に `GAMBLE_OS_SECRET_NAME` を追加し、Secrets Manager読み取り権限を付与する。

**Files:**
- Modify: `cdk/stacks/batch_stack.py`
- Modify: `cdk/tests/test_batch_stack.py`（必要に応じて）

**Step 1: 変更内容**

`auto_bet_executor_props` の `environment` に追加:

```python
# batch_stack.py の auto_bet_executor_props["environment"] に追加:
"GAMBLE_OS_SECRET_NAME": gamble_os_secret.secret_name,
```

Secrets Manager 権限に `baken-kaigi/gamble-os-credentials` を追加:

```python
# 既存の ipat/* 権限の後に追加:
gamble_os_secret.grant_read(auto_bet_executor_fn)
```

VPC内配置の条件分岐は残す（オッズ取得で `JRAVAN_API_URL` をまだ使うため）。

**Step 2: CDKテスト実行**

Run: `cd cdk && npx cdk synth --context jravan=true -q 2>&1 | tail -5`
Run: `cd cdk && uv run pytest tests/test_batch_stack.py -v`
Expected: PASS

**Step 3: コミット**

```bash
git add cdk/stacks/batch_stack.py cdk/tests/test_batch_stack.py
git commit -m "feat: auto_bet_executorにGAMBLE_OS_SECRET_NAME環境変数追加"
```

---

### Task 6: 旧実装の削除

`JraVanIpatGateway` とそのテストを削除する。

**Files:**
- Delete: `backend/src/infrastructure/providers/jravan_ipat_gateway.py`
- Delete: `backend/tests/infrastructure/providers/test_jravan_ipat_gateway.py`

**Step 1: 旧実装への参照がないことを確認**

Run: `cd backend && grep -r "jravan_ipat_gateway\|JraVanIpatGateway" --include="*.py" .`
Expected: 0件（削除対象ファイル自身のみ）

**Step 2: ファイル削除**

```bash
rm backend/src/infrastructure/providers/jravan_ipat_gateway.py
rm backend/tests/infrastructure/providers/test_jravan_ipat_gateway.py
```

**Step 3: 全テスト実行して回帰なしを確認**

Run: `cd backend && uv run pytest -x -q`
Expected: 全件 PASS、FAILなし

**Step 4: コミット**

```bash
git add -u backend/src/infrastructure/providers/jravan_ipat_gateway.py backend/tests/infrastructure/providers/test_jravan_ipat_gateway.py
git commit -m "chore: JraVanIpatGateway削除（GAMBLE-OS APIに移行済み）"
```

---

### Task 7: 回帰テスト + PR作成

全テストスイートを実行し、PRを作成する。

**Step 1: バックエンド全テスト**

Run: `cd backend && uv run pytest -q`
Expected: 全件 PASS

**Step 2: CDK全テスト**

Run: `cd cdk && uv run pytest -q`
Expected: 全件 PASS

**Step 3: PR作成**

```bash
git push -u origin feature/gamble-os-ipat-gateway
gh pr create --title "feat: GAMBLE-OS IPATゲートウェイ移行" --body "..."
```
