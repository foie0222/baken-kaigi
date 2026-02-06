"""AuthProvider列挙型のテスト."""
from src.domain.enums import AuthProvider


class TestAuthProvider:
    """AuthProviderのテスト."""

    def test_COGNITOの値(self):
        assert AuthProvider.COGNITO.value == "cognito"

    def test_GOOGLEの値(self):
        assert AuthProvider.GOOGLE.value == "google"

    def test_APPLEの値(self):
        assert AuthProvider.APPLE.value == "apple"

    def test_文字列から生成できる(self):
        assert AuthProvider("cognito") == AuthProvider.COGNITO

    def test_全メンバーが3つ(self):
        assert len(AuthProvider) == 3
