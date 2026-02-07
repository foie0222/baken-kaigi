"""IPAT認証情報を表現する値オブジェクト."""
from __future__ import annotations

import re
from dataclasses import dataclass

_ASCII_ALNUM_8 = re.compile(r"^[A-Za-z0-9]{8}$")
_DIGITS_8 = re.compile(r"^\d{8}$")
_DIGITS_4 = re.compile(r"^\d{4}$")


@dataclass(frozen=True)
class IpatCredentials:
    """IPAT投票に必要な認証情報."""

    inet_id: str
    subscriber_number: str
    pin: str
    pars_number: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not _ASCII_ALNUM_8.match(self.inet_id):
            raise ValueError("INET-IDは8桁の英数字である必要があります")
        if not _DIGITS_8.match(self.subscriber_number):
            raise ValueError("加入者番号は8桁の数字である必要があります")
        if not _DIGITS_4.match(self.pin):
            raise ValueError("暗証番号は4桁の数字である必要があります")
        if not _DIGITS_4.match(self.pars_number):
            raise ValueError("P-ARS番号は4桁の数字である必要があります")
