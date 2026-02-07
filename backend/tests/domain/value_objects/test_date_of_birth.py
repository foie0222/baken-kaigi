"""DateOfBirth値オブジェクトのテスト."""
from datetime import date, timedelta

import pytest

from src.domain.value_objects import DateOfBirth


class TestDateOfBirth:
    """DateOfBirthのテスト."""

    def test_20歳以上で生成できる(self):
        dob = DateOfBirth(date(2000, 1, 1))
        assert dob.value == date(2000, 1, 1)

    def test_ちょうど20歳で生成できる(self):
        today = date.today()
        twentieth_birthday = date(today.year - 20, today.month, today.day)
        dob = DateOfBirth(twentieth_birthday)
        assert dob.age() == 20

    def test_19歳でValueErrorが発生する(self):
        today = date.today()
        nineteenth_birthday = date(today.year - 19, today.month, today.day)
        with pytest.raises(ValueError, match="at least 20"):
            DateOfBirth(nineteenth_birthday)

    def test_未来日でValueErrorが発生する(self):
        with pytest.raises(ValueError, match="cannot be in the future"):
            DateOfBirth(date.today() + timedelta(days=1))

    def test_年齢計算(self):
        today = date.today()
        dob = DateOfBirth(date(today.year - 30, today.month, today.day))
        assert dob.age() == 30

    def test_誕生日前の年齢計算(self):
        today = date.today()
        # 明日が誕生日の場合（まだ誕生日を迎えていない）
        if today.month == 12 and today.day == 31:
            birthday = date(today.year - 30, 1, 1)
        else:
            tomorrow = today + timedelta(days=1)
            birthday = date(today.year - 30, tomorrow.month, tomorrow.day)
        dob = DateOfBirth(birthday)
        assert dob.age() == 29

    def test_str表現(self):
        dob = DateOfBirth(date(2000, 6, 15))
        assert str(dob) == "2000-06-15"

    def test_不変性(self):
        dob = DateOfBirth(date(2000, 1, 1))
        with pytest.raises(AttributeError):
            dob.value = date(1990, 1, 1)  # type: ignore
