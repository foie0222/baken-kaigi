"""自動投票 BetExecutor Lambda.

レース発走5分前に起動され、決定論的パイプラインで買い目を生成し、
IPAT投票を実行する。
"""
import logging
import os

import boto3
import requests

from src.domain.identifiers import CartId, UserId
from src.domain.entities import PurchaseOrder
from src.domain.value_objects import Money
from src.domain.services.betting_pipeline import (
    BETAS,
    PLACE_WEIGHTS,
    SOURCES,
    WIN_WEIGHTS,
    compute_agree_counts,
    log_opinion_pool,
    market_implied_probs,
    source_to_probs,
)
from src.domain.services.bet_generator import (
    generate_exacta_bets,
    generate_place_bets,
    generate_quinella_bets,
    generate_wide_bets,
    generate_win_bets,
)
from src.domain.services.bet_to_ipat_converter import BetToIpatConverter
from src.infrastructure.providers.gamble_os_ipat_gateway import GambleOsIpatGateway
from src.infrastructure.providers.secrets_manager_credentials_provider import (
    SecretsManagerCredentialsProvider,
)
from src.infrastructure.repositories.dynamodb_purchase_order_repository import (
    DynamoDBPurchaseOrderRepository,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JRAVAN_API_URL = os.environ.get("JRAVAN_API_URL", "http://10.0.1.100:8000")
GAMBLE_OS_SECRET_NAME = os.environ["GAMBLE_OS_SECRET_NAME"]
AI_PREDICTIONS_TABLE = os.environ.get(
    "AI_PREDICTIONS_TABLE_NAME", "baken-kaigi-ai-predictions"
)


def handler(event, context):
    """Lambda ハンドラ."""
    race_id = event["race_id"]
    logger.info("BetExecutor started: race_id=%s", race_id)

    target_user_id = os.environ.get("TARGET_USER_ID", "")
    if not target_user_id:
        raise ValueError("TARGET_USER_ID environment variable is required")

    try:
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = dynamodb.Table(AI_PREDICTIONS_TABLE)

        predictions = _fetch_predictions(table, race_id)
        if len(predictions) < 2:
            logger.warning("予想ソース不足: %d ソース", len(predictions))
            return {"status": "ok", "bets_count": 0, "reason": "insufficient_sources"}

        odds = _fetch_odds(race_id)
        bets = _run_pipeline(predictions, odds)

        if not bets:
            logger.info("買い目なし")
            return {"status": "ok", "bets_count": 0, "reason": "no_bets"}

        bet_lines = BetToIpatConverter.convert(race_id, bets)
        _submit_bets(race_id, bet_lines, target_user_id)
    except Exception:
        logger.exception("BetExecutor failed: race_id=%s", race_id)
        raise

    return {"status": "ok", "bets_count": len(bet_lines), "race_id": race_id}


def _fetch_predictions(table, race_id: str) -> dict:
    """DynamoDB から4ソースのAI予想を取得."""
    predictions = {}
    for source in SOURCES:
        resp = table.get_item(Key={"race_id": race_id, "source": source})
        item = resp.get("Item")
        if not item:
            continue
        preds = [
            {
                "horse_number": int(p["horse_number"]),
                "score": float(p["score"]),
                "rank": int(p["rank"]),
            }
            for p in item.get("predictions", [])
        ]
        if preds:
            predictions[source] = sorted(preds, key=lambda x: x["rank"])
    return predictions


def _fetch_odds(race_id: str) -> dict:
    """JRA-VAN API から最新オッズを取得."""
    resp = requests.get(f"{JRAVAN_API_URL}/races/{race_id}/odds", timeout=30)
    resp.raise_for_status()
    return resp.json()


def _run_pipeline(predictions: dict, odds: dict) -> list:
    """決定論的パイプラインで5券種の買い目を生成."""
    from src.domain.services.bet_generator import BetProposal

    all_bets: list[BetProposal] = []

    # --- 単勝用: WIN_WEIGHTS ---
    win_prob_dicts, win_weights = [], []
    for s, w in zip(SOURCES, WIN_WEIGHTS):
        if s in predictions:
            win_prob_dicts.append(source_to_probs(predictions[s], BETAS[s]))
            win_weights.append(w)
    if len(win_prob_dicts) >= 2:
        wt = sum(win_weights)
        win_combined = log_opinion_pool(win_prob_dicts, [w / wt for w in win_weights])
        if win_combined and "win" in odds:
            win_mkt = market_implied_probs(odds["win"])
            all_bets.extend(generate_win_bets(win_combined, win_mkt, odds["win"]))

    # --- 複勝・ワイド・馬連・馬単用: PLACE_WEIGHTS ---
    place_prob_dicts, place_weights = [], []
    source_probs_list = []
    for s, w in zip(SOURCES, PLACE_WEIGHTS):
        if s in predictions:
            pd = source_to_probs(predictions[s], BETAS[s])
            place_prob_dicts.append(pd)
            place_weights.append(w)
            source_probs_list.append(pd)
    if len(place_prob_dicts) >= 2:
        wt = sum(place_weights)
        place_combined = log_opinion_pool(
            place_prob_dicts, [w / wt for w in place_weights]
        )
        if not place_combined:
            return all_bets

        ranked = sorted(place_combined.items(), key=lambda x: x[1], reverse=True)
        agree_counts = compute_agree_counts(source_probs_list, top_n=4)

        if "place" in odds:
            all_bets.extend(generate_place_bets(ranked, odds["place"], agree_counts))

        if "quinella_place" in odds:
            all_bets.extend(
                generate_wide_bets(ranked, odds["quinella_place"], agree_counts)
            )

        if "quinella" in odds:
            all_bets.extend(
                generate_quinella_bets(ranked, odds["quinella"], agree_counts)
            )

        if "quinella" in odds:
            all_bets.extend(
                generate_exacta_bets(ranked, odds["quinella"], agree_counts)
            )

    return all_bets


def _submit_bets(race_id, bet_lines, target_user_id: str):
    """IPAT投票を実行し、PurchaseOrder を記録."""
    user_id = UserId(target_user_id)

    creds_provider = SecretsManagerCredentialsProvider()
    credentials = creds_provider.get_credentials(user_id)
    if credentials is None:
        raise RuntimeError(f"IPAT credentials not found for user: {target_user_id}")

    gateway = GambleOsIpatGateway(secret_name=GAMBLE_OS_SECRET_NAME)

    total = sum(line.amount for line in bet_lines)
    order = PurchaseOrder.create(
        user_id=user_id,
        cart_id=CartId(f"auto-{race_id}"),
        bet_lines=bet_lines,
        total_amount=Money(total),
    )
    order.mark_submitted()

    repo = DynamoDBPurchaseOrderRepository()

    success = gateway.submit_bets(credentials, bet_lines)
    if success:
        order.mark_completed()
    else:
        order.mark_failed("IPAT投票に失敗しました")

    repo.save(order)

    if not success:
        raise RuntimeError(f"IPAT submit failed for race: {race_id}")

    logger.info(
        "投票完了: race=%s, bets=%d, total=%d",
        race_id,
        len(bet_lines),
        total,
    )
