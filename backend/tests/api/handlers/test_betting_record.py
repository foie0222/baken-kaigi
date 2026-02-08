"""投票記録APIハンドラーのテスト."""
import json
from datetime import date

from src.api.dependencies import Dependencies
from src.api.handlers.betting_record import (
    betting_record_handler,
    create_betting_record_handler,
    get_betting_records_handler,
    get_betting_summary_handler,
    settle_betting_record_handler,
)
from src.domain.entities import BettingRecord
from src.domain.enums import BetType
from src.domain.identifiers import RaceId, UserId
from src.domain.value_objects import HorseNumbers, Money
from src.infrastructure.repositories.in_memory_betting_record_repository import (
    InMemoryBettingRecordRepository,
)


def _auth_event(
    user_id: str = "user-001",
    body: dict | None = None,
    query_params: dict | None = None,
    path_params: dict | None = None,
) -> dict:
    event = {
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": user_id,
                }
            }
        },
    }
    if body is not None:
        event["body"] = json.dumps(body)
    if query_params is not None:
        event["queryStringParameters"] = query_params
    if path_params is not None:
        event["pathParameters"] = path_params
    return event


def _setup_deps() -> InMemoryBettingRecordRepository:
    Dependencies.reset()
    repo = InMemoryBettingRecordRepository()
    Dependencies.set_betting_record_repository(repo)
    return repo


def _make_record(
    user_id: str = "user-001",
    race_date: date = date(2026, 5, 5),
    venue: str = "東京",
    bet_type: BetType = BetType.WIN,
) -> BettingRecord:
    return BettingRecord.create(
        user_id=UserId(user_id),
        race_id=RaceId("202605051211"),
        race_name="東京11R 日本ダービー",
        race_date=race_date,
        venue=venue,
        bet_type=bet_type,
        horse_numbers=HorseNumbers.of(1),
        amount=Money.of(100),
    )


class TestCreateBettingRecordHandler:
    """create_betting_record_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {"body": json.dumps({"race_id": "202605051211"})}
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常作成(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R 日本ダービー",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 100,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert "record_id" in body
        assert body["status"] == "pending"
        assert body["amount"] == 100

    def test_race_id未指定で400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_name": "東京11R",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 100,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_amount未指定で400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_amount_0以下で400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R 日本ダービー",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 0,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_amountがfloatの場合intに変換される(self) -> None:
        """floatのamountはintに変換されて正常作成される."""
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R 日本ダービー",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 100.0,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["amount"] == 100
        assert isinstance(body["amount"], int)

    def test_amountが小数の場合400(self) -> None:
        """小数点以下があるamountはバリデーションエラー."""
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R 日本ダービー",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 100.5,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_amountがNaNの場合400(self) -> None:
        """NaNのamountはバリデーションエラー."""
        _setup_deps()
        event = {
            "requestContext": {"authorizer": {"claims": {"sub": "user-001"}}},
            "body": '{"race_id":"202605051211","race_name":"東京11R","race_date":"2026-05-05","venue":"東京","bet_type":"win","horse_numbers":[1],"amount":NaN}',
        }
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_amountがInfinityの場合400(self) -> None:
        """Infinityのamountはバリデーションエラー."""
        _setup_deps()
        event = {
            "requestContext": {"authorizer": {"claims": {"sub": "user-001"}}},
            "body": '{"race_id":"202605051211","race_name":"東京11R","race_date":"2026-05-05","venue":"東京","bet_type":"win","horse_numbers":[1],"amount":Infinity}',
        }
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_amountがboolの場合400(self) -> None:
        """boolのamountはバリデーションエラー."""
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R 日本ダービー",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": True,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_不正なbet_typeで400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R 日本ダービー",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "invalid_type",
            "horse_numbers": [1],
            "amount": 100,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_race_idが整数の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": 202605051211,
            "race_name": "東京11R",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 100,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_race_dateが整数の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R",
            "race_date": 20260505,
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 100,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_venueが整数の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R",
            "race_date": "2026-05-05",
            "venue": 123,
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 100,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_bet_typeが整数の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": 1,
            "horse_numbers": [1],
            "amount": 100,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_horse_numbersが文字列の場合400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": "1,2,3",
            "amount": 100,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_不正なrace_dateで400(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R 日本ダービー",
            "race_date": "invalid-date",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 100,
        })
        result = create_betting_record_handler(event, None)
        assert result["statusCode"] == 400


class TestGetBettingRecordsHandler:
    """get_betting_records_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {}
        result = get_betting_records_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常取得(self) -> None:
        repo = _setup_deps()
        repo.save(_make_record())
        repo.save(_make_record())

        event = _auth_event()
        result = get_betting_records_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body) == 2

    def test_フィルタ付き取得(self) -> None:
        repo = _setup_deps()
        repo.save(_make_record(venue="東京"))
        repo.save(_make_record(venue="中山"))

        event = _auth_event(query_params={"venue": "東京"})
        result = get_betting_records_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body) == 1

    def test_空リスト(self) -> None:
        _setup_deps()
        event = _auth_event()
        result = get_betting_records_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body == []


