"""IpatCredentialsのテスト."""
import pytest

from src.domain.value_objects import IpatCredentials


class TestIpatCredentials:
    """IpatCredentialsの単体テスト."""

    def test_正常な値で生成できる(self) -> None:
        """正常な値でIpatCredentialsを生成できることを確認."""
        creds = IpatCredentials(
            inet_id="ABcd1234",
            subscriber_number="12345678",
            pin="1234",
            pars_number="5678",
        )
        assert creds.inet_id == "ABcd1234"
        assert creds.subscriber_number == "12345678"
        assert creds.pin == "1234"
        assert creds.pars_number == "5678"

    def test_INET_IDが8桁でないとエラー(self) -> None:
        """INET-IDが8桁でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="8桁の英数字"):
            IpatCredentials(
                inet_id="AB12",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            )

    def test_INET_IDに記号が含まれるとエラー(self) -> None:
        """INET-IDに英数字以外が含まれる場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="8桁の英数字"):
            IpatCredentials(
                inet_id="AB12-34!",
                subscriber_number="12345678",
                pin="1234",
                pars_number="5678",
            )

    def test_INET_IDが数字のみでも許容される(self) -> None:
        """INET-IDが数字のみの8桁でも正常に生成できることを確認."""
        creds = IpatCredentials(
            inet_id="12345678",
            subscriber_number="12345678",
            pin="1234",
            pars_number="5678",
        )
        assert creds.inet_id == "12345678"

    def test_加入者番号が8桁でないとエラー(self) -> None:
        """加入者番号が8桁でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="8桁の数字"):
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="1234",
                pin="1234",
                pars_number="5678",
            )

    def test_加入者番号が数字でないとエラー(self) -> None:
        """加入者番号が数字でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="8桁の数字"):
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="1234567a",
                pin="1234",
                pars_number="5678",
            )

    def test_PINが4桁でないとエラー(self) -> None:
        """PINが4桁でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="4桁"):
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="12345678",
                pin="12",
                pars_number="5678",
            )

    def test_PARS番号が4桁でないとエラー(self) -> None:
        """P-ARS番号が4桁でない場合ValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="4桁"):
            IpatCredentials(
                inet_id="ABcd1234",
                subscriber_number="12345678",
                pin="1234",
                pars_number="56",
            )

    def test_不変オブジェクトである(self) -> None:
        """IpatCredentialsは不変（frozen）であることを確認."""
        creds = IpatCredentials(
            inet_id="ABcd1234",
            subscriber_number="12345678",
            pin="1234",
            pars_number="5678",
        )
        with pytest.raises(AttributeError):
            creds.pin = "9999"  # type: ignore
