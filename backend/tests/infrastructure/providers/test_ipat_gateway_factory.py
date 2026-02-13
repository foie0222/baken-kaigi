"""IpatGateway ファクトリのテスト."""
from unittest.mock import patch

from src.infrastructure.providers.ipat_gateway_factory import create_ipat_gateway


class TestCreateIpatGateway:

    def test_環境変数gambleosでGambleOsGatewayを返す(self):
        with patch.dict("os.environ", {"IPAT_GATEWAY": "gambleos"}):
            from src.infrastructure.providers.gambleos_ipat_gateway import (
                GambleOsIpatGateway,
            )

            gw = create_ipat_gateway()
            assert isinstance(gw, GambleOsIpatGateway)

    def test_環境変数未設定でMockGatewayを返す(self):
        with patch.dict("os.environ", {}, clear=True):
            from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway

            gw = create_ipat_gateway()
            assert isinstance(gw, MockIpatGateway)