class TestGetBettingSummaryHandler:
    """get_betting_summary_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {}
        result = get_betting_summary_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常取得(self) -> None:
        repo = _setup_deps()
        record = _make_record()
        record.settle(Money.of(300))
        repo.save(record)

        event = _auth_event(query_params={"period": "all_time"})
        result = get_betting_summary_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["total_investment"] == 100
        assert body["total_payout"] == 300
        assert body["record_count"] == 1

    def test_デフォルトperiodはall_time(self) -> None:
        _setup_deps()
        event = _auth_event()
        result = get_betting_summary_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["record_count"] == 0


class TestSettleBettingRecordHandler:
    """settle_betting_record_handler のテスト."""

    def test_認証なしで401(self) -> None:
        _setup_deps()
        event = {
            "pathParameters": {"record_id": "r-001"},
            "body": json.dumps({"payout": 500}),
        }
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 401

    def test_正常確定(self) -> None:
        repo = _setup_deps()
        record = _make_record()
        repo.save(record)

        event = _auth_event(
            path_params={"record_id": record.record_id.value},
            body={"payout": 500},
        )
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "settled"
        assert body["payout"] == 500
        assert body["profit"] == 400

    def test_存在しない記録で404(self) -> None:
        _setup_deps()
        event = _auth_event(
            path_params={"record_id": "nonexistent"},
            body={"payout": 500},
        )
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 404

    def test_payoutがfloatの場合intに変換される(self) -> None:
        """floatのpayoutはintに変換されて正常確定される."""
        repo = _setup_deps()
        record = _make_record()
        repo.save(record)

        event = _auth_event(
            path_params={"record_id": record.record_id.value},
            body={"payout": 500.0},
        )
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["payout"] == 500
        assert isinstance(body["payout"], int)

    def test_payoutが小数の場合400(self) -> None:
        """小数点以下があるpayoutはバリデーションエラー."""
        repo = _setup_deps()
        record = _make_record()
        repo.save(record)

        event = _auth_event(
            path_params={"record_id": record.record_id.value},
            body={"payout": 500.5},
        )
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_payoutがNaNの場合400(self) -> None:
        """NaNのpayoutはバリデーションエラー."""
        repo = _setup_deps()
        record = _make_record()
        repo.save(record)

        event = {
            "requestContext": {"authorizer": {"claims": {"sub": "user-001"}}},
            "pathParameters": {"record_id": record.record_id.value},
            "body": '{"payout":NaN}',
        }
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_payoutがboolの場合400(self) -> None:
        """boolのpayoutはバリデーションエラー."""
        repo = _setup_deps()
        record = _make_record()
        repo.save(record)

        event = _auth_event(
            path_params={"record_id": record.record_id.value},
            body={"payout": False},
        )
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_payout未指定で400(self) -> None:
        _setup_deps()
        event = _auth_event(
            path_params={"record_id": "r-001"},
            body={},
        )
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_record_id未指定で400(self) -> None:
        _setup_deps()
        event = _auth_event(body={"payout": 500})
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_他ユーザーのレコードをsettleすると404(self) -> None:
        repo = _setup_deps()
        record = _make_record(user_id="user-002")
        repo.save(record)

        event = _auth_event(
            user_id="user-001",
            path_params={"record_id": record.record_id.value},
            body={"payout": 500},
        )
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 404

    def test_既にSETTLEDのレコードを再settleするとエラー(self) -> None:
        repo = _setup_deps()
        record = _make_record()
        record.settle(Money.of(500))
        repo.save(record)

        event = _auth_event(
            path_params={"record_id": record.record_id.value},
            body={"payout": 1000},
        )
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 400

    def test_payout負値で400(self) -> None:
        repo = _setup_deps()
        record = _make_record()
        repo.save(record)

        event = _auth_event(
            path_params={"record_id": record.record_id.value},
            body={"payout": -100},
        )
        result = settle_betting_record_handler(event, None)
        assert result["statusCode"] == 400


class TestBettingRecordRouter:
    """betting_record_handler ルーティングのテスト."""

    def test_POST_betting_recordsでcreateに振り分け(self) -> None:
        _setup_deps()
        event = _auth_event(body={
            "race_id": "202605051211",
            "race_name": "東京11R 日本ダービー",
            "race_date": "2026-05-05",
            "venue": "東京",
            "bet_type": "win",
            "horse_numbers": [1],
            "amount": 100,
        })
        event["resource"] = "/betting-records"
        event["httpMethod"] = "POST"
        result = betting_record_handler(event, None)
        assert result["statusCode"] == 201

    def test_GET_betting_recordsでlistに振り分け(self) -> None:
        _setup_deps()
        event = _auth_event()
        event["resource"] = "/betting-records"
        event["httpMethod"] = "GET"
        result = betting_record_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body == []

    def test_GET_betting_records_summaryでsummaryに振り分け(self) -> None:
        _setup_deps()
        event = _auth_event()
        event["resource"] = "/betting-records/summary"
        event["httpMethod"] = "GET"
        result = betting_record_handler(event, None)
        assert result["statusCode"] == 200

    def test_PUT_settleでsettleに振り分け(self) -> None:
        repo = _setup_deps()
        record = _make_record()
        repo.save(record)

        event = _auth_event(
            path_params={"record_id": record.record_id.value},
            body={"payout": 500},
        )
        event["resource"] = "/betting-records/{record_id}/settle"
        event["httpMethod"] = "PUT"
        result = betting_record_handler(event, None)
        assert result["statusCode"] == 200

    def test_不明なルートで400(self) -> None:
        event = {"resource": "/unknown", "httpMethod": "GET"}
        result = betting_record_handler(event, None)
        assert result["statusCode"] == 400
