"""IpatCredentialsのテスト."""
import pytest

from src.domain.value_objects import IpatCredentials


class TestIpatCredentials:
    """IpatCredentialsの単体テスト."""

    def test_正常な値で生成できる(self) -> None:
        """正常な値でIpatCredentialsを生成できることを確認."""
        creds = IpatCredentials(
            card_number="123456789012",
            birthday="19900101",
            pin="1234",
            dummy_pin="5678",
        )
        assert creds.card_number == "123456789012"
        assert creds.birthday == "19900101"
        assert creds.pin == "1234"
        assert creds.dummy_pin == "5678"

    def test_カード番号が12桁でないとエラー(self) -> None:
        """カード番号が12桁でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="12桁"):
            IpatCredentials(
                card_number="1234",
                birthday="19900101",
                pin="1234",
                dummy_pin="5678",
            )

    def test_カード番号が数字でないとエラー(self) -> None:
        """カード番号が数字でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="12桁"):
            IpatCredentials(
                card_number="12345678901a",
                birthday="19900101",
                pin="1234",
                dummy_pin="5678",
            )

    def test_誕生日が8桁でないとエラー(self) -> None:
        """誕生日が8桁でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="8桁"):
            IpatCredentials(
                card_number="123456789012",
                birthday="1990",
                pin="1234",
                dummy_pin="5678",
            )

    def test_誕生日が数字でないとエラー(self) -> None:
        """誕生日が数字でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="8桁"):
            IpatCredentials(
                card_number="123456789012",
                birthday="1990010a",
                pin="1234",
                dummy_pin="5678",
            )

    def test_PINが4桁でないとエラー(self) -> None:
        """PINが4桁でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="4桁"):
            IpatCredentials(
                card_number="123456789012",
                birthday="19900101",
                pin="12",
                dummy_pin="5678",
            )

    def test_ダミーPINが4桁でないとエラー(self) -> None:
        """ダミーPINが4桁でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="4桁"):
            IpatCredentials(
                card_number="123456789012",
                birthday="19900101",
                pin="1234",
                dummy_pin="56",
            )

    def test_不変オブジェクトである(self) -> None:
        """IpatCredentialsは不変（frozen）であることを確認."""
        creds = IpatCredentials(
            card_number="123456789012",
            birthday="19900101",
            pin="1234",
            dummy_pin="5678",
        )
        with pytest.raises(AttributeError):
            creds.pin = "9999"  # type: ignore
