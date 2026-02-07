"""IPAT認証情報を表現する値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IpatCredentials:
    """IPAT投票に必要な認証情報."""

    card_number: str
    birthday: str
    pin: str
    dummy_pin: str

    def __post_init__(self) -> None:
        """バリデーション."""
        if not self.card_number.isdigit() or len(self.card_number) != 12:
            raise ValueError("カード番号は12桁の数字である必要があります")
        if not self.birthday.isdigit() or len(self.birthday) != 8:
            raise ValueError("誕生日はYYYYMMDD形式の8桁の数字である必要があります")
        if not self.pin.isdigit() or len(self.pin) != 4:
            raise ValueError("PINは4桁の数字である必要があります")
        if not self.dummy_pin.isdigit() or len(self.dummy_pin) != 4:
            raise ValueError("ダミーPINは4桁の数字である必要があります")
