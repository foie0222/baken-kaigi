"""IpatGateway ファクトリ."""
import logging
import os

from src.domain.ports.ipat_gateway import IpatGateway

logger = logging.getLogger(__name__)


def create_ipat_gateway() -> IpatGateway:
    """環境変数に基づいてIpatGatewayを生成する.

    IPAT_GATEWAY:
        "mock"     → MockIpatGateway（ローカル開発・テスト用）
        "gambleos" → GambleOsIpatGateway
        未設定      → GambleOsIpatGateway（デフォルト）
    """
    gateway_type = os.environ.get("IPAT_GATEWAY")
    if gateway_type == "mock":
        from src.infrastructure.providers.mock_ipat_gateway import MockIpatGateway

        return MockIpatGateway()

    if gateway_type and gateway_type != "gambleos":
        logger.warning("Unknown IPAT_GATEWAY=%s, falling back to GambleOs", gateway_type)

    from src.infrastructure.providers.gambleos_ipat_gateway import (
        GambleOsIpatGateway,
    )

    return GambleOsIpatGateway()
