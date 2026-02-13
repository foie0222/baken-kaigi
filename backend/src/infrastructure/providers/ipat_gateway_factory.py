"""IpatGateway ファクトリ."""
import os

from src.domain.ports.ipat_gateway import IpatGateway


def create_ipat_gateway() -> IpatGateway:
    """環境変数に基づいてIpatGatewayを生成する.

    IPAT_GATEWAY:
        "gambleos" → GambleOsIpatGateway
        未設定      → MockIpatGateway
    """
    gateway_type = os.environ.get("IPAT_GATEWAY", "")
    if gateway_type == "gambleos":
        from src.infrastructure.providers.gambleos_ipat_gateway import (
            GambleOsIpatGateway,
        )

        return GambleOsIpatGateway()
    else:
        from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway

        return MockIpatGateway()
