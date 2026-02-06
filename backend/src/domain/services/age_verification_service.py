"""年齢確認ドメインサービス."""
from datetime import date


class AgeVerificationService:
    """年齢確認サービス."""

    MINIMUM_AGE = 20

    @staticmethod
    def is_eligible(date_of_birth: date) -> bool:
        """馬券購入の年齢要件を満たしているか判定する."""
        today = date.today()
        age = today.year - date_of_birth.year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1
        return age >= AgeVerificationService.MINIMUM_AGE

    @staticmethod
    def calculate_age(date_of_birth: date) -> int:
        """年齢を計算する."""
        today = date.today()
        age = today.year - date_of_birth.year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1
        return age
