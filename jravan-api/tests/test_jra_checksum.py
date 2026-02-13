"""JRAチェックサム計算のテスト."""
import sys
from pathlib import Path

import pytest

# テスト対象モジュールへのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import calculate_jra_checksum


class TestCalculateJraChecksum:
    """calculate_jra_checksum関数の単体テスト."""

    def test_1R_日目1_base_value_243(self) -> None:
        """1日目1Rのチェックサムはbase_valueそのまま."""
        result = calculate_jra_checksum(base_value=243, kaisai_nichime=1, race_number=1)
        assert result == 243

    def test_1R_日目2_base_value_243(self) -> None:
        """2日目1Rのチェックサムは(base + 48) mod 256."""
        # (243 + 48) mod 256 = 291 mod 256 = 35
        result = calculate_jra_checksum(base_value=243, kaisai_nichime=2, race_number=1)
        assert result == 35

    def test_1R_日目8_base_value_243(self) -> None:
        """8日目1Rのチェックサムは(base + 7*48) mod 256."""
        # (243 + 7*48) mod 256 = (243 + 336) mod 256 = 579 mod 256 = 67
        result = calculate_jra_checksum(base_value=243, kaisai_nichime=8, race_number=1)
        assert result == 67

    def test_2R_日目1_base_value_243(self) -> None:
        """1日目2Rのチェックサムは(1R + 181) mod 256."""
        # 1R = 243, 2R = (243 + 181) mod 256 = 424 mod 256 = 168
        result = calculate_jra_checksum(base_value=243, kaisai_nichime=1, race_number=2)
        assert result == 168

    def test_9R_日目1_base_value_243(self) -> None:
        """1日目9Rのチェックサムは(1R + 181*8) mod 256."""
        # 1R = 243, 9R = (243 + 181*8) mod 256 = (243 + 1448) mod 256 = 1691 mod 256 = 155
        result = calculate_jra_checksum(base_value=243, kaisai_nichime=1, race_number=9)
        assert result == 155

    def test_10R_日目1_base_value_243(self) -> None:
        """1日目10Rのチェックサムは(9R + 245) mod 256."""
        # 9R = 155, 10R = (155 + 245) mod 256 = 400 mod 256 = 144
        result = calculate_jra_checksum(base_value=243, kaisai_nichime=1, race_number=10)
        assert result == 144

    def test_11R_日目1_base_value_243(self) -> None:
        """1日目11Rのチェックサムは(10R + 181) mod 256."""
        # 10R = 144, 11R = (144 + 181) mod 256 = 325 mod 256 = 69
        result = calculate_jra_checksum(base_value=243, kaisai_nichime=1, race_number=11)
        assert result == 69

    def test_12R_日目1_base_value_243(self) -> None:
        """1日目12Rのチェックサムは(11R + 181) mod 256."""
        # 11R = 69, 12R = (69 + 181) mod 256 = 250
        result = calculate_jra_checksum(base_value=243, kaisai_nichime=1, race_number=12)
        assert result == 250

    def test_全レースが0から255の範囲内(self) -> None:
        """全てのチェックサムが0-255の範囲内であることを確認."""
        for base in [0, 127, 255]:
            for nichime in range(1, 13):
                for race_num in range(1, 13):
                    result = calculate_jra_checksum(base, nichime, race_num)
                    assert result is not None
                    assert 0 <= result <= 255, f"Out of range: base={base}, nichime={nichime}, race={race_num} => {result}"

    def test_境界値_日目0_はNone(self) -> None:
        """日目が0の場合はNoneを返す."""
        result = calculate_jra_checksum(base_value=100, kaisai_nichime=0, race_number=1)
        assert result is None

    def test_境界値_日目13_はNone(self) -> None:
        """日目が13の場合はNoneを返す."""
        result = calculate_jra_checksum(base_value=100, kaisai_nichime=13, race_number=1)
        assert result is None

    def test_境界値_レース番号0_はNone(self) -> None:
        """レース番号が0の場合はNoneを返す."""
        result = calculate_jra_checksum(base_value=100, kaisai_nichime=1, race_number=0)
        assert result is None

    def test_境界値_レース番号13_はNone(self) -> None:
        """レース番号が13の場合はNoneを返す."""
        result = calculate_jra_checksum(base_value=100, kaisai_nichime=1, race_number=13)
        assert result is None

    def test_境界値_負の日目_はNone(self) -> None:
        """日目が負の場合はNoneを返す."""
        result = calculate_jra_checksum(base_value=100, kaisai_nichime=-1, race_number=1)
        assert result is None

    def test_境界値_負のレース番号_はNone(self) -> None:
        """レース番号が負の場合はNoneを返す."""
        result = calculate_jra_checksum(base_value=100, kaisai_nichime=1, race_number=-1)
        assert result is None

    def test_base_value_0でも正しく計算(self) -> None:
        """base_valueが0でも正しく計算される."""
        # 1日目1R = 0
        result = calculate_jra_checksum(base_value=0, kaisai_nichime=1, race_number=1)
        assert result == 0
        # 1日目2R = (0 + 181) mod 256 = 181
        result = calculate_jra_checksum(base_value=0, kaisai_nichime=1, race_number=2)
        assert result == 181

    def test_base_value_255でオーバーフローしない(self) -> None:
        """base_valueが255でもオーバーフローせずmod 256で計算される."""
        # 1日目1R = 255
        result = calculate_jra_checksum(base_value=255, kaisai_nichime=1, race_number=1)
        assert result == 255
        # 1日目2R = (255 + 181) mod 256 = 436 mod 256 = 180
        result = calculate_jra_checksum(base_value=255, kaisai_nichime=1, race_number=2)
        assert result == 180

    def test_実際のチェックサム例_中山1回8日目1R(self) -> None:
        """実際のJRA URLから逆算したチェックサム例."""
        # URL: pw01dde0106202601080120260124/F3 = チェックサム 0xF3 = 243
        # これは8日目1Rなので、base_value から逆算:
        # 243 = (base + 7*48) mod 256
        # 243 = (base + 336) mod 256
        # base = 243 - 336 + 256 = 163
        result = calculate_jra_checksum(base_value=163, kaisai_nichime=8, race_number=1)
        assert result == 243  # 0xF3
