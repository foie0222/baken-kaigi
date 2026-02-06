"""認証プロバイダの列挙型."""
from enum import Enum


class AuthProvider(str, Enum):
    """認証プロバイダ."""

    COGNITO = "cognito"
    GOOGLE = "google"
    APPLE = "apple"
