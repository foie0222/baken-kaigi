"""AgeVerificationServiceのテスト."""
from datetime import date

from src.domain.services import AgeVerificationService


class TestAgeVerificationService:
    """年齢確認サービスのテスト."""

    def test_20歳以上は適格(self):
        today = date.today()
        dob = date(today.year - 25, today.month, today.day)
        assert AgeVerificationService.is_eligible(dob) is True

    def test_ちょうど20歳は適格(self):
        today = date.today()
        dob = date(today.year - 20, today.month, today.day)
        assert AgeVerificationService.is_eligible(dob) is True

    def test_19歳は不適格(self):
        today = date.today()
        dob = date(today.year - 19, today.month, today.day)
        assert AgeVerificationService.is_eligible(dob) is False

    def test_年齢計算_30歳(self):
        today = date.today()
        dob = date(today.year - 30, today.month, today.day)
        assert AgeVerificationService.calculate_age(dob) == 30
