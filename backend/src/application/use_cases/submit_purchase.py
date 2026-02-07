"""購入実行ユースケース."""
from src.domain.entities import PurchaseOrder
from src.domain.identifiers import CartId, UserId
from src.domain.ports import (
    CartRepository,
    IpatCredentialsProvider,
    IpatGateway,
    PurchaseOrderRepository,
    SpendingLimitProvider,
)
from src.domain.services.cart_to_ipat_converter import CartToIpatConverter
from src.domain.services.purchase_validator import PurchaseValidator


class CartNotFoundError(Exception):
    """カートが見つからないエラー."""

    pass


class CredentialsNotFoundError(Exception):
    """IPAT認証情報が見つからないエラー."""

    pass


class InsufficientBalanceError(Exception):
    """残高不足エラー."""

    pass


class IpatSubmissionError(Exception):
    """IPAT投票送信エラー."""

    pass


class SubmitPurchaseUseCase:
    """購入実行ユースケース."""

    def __init__(
        self,
        cart_repository: CartRepository,
        purchase_order_repository: PurchaseOrderRepository,
        ipat_gateway: IpatGateway,
        credentials_provider: IpatCredentialsProvider,
        spending_limit_provider: SpendingLimitProvider,
    ) -> None:
        """初期化."""
        self._cart_repository = cart_repository
        self._purchase_order_repository = purchase_order_repository
        self._ipat_gateway = ipat_gateway
        self._credentials_provider = credentials_provider
        self._spending_limit_provider = spending_limit_provider

    def execute(
        self,
        user_id: str,
        cart_id: str,
        race_date: str,
        course_code: str,
        race_number: int,
    ) -> PurchaseOrder:
        """購入を実行する."""
        uid = UserId(user_id)
        cid = CartId(cart_id)

        # カート取得
        cart = self._cart_repository.find_by_id(cid)
        if cart is None:
            raise CartNotFoundError(f"Cart not found: {cart_id}")

        # 認証情報取得
        credentials = self._credentials_provider.get_credentials(uid)
        if credentials is None:
            raise CredentialsNotFoundError("IPAT credentials not configured")

        # 残高照会
        balance = self._ipat_gateway.get_balance(credentials)

        # バリデーション
        try:
            PurchaseValidator.validate_purchase(
                cart=cart,
                balance=balance,
                spending_limit_provider=self._spending_limit_provider,
                user_id=uid,
            )
        except ValueError as e:
            raise InsufficientBalanceError(str(e)) from e

        # カートからIPAT投票行に変換
        bet_lines = CartToIpatConverter.convert(
            cart=cart,
            race_date=race_date,
            course_code=course_code,
            race_number=race_number,
        )

        # 購入注文作成
        order = PurchaseOrder.create(
            user_id=uid,
            cart_id=cid,
            bet_lines=bet_lines,
            total_amount=cart.get_total_amount(),
        )

        # 投票実行
        order.mark_submitted()
        success = self._ipat_gateway.submit_bets(credentials, bet_lines)

        if success:
            order.mark_completed()
        else:
            order.mark_failed("IPAT投票に失敗しました")

        # 結果保存
        self._purchase_order_repository.save(order)

        if not success:
            raise IpatSubmissionError("IPAT投票に失敗しました")

        return order
