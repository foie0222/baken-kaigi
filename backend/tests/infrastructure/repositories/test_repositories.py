"""リポジトリのテスト."""
from abc import ABC

import pytest

from src.domain.value_objects import BetSelection
from src.domain.enums import BetType
from src.domain.entities import Cart
from src.domain.entities import CartItem
from src.domain.ports import CartRepository
from src.domain.entities import ConsultationSession
from src.domain.ports import ConsultationSessionRepository
from src.domain.value_objects import HorseNumbers
from src.infrastructure.repositories import InMemoryCartRepository
from src.infrastructure.repositories import InMemoryConsultationSessionRepository
from src.domain.value_objects import Money
from src.domain.identifiers import RaceId


class TestCartRepository:
    """CartRepositoryの単体テスト."""

    def test_CartRepositoryは抽象基底クラスである(self) -> None:
        """CartRepositoryがABCを継承していることを確認."""
        assert issubclass(CartRepository, ABC)


class TestInMemoryCartRepository:
    """InMemoryCartRepositoryの単体テスト."""

    def test_saveで保存しfind_by_idで取得できる(self) -> None:
        """saveで保存したカートをfind_by_idで取得できることを確認."""
        repo = InMemoryCartRepository()
        cart = Cart.create()
        repo.save(cart)
        found = repo.find_by_id(cart.cart_id)
        assert found is not None
        assert found.cart_id == cart.cart_id

    def test_find_by_idで存在しないIDはNone(self) -> None:
        """find_by_idで存在しないIDを指定するとNoneが返ることを確認."""
        repo = InMemoryCartRepository()
        from src.domain.identifiers import CartId
        assert repo.find_by_id(CartId("nonexistent")) is None

    def test_saveで既存カートを更新できる(self) -> None:
        """saveで既存のカートを更新できることを確認."""
        repo = InMemoryCartRepository()
        cart = Cart.create()
        repo.save(cart)
        bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
        cart.add_item(RaceId("r1"), "レース1", bet)
        repo.save(cart)
        found = repo.find_by_id(cart.cart_id)
        assert found.get_item_count() == 1

    def test_deleteで削除できる(self) -> None:
        """deleteでカートを削除できることを確認."""
        repo = InMemoryCartRepository()
        cart = Cart.create()
        repo.save(cart)
        repo.delete(cart.cart_id)
        assert repo.find_by_id(cart.cart_id) is None

    def test_deleteで存在しないIDは何もしない(self) -> None:
        """deleteで存在しないIDを指定しても例外が発生しないことを確認."""
        repo = InMemoryCartRepository()
        from src.domain.identifiers import CartId
        repo.delete(CartId("nonexistent"))  # 例外が発生しない

    def test_find_by_user_idでユーザーのカートを取得(self) -> None:
        """find_by_user_idでユーザーに紐付いたカートを取得できることを確認."""
        repo = InMemoryCartRepository()
        from src.domain.identifiers import UserId
        cart = Cart.create(user_id=UserId("user-1"))
        repo.save(cart)
        found = repo.find_by_user_id(UserId("user-1"))
        assert found is not None
        assert found.user_id.value == "user-1"

    def test_find_by_user_idで存在しないユーザーはNone(self) -> None:
        """find_by_user_idで存在しないユーザーを指定するとNoneが返ることを確認."""
        repo = InMemoryCartRepository()
        from src.domain.identifiers import UserId
        assert repo.find_by_user_id(UserId("nonexistent")) is None


class TestConsultationSessionRepository:
    """ConsultationSessionRepositoryの単体テスト."""

    def test_ConsultationSessionRepositoryは抽象基底クラスである(self) -> None:
        """ConsultationSessionRepositoryがABCを継承していることを確認."""
        assert issubclass(ConsultationSessionRepository, ABC)


class TestInMemoryConsultationSessionRepository:
    """InMemoryConsultationSessionRepositoryの単体テスト."""

    def test_saveで保存しfind_by_idで取得できる(self) -> None:
        """saveで保存したセッションをfind_by_idで取得できることを確認."""
        repo = InMemoryConsultationSessionRepository()
        session = ConsultationSession.create()
        repo.save(session)
        found = repo.find_by_id(session.session_id)
        assert found is not None
        assert found.session_id == session.session_id

    def test_find_by_idで存在しないIDはNone(self) -> None:
        """find_by_idで存在しないIDを指定するとNoneが返ることを確認."""
        repo = InMemoryConsultationSessionRepository()
        from src.domain.identifiers import SessionId
        assert repo.find_by_id(SessionId("nonexistent")) is None

    def test_saveで既存セッションを更新できる(self) -> None:
        """saveで既存のセッションを更新できることを確認."""
        repo = InMemoryConsultationSessionRepository()
        session = ConsultationSession.create()
        repo.save(session)
        bet = BetSelection(BetType.WIN, HorseNumbers.of(1), Money(100))
        item = CartItem.create(RaceId("r1"), "R1", bet)
        session.start([item])
        repo.save(session)
        found = repo.find_by_id(session.session_id)
        from src.domain.enums import SessionStatus
        assert found.status == SessionStatus.IN_PROGRESS

    def test_deleteで削除できる(self) -> None:
        """deleteでセッションを削除できることを確認."""
        repo = InMemoryConsultationSessionRepository()
        session = ConsultationSession.create()
        repo.save(session)
        repo.delete(session.session_id)
        assert repo.find_by_id(session.session_id) is None

    def test_find_by_user_idでユーザーのセッションを取得(self) -> None:
        """find_by_user_idでユーザーのセッション一覧を取得できることを確認."""
        repo = InMemoryConsultationSessionRepository()
        from src.domain.identifiers import UserId
        session1 = ConsultationSession.create(user_id=UserId("user-1"))
        session2 = ConsultationSession.create(user_id=UserId("user-1"))
        session3 = ConsultationSession.create(user_id=UserId("user-2"))
        repo.save(session1)
        repo.save(session2)
        repo.save(session3)
        sessions = repo.find_by_user_id(UserId("user-1"))
        assert len(sessions) == 2

    def test_find_by_user_idで存在しないユーザーは空リスト(self) -> None:
        """find_by_user_idで存在しないユーザーを指定すると空リストが返ることを確認."""
        repo = InMemoryConsultationSessionRepository()
        from src.domain.identifiers import UserId
        assert repo.find_by_user_id(UserId("nonexistent")) == []
