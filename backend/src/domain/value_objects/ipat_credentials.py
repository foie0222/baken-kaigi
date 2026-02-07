"""IPAT認証情報を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpatCredentials:
    """IPAT投票に必要な認証情報."""

    inet_id: str
    subscriber_number: str
    pin: str
    pars_number: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.inet_id.isalnum() or len(self.inet_id) != 8:
            raise ValueError("INET-IDは8桁の英数字である必要があります")
        if not self.subscriber_number.isdigit() or len(self.subscriber_number) != 8:
            raise ValueError("加入者番号は8桁の数字である必要があります")
        if not self.pin.isdigit() or len(self.pin) != 4:
            raise ValueError("暗証番号は4桁の数字である必要があります")
        if not self.pars_number.isdigit() or len(self.pars_number) != 4:
            raise ValueError("P-ARS番号は4桁の数字である必要があります")
