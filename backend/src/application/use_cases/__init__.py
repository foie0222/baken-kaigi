"""ユースケースモジュール."""
from .add_to_cart import AddToCartResult, AddToCartUseCase, CartNotFoundError
from .clear_cart import ClearCartResult, ClearCartUseCase
from .clear_cart import CartNotFoundError as ClearCartNotFoundError
from .get_cart import CartItemDTO, GetCartResult, GetCartUseCase
from .get_consultation import GetConsultationResult, GetConsultationUseCase
from .get_race_detail import GetRaceDetailUseCase, RaceDetailResult
from .get_race_list import GetRaceListUseCase, RaceListResult
from .remove_from_cart import ItemNotFoundError, RemoveFromCartResult, RemoveFromCartUseCase
from .remove_from_cart import CartNotFoundError as RemoveCartNotFoundError
from .send_message import (
    SendMessageResult,
    SendMessageUseCase,
    SessionNotFoundError,
    SessionNotInProgressError,
)
from .start_consultation import (
    EmptyCartError,
    StartConsultationResult,
    StartConsultationUseCase,
)
from .start_consultation import CartNotFoundError as StartConsultationCartNotFoundError
from .get_user_profile import GetUserProfileUseCase, UserNotFoundError, UserProfileResult
from .register_user import RegisterUserUseCase, RegisterUserResult, UserAlreadyExistsError
from .request_account_deletion import AccountDeletionResult, RequestAccountDeletionUseCase
from .update_user_profile import UpdateUserProfileResult, UpdateUserProfileUseCase
from .get_loss_limit import GetLossLimitResult, GetLossLimitUseCase
from .get_loss_limit import UserNotFoundError as LossLimitUserNotFoundError
from .set_loss_limit import (
    InvalidLossLimitAmountError,
    LossLimitAlreadySetError,
    SetLossLimitResult,
    SetLossLimitUseCase,
)
from .update_loss_limit import (
    LossLimitNotSetError,
    UpdateLossLimitResult,
    UpdateLossLimitUseCase,
)
from .update_loss_limit import InvalidLossLimitAmountError as UpdateInvalidLossLimitAmountError
from .check_loss_limit import CheckLossLimitResult, CheckLossLimitUseCase

__all__ = [
    # Race Use Cases
    "GetRaceListUseCase",
    "RaceListResult",
    "GetRaceDetailUseCase",
    "RaceDetailResult",
    # Cart Use Cases
    "AddToCartUseCase",
    "AddToCartResult",
    "GetCartUseCase",
    "GetCartResult",
    "CartItemDTO",
    "RemoveFromCartUseCase",
    "RemoveFromCartResult",
    "ClearCartUseCase",
    "ClearCartResult",
    # Consultation Use Cases
    "StartConsultationUseCase",
    "StartConsultationResult",
    "SendMessageUseCase",
    "SendMessageResult",
    "GetConsultationUseCase",
    "GetConsultationResult",
    # Errors
    "CartNotFoundError",
    "ItemNotFoundError",
    "EmptyCartError",
    "SessionNotFoundError",
    "SessionNotInProgressError",
    # User Use Cases
    "AccountDeletionResult",
    "GetUserProfileUseCase",
    "RegisterUserResult",
    "RegisterUserUseCase",
    "RequestAccountDeletionUseCase",
    "UpdateUserProfileResult",
    "UpdateUserProfileUseCase",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "UserProfileResult",
    # Loss Limit Use Cases
    "GetLossLimitUseCase",
    "GetLossLimitResult",
    "SetLossLimitUseCase",
    "SetLossLimitResult",
    "UpdateLossLimitUseCase",
    "UpdateLossLimitResult",
    "CheckLossLimitUseCase",
    "CheckLossLimitResult",
    "InvalidLossLimitAmountError",
    "LossLimitAlreadySetError",
    "LossLimitNotSetError",
    "LossLimitUserNotFoundError",
]
