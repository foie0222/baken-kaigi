"""DynamoDB共通ユーティリティのテスト."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from batch.dynamodb_utils import convert_floats


class TestConvertFloats:
    """convert_floatsのテスト."""

    def test_floatをDecimalに変換(self):
        """正常系: float値がDecimalに変換される."""
        assert convert_floats(17.1) == Decimal("17.1")
        assert isinstance(convert_floats(17.1), Decimal)

    def test_intはそのまま(self):
        """正常系: int値は変換されない."""
        assert convert_floats(42) == 42
        assert isinstance(convert_floats(42), int)

    def test_strはそのまま(self):
        """正常系: 文字列は変換されない."""
        assert convert_floats("hello") == "hello"

    def test_dictのfloat値を変換(self):
        """正常系: dict内のfloat値が再帰的に変換される."""
        result = convert_floats({"score": 17.1, "name": "馬A", "rank": 1})
        assert result["score"] == Decimal("17.1")
        assert isinstance(result["score"], Decimal)
        assert result["name"] == "馬A"
        assert result["rank"] == 1

    def test_listのfloat値を変換(self):
        """正常系: list内のfloat値が再帰的に変換される."""
        result = convert_floats([17.1, 8.5, "text", 3])
        assert result[0] == Decimal("17.1")
        assert result[1] == Decimal("8.5")
        assert result[2] == "text"
        assert result[3] == 3

    def test_ネストされた構造を再帰変換(self):
        """正常系: ネストされたdict/list内のfloat値も変換される."""
        data = [
            {"score": 52.4, "horse_number": 5, "nested": {"value": 3.14}},
            {"score": 49.2, "horse_number": 3},
        ]
        result = convert_floats(data)

        assert result[0]["score"] == Decimal("52.4")
        assert result[0]["nested"]["value"] == Decimal("3.14")
        assert result[1]["score"] == Decimal("49.2")
        assert result[0]["horse_number"] == 5

    def test_空リスト(self):
        """正常系: 空リストはそのまま."""
        assert convert_floats([]) == []

    def test_空dict(self):
        """正常系: 空dictはそのまま."""
        assert convert_floats({}) == {}

    def test_Noneはそのまま(self):
        """正常系: Noneは変換されない."""
        assert convert_floats(None) is None
